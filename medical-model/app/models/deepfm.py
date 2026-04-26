"""DeepFM 模型 — 合并Embedding版本（兼容Opacus DP-SGD）+ 连续特征旁路

v3: 删除nn.Sigmoid输出层, forward返回raw logits (Opacus+FocalLoss兼容)
    推理时在predictor中手动sigmoid

变更原因:
1. FocalLoss标准实现基于logits, 对sigmoid输出逆变换引入数值不稳定性
2. Opacus DP-SGD在logits空间操作更稳定
3. BCEWithLogitsLoss要求logits输入
"""

import torch
import torch.nn as nn
from typing import List, Tuple, Optional
from itertools import accumulate


class MultiFieldFM(nn.Module):
    """多字段 Factorization Machine：合并 Embedding + 二阶交叉交互

    合成 Embedding 方案：将每个字段的 Embedding 合并为一个大的 nn.Embedding，
    通过 field_offsets 偏移索引来区分不同字段。此方案兼容 Opacus PrivacyEngine，
    因为 Opacus 不支持 nn.ModuleList 中的循环遍历。

    v2: field_offsets改为register_buffer, 确保state_dict包含且设备迁移正确

    Args:
        field_dims: 每个字段的词汇表大小列表
        embed_dim: Embedding 维度
        embed_dropout: Embedding dropout 比率
    """

    def __init__(self, field_dims: List[int], embed_dim: int, embed_dropout: float = 0.1):
        super().__init__()
        self.num_fields = len(field_dims)
        self.embed_dim = embed_dim
        self.field_dims = field_dims

        # 合并 Embedding：所有字段词汇表拼接为一个大的 Embedding
        total_dim = sum(field_dims)

        # v2: register_buffer替代Python list
        offsets = torch.tensor(
            [0] + list(accumulate(field_dims[:-1])), dtype=torch.long
        )
        self.register_buffer('field_offsets', offsets)

        self.embedding = nn.Embedding(total_dim, embed_dim)
        self.linear = nn.Embedding(total_dim, 1)

        self.embed_dropout = nn.Dropout(embed_dropout)

    def forward(
        self, field_indices: torch.Tensor, continuous_features: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            field_indices: [batch, num_fields] 每个字段的整数索引
            continuous_features: [batch, num_continuous] 连续特征（可选，归一化后传入）
        Returns:
            first_order: [batch, 1] 一阶项
            embeds: [batch, num_fields, embed_dim] 各字段嵌入向量
        """
        # 将字段索引偏移到合并 Embedding 的全局位置
        # v2: 使用register_buffer, 无需每次创建新tensor
        global_indices = field_indices + self.field_offsets.unsqueeze(0)

        # 一阶项：各字段偏置求和
        first_order = self.linear(global_indices).sum(dim=1)  # [batch, 1]

        # 二阶项：FM 交互
        embeds = self.embedding(global_indices)  # [batch, num_fields, embed_dim]
        embeds = self.embed_dropout(embeds)

        square_of_sum = embeds.sum(dim=1).pow(2)  # [batch, embed_dim]
        sum_of_square = embeds.pow(2).sum(dim=1)   # [batch, embed_dim]
        second_order = 0.5 * (square_of_sum - sum_of_square).sum(dim=1, keepdim=True)

        return first_order + second_order, embeds


class Deep(nn.Module):
    """Deep 部分：MLP with LayerNorm，支持逐层差异化 dropout

    Args:
        input_dim: 输入维度（= num_fields * embed_dim + num_continuous）
        hidden_dims: 隐藏层维度列表
        dropouts: 逐层 dropout 比率列表，长度应等于 hidden_dims
    """

    def __init__(
        self,
        input_dim: int,
        hidden_dims: List[int],
        dropouts: Optional[List[float]] = None,
    ):
        super().__init__()
        if dropouts is None:
            dropouts = [0.1] * len(hidden_dims)
        elif len(dropouts) == 1:
            dropouts = dropouts * len(hidden_dims)

        if len(dropouts) != len(hidden_dims):
            raise ValueError(
                f"dropouts length ({len(dropouts)}) must match hidden_dims length ({len(hidden_dims)})"
            )

        layers = []
        prev_dim = input_dim
        for hidden_dim, dropout_rate in zip(hidden_dims, dropouts):
            layers.extend([
                nn.Linear(prev_dim, hidden_dim),
                nn.ReLU(),
                nn.LayerNorm(hidden_dim),
                nn.Dropout(dropout_rate),
            ])
            prev_dim = hidden_dim
        layers.append(nn.Linear(prev_dim, 1))
        self.mlp = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.mlp(x)


class DeepFM(nn.Module):
    """多字段 DeepFM：FM + Deep + 连续特征旁路 + raw logits 输出

    v3: 删除nn.Sigmoid输出层, forward返回raw logits
    推理时在predictor中手动sigmoid: torch.sigmoid(logits)

    Args:
        field_dims: 每个字段的词汇表大小列表
        embed_dim: Embedding 维度
        hidden_dims: Deep MLP 隐藏层维度列表
        num_continuous: 连续特征数量（默认4: age_raw, bmi_raw, gfr_raw, liver_score_raw）
        dropout: Deep 部分 dropout（单值或逐层列表）
        embed_dropout: Embedding dropout 比率
    """

    def __init__(
        self,
        field_dims: List[int],
        embed_dim: int = 8,
        hidden_dims: List[int] = [64, 32],
        num_continuous: int = 4,
        dropout: float = 0.1,
        embed_dropout: float = 0.05,
    ):
        super().__init__()
        self.fm = MultiFieldFM(field_dims, embed_dim, embed_dropout)
        deep_input_dim = len(field_dims) * embed_dim + num_continuous
        # 逐层递减 dropout
        dropouts = [
            min(dropout, 0.1 + 0.05 * (len(hidden_dims) - i - 1) / max(len(hidden_dims) - 1, 1))
            for i in range(len(hidden_dims))
        ]
        self.deep = Deep(deep_input_dim, hidden_dims, dropouts)
        # v3: 不再使用nn.Sigmoid, 返回raw logits
        self.num_continuous = num_continuous

    def forward(
        self, field_indices: torch.Tensor, continuous_features: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            field_indices: [batch, num_fields] 每个字段的整数索引
            continuous_features: [batch, num_continuous] 连续特征（可选）
        Returns:
            logits: [batch, 1] raw logits (未经sigmoid)
            embeds: [batch, num_fields, embed_dim] 嵌入向量（用于解释）
        """
        fm_out, embeds = self.fm(field_indices, continuous_features)

        deep_input = embeds.view(embeds.size(0), -1)

        # 连续特征旁路：归一化后的连续值直接拼接
        if continuous_features is not None and self.num_continuous > 0:
            deep_input = torch.cat([deep_input, continuous_features], dim=1)

        deep_out = self.deep(deep_input)
        logits = fm_out + deep_out
        return logits, embeds
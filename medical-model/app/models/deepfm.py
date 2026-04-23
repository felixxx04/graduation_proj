import torch
import torch.nn as nn
from typing import List, Tuple


class MultiFieldFM(nn.Module):
    """多字段 Factorization Machine：每个字段独立 Embedding + 二阶交叉交互"""

    def __init__(self, field_dims: List[int], embed_dim: int, embed_dropout: float = 0.1):
        super().__init__()
        self.num_fields = len(field_dims)
        self.embed_dim = embed_dim

        # 每个字段独立 Embedding
        self.embeddings = nn.ModuleList([
            nn.Embedding(dim, embed_dim) for dim in field_dims
        ])
        self.embed_dropout = nn.Dropout(embed_dropout)

        # 一阶线性偏置（每个字段一个）
        self.linear_biases = nn.ModuleList([
            nn.Embedding(dim, 1) for dim in field_dims
        ])

    def forward(self, field_indices: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            field_indices: [batch, num_fields] 每个字段的整数索引
        Returns:
            first_order: [batch, 1] 一阶项
            embeds: [batch, num_fields, embed_dim] 各字段嵌入向量
        """
        # 一阶项：各字段偏置求和
        first_order = torch.zeros(field_indices.size(0), 1, device=field_indices.device)
        for i in range(self.num_fields):
            first_order += self.linear_biases[i](field_indices[:, i])

        # 二阶项：FM 交互
        embeds = torch.stack([
            self.embeddings[i](field_indices[:, i]) for i in range(self.num_fields)
        ], dim=1)  # [batch, num_fields, embed_dim]
        embeds = self.embed_dropout(embeds)

        square_of_sum = embeds.sum(dim=1).pow(2)  # [batch, embed_dim]
        sum_of_square = embeds.pow(2).sum(dim=1)   # [batch, embed_dim]
        second_order = 0.5 * (square_of_sum - sum_of_square).sum(dim=1, keepdim=True)

        return first_order + second_order, embeds


class Deep(nn.Module):
    """Deep 部分：MLP with LayerNorm"""

    def __init__(self, input_dim: int, hidden_dims: List[int], dropout: float = 0.3):
        super().__init__()
        layers = []
        prev_dim = input_dim
        for hidden_dim in hidden_dims:
            layers.extend([
                nn.Linear(prev_dim, hidden_dim),
                nn.ReLU(),
                nn.LayerNorm(hidden_dim),
                nn.Dropout(dropout),
            ])
            prev_dim = hidden_dim
        layers.append(nn.Linear(prev_dim, 1))
        self.mlp = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.mlp(x)


class DeepFM(nn.Module):
    """多字段 DeepFM：FM + Deep + Sigmoid 输出"""

    def __init__(self, field_dims: List[int], embed_dim: int = 16,
                 hidden_dims: List[int] = [128, 64, 32],
                 dropout: float = 0.3, embed_dropout: float = 0.1):
        super().__init__()
        self.fm = MultiFieldFM(field_dims, embed_dim, embed_dropout)
        deep_input_dim = len(field_dims) * embed_dim
        self.deep = Deep(deep_input_dim, hidden_dims, dropout)
        self.output_layer = nn.Sigmoid()

    def forward(self, field_indices: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            field_indices: [batch, num_fields] 每个字段的整数索引
        Returns:
            output: [batch, 1] sigmoid 概率
            embeds: [batch, num_fields, embed_dim] 嵌入向量（用于解释）
        """
        fm_out, embeds = self.fm(field_indices)
        deep_input = embeds.view(embeds.size(0), -1)
        deep_out = self.deep(deep_input)
        output = fm_out + deep_out
        return self.output_layer(output), embeds
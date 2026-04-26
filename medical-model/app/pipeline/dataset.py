"""DrugRecommendation Dataset — PyTorch Dataset 用于训练

每条样本 = (field_indices_tensor, continuous_features_tensor, label_tensor)
"""

import torch
import logging
from typing import List, Dict, Any
from torch.utils.data import Dataset

logger = logging.getLogger(__name__)


class DrugRecommendationDataset(Dataset):
    """药物推荐训练数据集

    Args:
        samples: 训练样本列表，每条含:
            - field_indices: List[int] 字段索引
            - continuous_features: List[float] 连续特征
            - label: float 标签值
            - safety_flags: dict 安全标记（不用于训练，仅用于分析）
    """

    def __init__(self, samples: List[Dict[str, Any]]):
        self.samples = samples
        self.num_fields = len(samples[0]['field_indices'])
        self.num_continuous = len(samples[0].get('continuous_features', []))

        logger.info(
            f"DrugRecommendationDataset: {len(samples)} samples, "
            f"{self.num_fields} fields, {self.num_continuous} continuous features"
        )

        # 统计标签分布
        label_counts = {}
        for s in samples:
            label = round(s['label'], 1)
            label_counts[label] = label_counts.get(label, 0) + 1
        logger.info(f"Label distribution: {label_counts}")

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        sample = self.samples[idx]

        field_indices = torch.tensor(
            sample['field_indices'], dtype=torch.long
        )
        continuous_features = torch.tensor(
            sample.get('continuous_features', [0.0] * self.num_continuous),
            dtype=torch.float32,
        )
        label = torch.tensor(
            sample['label'], dtype=torch.float32
        ).unsqueeze(0)

        return {
            'field_indices': field_indices,
            'continuous_features': continuous_features,
            'label': label,
        }

    def get_negative_sample_ratio(self) -> float:
        """获取负样本比例（label <= 0.3 的样本占比）"""
        neg_count = sum(1 for s in self.samples if s['label'] <= 0.3)
        return neg_count / len(self.samples) if len(self.samples) > 0 else 0.0
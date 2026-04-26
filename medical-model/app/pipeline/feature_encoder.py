"""特征编码器 — 将原始数据转换为 DeepFM field_indices

负责：
- 构建每个字段的词汇表映射（value → index）
- 将患者+药物数据转换为 field_indices 数组
- 反向映射用于推荐解释
- JSON 序列化/反序列化 vocab 和 field_dims
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from app.pipeline.schema import FIELD_ORDER, CONTINUOUS_FEATURES

logger = logging.getLogger(__name__)


class FeatureEncoder:
    """特征编码器：原始数据 → field_indices + continuous_features"""

    # 分类字段中 unknown/missing 值的固定索引 = 0
    UNKNOWN_INDEX = 0
    # 低频词汇裁剪阈值：出现次数低于此值的 drug_candidate 映射到 __RARE__
    RARE_FREQ_THRESHOLD = 2

    def __init__(self):
        self.vocab_maps: Dict[str, Dict[str, int]] = {}
        self.reverse_maps: Dict[str, Dict[int, str]] = {}
        self.field_dims: List[int] = []
        self.num_continuous: int = len(CONTINUOUS_FEATURES)
        self._fitted = False

    def fit(self, data: List[Dict[str, Any]]) -> 'FeatureEncoder':
        """从数据构建 vocab 映射和 field_dims

        对 drug_candidate 字段进行频率裁剪：出现次数低于 RARE_FREQ_THRESHOLD 的
        值映射到 __RARE__ token，大幅减少嵌入维度（1617→~500）。

        Args:
            data: 训练数据列表，每条包含所有字段值
        Returns:
            self（支持链式调用）
        """
        for field_name in FIELD_ORDER:
            vocab: Dict[str, int] = {'__unknown__': self.UNKNOWN_INDEX}
            values = set()
            freq: Dict[str, int] = {}

            for record in data:
                value = record.get(field_name)
                if value is not None:
                    str_value = str(value)
                    values.add(str_value)
                    freq[str_value] = freq.get(str_value, 0) + 1

            # 对 drug_candidate 字段进行频率裁剪
            if field_name == 'drug_candidate':
                rare_token = '__RARE__'
                pruned_values = set()
                pruned_count = 0
                for v in values:
                    if freq[v] >= self.RARE_FREQ_THRESHOLD:
                        pruned_values.add(v)
                    else:
                        pruned_count += 1
                logger.info(
                    f"drug_candidate vocab pruning: {len(values)} → {len(pruned_values)}, "
                    f"{pruned_count} rare values (<{self.RARE_FREQ_THRESHOLD} freq) → '{rare_token}'"
                )
                # 确保罕见词汇表中有 rare_token
                vocab[rare_token] = len(vocab)  # 先占位，后面排序后会重新编号
                values = pruned_values

            # 按排序顺序分配索引（从1开始，0留给unknown）
            for i, value in enumerate(sorted(values), start=1):
                vocab[value] = i

            self.vocab_maps[field_name] = vocab
            self.reverse_maps[field_name] = {v: k for k, v in vocab.items()}

        # field_dims = 每个字段词汇表大小
        self.field_dims = [len(self.vocab_maps[f]) for f in FIELD_ORDER]
        self._fitted = True

        logger.info(f"FeatureEncoder fitted: {len(FIELD_ORDER)} fields, "
                     f"field_dims={self.field_dims}, "
                     f"total_vocab={sum(self.field_dims)}")
        return self

    def transform(self, record: Dict[str, Any]) -> Tuple[List[int], List[float]]:
        """将一条记录转换为 field_indices + continuous_features

        Args:
            record: 包含所有字段值的字典
        Returns:
            field_indices: 字段索引列表（长度 = num_fields）
            continuous_features: 连续特征列表（长度 = num_continuous）
        """
        if not self._fitted:
            raise RuntimeError("FeatureEncoder must be fitted before transform")

        field_indices = []
        for field_name in FIELD_ORDER:
            value = record.get(field_name)
            vocab = self.vocab_maps[field_name]

            if value is None:
                field_indices.append(self.UNKNOWN_INDEX)
            else:
                str_value = str(value)
                idx = vocab.get(str_value)
                if idx is None:
                    # drug_candidate 字段：不在词汇表中的值映射到 __RARE__
                    rare_idx = vocab.get('__RARE__')
                    if rare_idx is not None:
                        field_indices.append(rare_idx)
                    else:
                        field_indices.append(self.UNKNOWN_INDEX)
                else:
                    field_indices.append(idx)

        continuous_features = []
        for feat_name in CONTINUOUS_FEATURES:
            raw_value = record.get(feat_name)
            if raw_value is not None:
                continuous_features.append(float(raw_value))
            else:
                continuous_features.append(0.0)

        return field_indices, continuous_features

    def inverse_transform(self, field_name: str, index: int) -> Optional[str]:
        """反向映射：字段索引 → 原始值（用于推荐解释）

        Args:
            field_name: 字段名
            index: 字段索引值
        Returns:
            原始值字符串，unknown 返回 None
        """
        if not self._fitted:
            raise RuntimeError("FeatureEncoder must be fitted before inverse_transform")

        reverse = self.reverse_maps.get(field_name, {})
        value = reverse.get(index)
        if value == '__unknown__':
            return None
        return value

    def get_field_dim(self, field_name: str) -> int:
        """获取指定字段的词汇表大小"""
        if not self._fitted:
            raise RuntimeError("FeatureEncoder must be fitted first")
        idx = FIELD_ORDER.index(field_name)
        return self.field_dims[idx]

    def save(self, path: str) -> None:
        """序列化 vocab 映射和 field_dims 到 JSON"""
        data = {
            'field_order': FIELD_ORDER,
            'continuous_features': CONTINUOUS_FEATURES,
            'field_dims': self.field_dims,
            'vocab_maps': self.vocab_maps,
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"FeatureEncoder saved to {path}")

    @classmethod
    def load(cls, path: str) -> 'FeatureEncoder':
        """从 JSON 反序列化 vocab 映射和 field_dims"""
        encoder = cls()
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        encoder.field_dims = data['field_dims']
        encoder.vocab_maps = data['vocab_maps']
        encoder.num_continuous = len(data['continuous_features'])

        # 构建 reverse_maps
        for field_name, vocab in encoder.vocab_maps.items():
            encoder.reverse_maps[field_name] = {v: k for k, v in vocab.items()}

        encoder._fitted = True
        logger.info(f"FeatureEncoder loaded from {path}: "
                     f"field_dims={encoder.field_dims}")
        return encoder
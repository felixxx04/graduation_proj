"""数据集划分器 — 按patient_id分组划分训练/验证/测试集

防止数据泄露：同一患者的所有样本必须在同一划分中。
划分比例：70% 训练 / 15% 验证 / 15% 测试
"""

import random
import logging
from typing import Dict, List, Any, Tuple

logger = logging.getLogger(__name__)


def split_by_patient(
    data: List[Dict[str, Any]],
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """按 patient_id 分组划分数据集

    确保同一患者的所有样本在同一划分中，防止数据泄露。

    Args:
        data: 训练样本列表，每条样本含 patient_id 字段
        train_ratio: 训练集比例
        val_ratio: 验证集比例
        test_ratio: 测试集比例
        seed: 随机种子
    Returns:
        train_data, val_data, test_data
    """
    if abs(train_ratio + val_ratio + test_ratio - 1.0) >= 1e-6:
        raise ValueError(
            f"Split ratios must sum to 1.0, got {train_ratio + val_ratio + test_ratio}"
        )

    # 按 patient_id 分组
    patient_groups: Dict[str, List[Dict[str, Any]]] = {}
    for record in data:
        patient_id = str(record.get('patient_id', 'unknown'))
        if patient_id not in patient_groups:
            patient_groups[patient_id] = []
        patient_groups[patient_id].append(record)

    # 随机划分患者
    patient_ids = list(patient_groups.keys())
    rng = random.Random(seed)
    rng.shuffle(patient_ids)

    n_total = len(patient_ids)
    n_train = int(n_total * train_ratio)
    n_val = int(n_total * val_ratio)

    train_ids = patient_ids[:n_train]
    val_ids = patient_ids[n_train:n_train + n_val]
    test_ids = patient_ids[n_train + n_val:]

    train_data = [r for pid in train_ids for r in patient_groups[pid]]
    val_data = [r for pid in val_ids for r in patient_groups[pid]]
    test_data = [r for pid in test_ids for r in patient_groups[pid]]

    logger.info(
        f"Dataset split: {len(train_ids)} patients ({len(train_data)} samples) train, "
        f"{len(val_ids)} patients ({len(val_data)} samples) val, "
        f"{len(test_ids)} patients ({len(test_data)} samples) test"
    )

    return train_data, val_data, test_data
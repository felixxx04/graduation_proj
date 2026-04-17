"""
患者特征处理器
将患者和药物数据转换为模型输入特征向量
支持词汇表版本管理与序列化
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import json
import logging
import hashlib

logger = logging.getLogger(__name__)

# 固定词汇表，确保跨模块一致性
DISEASE_VOCAB = [
    '高血压', '糖尿病', '冠心病', '高血脂', '哮喘',
    '慢性肾病', '肝炎', '胃溃疡', '关节炎', '抑郁症',
    '甲状腺疾病', '贫血', '痛风', '骨质疏松', '心衰',
    '脑梗塞', '帕金森', '癫痫', '肿瘤', '其他'
]

ALLERGY_VOCAB = [
    '青霉素', '磺胺类', '阿司匹林', '碘造影剂', '头孢类',
    '链霉素', '万古霉素', '喹诺酮类', '四环素类', '其他'
]

DRUG_CATEGORY_MAP = {
    '降糖药': 0, '降压药': 1, '降脂药': 2, '抗血小板药': 3,
    '消化系统用药': 4, '心血管用药': 5, '抗感染药': 6, '其他': 7
}

FEATURE_DIM = 200


def _safe_parse_json_list(value: Any) -> List[str]:
    """安全解析 JSON 列表字段，处理各种输入格式"""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        if not value.strip():
            return []
        # 支持中文逗号和英文逗号分隔
        if value.startswith('['):
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, list) else []
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Failed to parse JSON list: {value[:100]}")
                return []
        # 尝试逗号分隔
        return [item.strip() for item in value.replace('，', ',').split(',') if item.strip()]
    return []


class PatientFeatureProcessor:
    """患者特征处理器，支持词汇表版本管理与序列化"""

    VERSION = "2.0"

    def __init__(self):
        self.age_bins = [0, 18, 30, 45, 60, 75, 100]
        self.disease_vocab: Dict[str, int] = {d: i for i, d in enumerate(DISEASE_VOCAB)}
        self.drug_vocab: Dict[str, int] = {}
        self.allergy_vocab: Dict[str, int] = {a: i for i, a in enumerate(ALLERGY_VOCAB)}
        self._fitted = False
        self._drug_vocab_version: Optional[str] = None

    def fit(self, patients: List[Dict[str, Any]], drugs: List[Dict[str, Any]]) -> 'PatientFeatureProcessor':
        """
        从数据中学习词汇表

        Args:
            patients: 患者数据列表
            drugs: 药物数据列表

        Returns:
            self，支持链式调用

        Raises:
            ValueError: 输入数据为空或格式无效
        """
        if not patients and not drugs:
            raise ValueError("At least one of patients or drugs must be provided")

        # 构建药物词汇表
        if drugs:
            drug_names = set()
            for d in drugs:
                name = d.get('name')
                if not name:
                    logger.warning(f"Drug missing 'name' field: {d.get('id', 'unknown')}")
                    continue
                drug_names.add(name)
            self.drug_vocab = {d: i for i, d in enumerate(sorted(drug_names))}
            self._drug_vocab_version = self._compute_vocab_hash(self.drug_vocab)

        self._fitted = True
        logger.info(
            f"Preprocessor fitted: disease_vocab={len(self.disease_vocab)}, "
            f"drug_vocab={len(self.drug_vocab)}, allergy_vocab={len(self.allergy_vocab)}"
        )
        return self

    def transform_patient(self, patient: Dict[str, Any]) -> np.ndarray:
        """
        将患者数据转换为特征向量

        Args:
            patient: 患者数据字典

        Returns:
            特征向量 (numpy float32 array)

        Raises:
            ValueError: 患者数据格式无效
        """
        if not isinstance(patient, dict):
            raise ValueError(f"Patient must be a dict, got {type(patient)}")

        features: List[float] = []

        # 1. 年龄分箱 one-hot
        age = patient.get('age', 45)
        if age is None:
            age = 45
        try:
            age = float(age)
        except (TypeError, ValueError):
            logger.warning(f"Invalid age value: {patient.get('age')}, defaulting to 45")
            age = 45

        age_bin = np.digitize([age], self.age_bins)[0]
        age_onehot = np.zeros(len(self.age_bins) + 1)  # +1 防止 age > max_bin 越界
        age_bin = min(age_bin, len(age_onehot) - 1)  # 安全截断
        age_onehot[age_bin] = 1
        features.extend(age_onehot)

        # 2. 性别特征
        gender = patient.get('gender', '男')
        features.append(1 if (gender == '男' or gender == 'MALE') else 0)

        # 3. 慢性疾病 one-hot
        diseases = _safe_parse_json_list(patient.get('chronic_diseases'))
        disease_vec = np.zeros(len(self.disease_vocab))
        for d in diseases:
            if d in self.disease_vocab:
                disease_vec[self.disease_vocab[d]] = 1
            else:
                # 未知疾病归入"其他"类别
                if '其他' in self.disease_vocab:
                    disease_vec[self.disease_vocab['其他']] = 1
        features.extend(disease_vec)

        # 4. 过敏史 one-hot
        allergies = _safe_parse_json_list(patient.get('allergies'))
        allergy_vec = np.zeros(len(self.allergy_vocab))
        for a in allergies:
            if a == '无':
                continue
            if a in self.allergy_vocab:
                allergy_vec[self.allergy_vocab[a]] = 1
            elif '其他' in self.allergy_vocab:
                allergy_vec[self.allergy_vocab['其他']] = 1
        features.extend(allergy_vec)

        return np.array(features, dtype=np.float32)

    def transform_drug(self, drug: Dict[str, Any]) -> np.ndarray:
        """
        将药物数据转换为特征向量

        Args:
            drug: 药物数据字典

        Returns:
            特征向量 (numpy float32 array)

        Raises:
            ValueError: 药物数据格式无效
        """
        if not isinstance(drug, dict):
            raise ValueError(f"Drug must be a dict, got {type(drug)}")

        features: List[float] = []

        # 1. 药物类别 one-hot
        category = drug.get('category', '')
        cat_vec = np.zeros(len(DRUG_CATEGORY_MAP))
        cat_idx = DRUG_CATEGORY_MAP.get(category, DRUG_CATEGORY_MAP.get('其他', len(DRUG_CATEGORY_MAP) - 1))
        cat_vec[cat_idx] = 1
        features.extend(cat_vec)

        # 2. 适应症特征（使用确定性编码替代 hash）
        indications = _safe_parse_json_list(drug.get('indications'))
        for i in range(5):
            if i < len(indications):
                # 使用 MD5 哈希确保确定性
                encoded = int(hashlib.md5(indications[i].encode('utf-8')).hexdigest()[:8], 16) % 100 / 100.0
                features.append(encoded)
            else:
                features.append(0.0)

        return np.array(features, dtype=np.float32)

    def get_field_dims(self) -> List[int]:
        """获取各字段维度，用于 DeepFM 初始化"""
        return [
            len(self.age_bins) + 1,  # age one-hot (含溢出位)
            2,                       # gender
            len(self.disease_vocab),
            len(self.allergy_vocab),
            len(DRUG_CATEGORY_MAP),  # drug category
            5,                       # indications
        ]

    def to_state(self) -> Dict[str, Any]:
        """序列化处理器状态，用于版本管理"""
        return {
            'version': self.VERSION,
            'age_bins': self.age_bins,
            'disease_vocab': self.disease_vocab,
            'drug_vocab': self.drug_vocab,
            'allergy_vocab': self.allergy_vocab,
            'drug_vocab_version': self._drug_vocab_version,
            'fitted': self._fitted,
        }

    @classmethod
    def from_state(cls, state: Dict[str, Any]) -> 'PatientFeatureProcessor':
        """从序列化状态恢复处理器"""
        processor = cls()
        if state.get('version') != cls.VERSION:
            logger.warning(
                f"Preprocessor version mismatch: loaded={state.get('version')}, "
                f"current={cls.VERSION}. Vocabularies may be incompatible."
            )
        processor.age_bins = state.get('age_bins', processor.age_bins)
        processor.disease_vocab = state.get('disease_vocab', processor.disease_vocab)
        processor.drug_vocab = state.get('drug_vocab', processor.drug_vocab)
        processor.allergy_vocab = state.get('allergy_vocab', processor.allergy_vocab)
        processor._drug_vocab_version = state.get('drug_vocab_version')
        processor._fitted = state.get('fitted', False)
        return processor

    @staticmethod
    def _compute_vocab_hash(vocab: Dict[str, int]) -> str:
        """计算词汇表哈希，用于版本校验"""
        content = json.dumps(vocab, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(content.encode('utf-8')).hexdigest()[:12]

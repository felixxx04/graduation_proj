"""Pipeline 入口 — 串联特征编码、标签生成、数据划分、数据集构建

v3: 智能配对替代全配对 — 三阶段采样解决96.4%标签0.05问题

全配对问题: 718药物×110患者=79K样本, 96.4%标签0.05(无适应症), 模型学不到有效信号
智能配对: (1)适应症匹配正样本 (2)禁忌/过敏硬负样本 (3)少量随机中性样本
"""

import logging
import json
import random
from typing import Dict, List, Any, Optional, Set
from pathlib import Path

from app.pipeline.feature_encoder import FeatureEncoder
from app.pipeline.labeler import compute_label, apply_label_smoothing
from app.pipeline.splitter import split_by_patient
from app.pipeline.dataset import DrugRecommendationDataset
from app.pipeline.schema import FIELD_ORDER, CONTINUOUS_FEATURES
from app.pipeline.record_builder import build_feature_record
from app.utils.clinical_matcher import match_indication, normalize_disease, match_allergy, match_condition
from app.config import settings

logger = logging.getLogger(__name__)


class PipelineRunner:
    """数据管道入口：原始数据 → 训练数据集"""

    def __init__(self):
        self.encoder = FeatureEncoder()
        self.contraindication_map: Dict[str, List[Dict]] = {}
        self.interaction_map: Dict[str, List[Dict]] = {}
        self.indication_map: Dict[str, List[Dict]] = {}

    def load_safety_data(
        self,
        contraindications: Dict[str, List[Dict[str, Any]]],
        interactions: Dict[str, List[Dict[str, Any]]],
    ) -> None:
        """加载禁忌症和交互数据"""
        self.contraindication_map = contraindications
        self.interaction_map = interactions
        logger.info(
            f"Loaded safety data: {len(contraindications)} drugs with contraindications, "
            f"{len(interactions)} drugs with interactions"
        )

    def load_indication_data(
        self,
        indication_map: Dict[str, List[Dict[str, Any]]],
    ) -> None:
        """加载适应症映射数据并标准化type值

        标准化规则:
        - "Supportive" → "Adjunctive" (辅助/佐剂治疗)
        - 空值/None → "On Label" (默认为标准适应症)
        - 其他值保持不变
        """
        TYPE_NORMALIZE = {
            'supportive': 'Adjunctive',
            '': 'On Label',
        }
        normalized_map = {}
        normalize_count = 0
        for drug_name, indications in indication_map.items():
            normalized_indications = []
            for ind in indications:
                if isinstance(ind, dict):
                    raw_type = str(ind.get('type', '')).strip()
                    normalized_type = TYPE_NORMALIZE.get(raw_type.lower(), raw_type)
                    if normalized_type != raw_type:
                        normalize_count += 1
                    normalized_ind = {**ind, 'type': normalized_type}
                    normalized_indications.append(normalized_ind)
                else:
                    normalized_indications.append(ind)
            normalized_map[drug_name] = normalized_indications
        self.indication_map = normalized_map
        logger.info(
            f"Loaded indication data: {len(normalized_map)} drugs, "
            f"normalized {normalize_count} type values"
        )

    def build_training_samples(
        self,
        patients: List[Dict[str, Any]],
        drugs: List[Dict[str, Any]],
        max_random_negatives_per_patient: int = 10,
        seed: int = 42,
    ) -> List[Dict[str, Any]]:
        """智能配对构建训练样本 — 三阶段采样替代全配对

        阶段1: 适应症匹配 — 患者疾病 × 有对应适应症的药物 → 正样本+部分负样本
        阶段2: 禁忌/过敏硬负样本 — 患者有禁忌/过敏 × 对应药物 → 硬负样本(label=0.0)
        阶段3: 随机中性样本 — 每患者随机采样少量无适应症也无禁忌的药物 → label=0.05

        Args:
            patients: 患者数据列表
            drugs: 药物数据列表
            max_random_negatives_per_patient: 每患者最大随机中性样本数
            seed: 随机种子
        Returns:
            训练样本列表
        """
        rng = random.Random(seed)

        # 构建 patient_id → allergies 映射
        patient_allergies_map: Dict[str, List[str]] = {}
        patient_chronic_map: Dict[str, List[str]] = {}
        patient_meds_map: Dict[str, List[str]] = {}

        for patient in patients:
            pid = patient.get('id', patient.get('patient_id', 'unknown'))
            allergies = patient.get('allergies', []) or patient.get('allergy_list', []) or []
            if allergies:
                patient_allergies_map[pid] = allergies
            chronic = patient.get('chronic_diseases', []) or []
            if chronic:
                patient_chronic_map[pid] = chronic
            meds = patient.get('current_medications', []) or patient.get('medication_list', []) or []
            if meds:
                patient_meds_map[pid] = [str(m) for m in meds if m and m != '__unknown__']

        # 构建药物名→适应症条件的快速索引
        drug_indication_index: Dict[str, Set[str]] = {}
        drug_name_set: Set[str] = set()
        for drug in drugs:
            drug_name = drug.get('generic_name', drug.get('name', ''))
            drug_name_set.add(drug_name.lower())
            indications = self.indication_map.get(drug_name, [])
            conditions = set()
            for ind in indications:
                if isinstance(ind, dict):
                    cond = str(ind.get('condition', '')).lower()
                else:
                    cond = str(ind).lower()
                if cond:
                    conditions.add(normalize_disease(cond))
            drug_indication_index[drug_name.lower()] = conditions

        # ===== 阶段1+2: 适应症匹配 + 禁忌/过敏配对 =====
        paired_set: Set[tuple] = set()  # (pid, drug_name) 防止重复
        paired_drugs: List[Dict[str, Any]] = []

        # 患者条件标准化集合（用于快速匹配）
        patient_condition_sets: Dict[str, Set[str]] = {}
        for patient in patients:
            pid = patient.get('id', patient.get('patient_id', 'unknown'))
            conditions = set()
            for d in patient.get('diseases', []) or []:
                if d and d != '__unknown__':
                    conditions.add(normalize_disease(str(d).lower()))
            for d in patient.get('chronic_diseases', []) or []:
                if d and d != '__unknown__':
                    conditions.add(normalize_disease(str(d).lower()))
            patient_condition_sets[pid] = conditions

        # 阶段1: 适应症匹配配对
        indication_pairs = 0
        for patient in patients:
            pid = patient.get('id', patient.get('patient_id', 'unknown'))
            patient_conditions_norm = patient_condition_sets.get(pid, set())

            for drug in drugs:
                drug_name = drug.get('generic_name', drug.get('name', ''))
                drug_conditions = drug_indication_index.get(drug_name.lower(), set())

                # 检查是否有适应症匹配
                has_match = False
                for p_cond in patient_conditions_norm:
                    for d_cond in drug_conditions:
                        if match_indication({p_cond}, d_cond):
                            has_match = True
                            break
                    if has_match:
                        break

                if has_match:
                    pair_key = (pid, drug_name)
                    if pair_key not in paired_set:
                        paired_set.add(pair_key)
                        paired_drugs.append({'patient': patient, 'drug': drug})
                        indication_pairs += 1

        # 阶段2: 禁忌/过敏硬负样本配对
        contra_pairs = 0
        for patient in patients:
            pid = patient.get('id', patient.get('patient_id', 'unknown'))

            for drug in drugs:
                drug_name = drug.get('generic_name', drug.get('name', ''))
                contraindications = self.contraindication_map.get(drug_name, [])

                # 检查是否有禁忌匹配（绝对/相对禁忌或过敏）
                has_contra = False
                for contra in contraindications:
                    contra_type = contra.get('contraindication_type', 'disease')
                    contra_name = str(contra.get('contraindication_name', ''))

                    if contra_type == 'allergy_type':
                        # 检查过敏匹配
                        patient_allergies = set()
                        for a in (patient.get('allergies', []) or patient.get('allergy_list', []) or []):
                            if a and a != '__unknown__':
                                patient_allergies.add(str(a).lower())
                        if match_allergy(patient_allergies, contra_name):
                            has_contra = True
                            break
                    elif contra_type == 'drug_class':
                        # 检查当前用药类匹配
                        meds_set = {str(m).lower() for m in (patient.get('current_medications', []) or []) if m and m != '__unknown__'}
                        if match_condition(meds_set, contra_name):
                            has_contra = True
                            break
                    else:
                        if match_indication(patient_condition_sets.get(pid, set()), contra_name):
                            # 禁忌与患者疾病匹配（反向使用match_indication）
                            # 注意: match_indication用于疾病匹配，禁忌也是疾病
                            has_contra = True
                            break

                if has_contra:
                    pair_key = (pid, drug_name)
                    if pair_key not in paired_set:
                        paired_set.add(pair_key)
                        paired_drugs.append({'patient': patient, 'drug': drug})
                        contra_pairs += 1

        # ===== 阶段3: 随机中性样本 =====
        # 构建 pid → 已配对药物名集合 的快速索引
        patient_paired_drugs: Dict[str, Set[str]] = {}
        for (pid, dname) in paired_set:
            if pid not in patient_paired_drugs:
                patient_paired_drugs[pid] = set()
            patient_paired_drugs[pid].add(dname)

        random_pairs = 0
        for patient in patients:
            pid = patient.get('id', patient.get('patient_id', 'unknown'))
            already_paired_names = patient_paired_drugs.get(pid, set())

            # 可选的未配对药物
            unpaired_drugs = [
                drug for drug in drugs
                if drug.get('generic_name', drug.get('name', '')) not in already_paired_names
            ]

            # 随机采样少量
            sample_count = min(max_random_negatives_per_patient, len(unpaired_drugs))
            sampled = rng.sample(unpaired_drugs, sample_count) if unpaired_drugs else []

            for drug in sampled:
                paired_drugs.append({'patient': patient, 'drug': drug})
                random_pairs += 1

        logger.info(
            f"智能配对: {indication_pairs} 适应症配对 + "
            f"{contra_pairs} 禁忌配对 + {random_pairs} 随机中性配对 = "
            f"{len(paired_drugs)} 总配对"
        )

        # ===== 构建特征记录 + 标签 + 编码 =====
        # 先构建原始数据用于 fit encoder
        raw_field_data = []
        for pair in paired_drugs:
            record = self._build_raw_record(pair['patient'], pair['drug'])
            raw_field_data.append(record)

        # Fit encoder
        self.encoder.fit(raw_field_data)

        # 生成标签和编码后的样本
        all_records = []
        for record in raw_field_data:
            patient_data = self._extract_patient_from_record(
                record, patient_allergies_map, patient_chronic_map, patient_meds_map,
            )
            drug_data = self._extract_drug_from_record(record)

            label, safety_flags = compute_label(
                patient_data, drug_data,
                self.contraindication_map, self.interaction_map,
            )

            smoothed_label = apply_label_smoothing(label)

            field_indices, continuous_features = self.encoder.transform(record)

            sample = {
                'patient_id': record.get('patient_id', 'unknown'),
                'drug_id': record.get('drug_candidate', 'unknown'),
                'field_indices': field_indices,
                'continuous_features': continuous_features,
                'label': smoothed_label,
                'raw_label': label,
                'safety_flags': safety_flags,
            }
            all_records.append(sample)

        logger.info(f"Built {len(all_records)} training samples (智能配对)")
        return all_records

    def run(
        self,
        patients: List[Dict[str, Any]],
        drugs: List[Dict[str, Any]],
        seed: int = 42,
    ) -> Dict[str, Any]:
        """完整管道运行

        自动加载pipeline_data.json中的safety/indication数据
        （仅当外部未预加载时才自动加载，允许外部覆盖）

        Returns:
            训练+验证+测试数据集, encoder, field_dims, 标签分布
        """
        # 防御性加载: 如果safety/indication数据未预加载，自动从pipeline_data.json读取
        if not self.contraindication_map or not self.indication_map:
            pipeline_path = Path(settings.data_dir) / "pipeline_data.json"
            if pipeline_path.exists():
                with open(pipeline_path, 'r', encoding='utf-8') as f:
                    pipeline_data = json.load(f)
                if not self.contraindication_map:
                    self.contraindication_map = pipeline_data.get('contraindication_map', {})
                    logger.info(f"Auto-loaded {len(self.contraindication_map)} contraindication entries")
                if not self.interaction_map:
                    self.interaction_map = pipeline_data.get('interaction_map', {})
                    logger.info(f"Auto-loaded {len(self.interaction_map)} interaction entries")
                if not self.indication_map:
                    self.indication_map = pipeline_data.get('indication_map', {})
                    logger.info(f"Auto-loaded {len(self.indication_map)} indication entries")
            else:
                logger.warning(
                    f"pipeline_data.json not found at {pipeline_path}. "
                    f"Safety/indication data empty — 智能配对将无法匹配适应症/禁忌！"
                )
        # 智能配对构建训练样本
        samples = self.build_training_samples(patients, drugs, seed=seed)

        # 按患者划分 (FocalLoss处理不平衡)
        train_data, val_data, test_data = split_by_patient(samples, seed=seed)

        train_dataset = DrugRecommendationDataset(train_data)
        val_dataset = DrugRecommendationDataset(val_data)
        test_dataset = DrugRecommendationDataset(test_data)

        # 标签分布统计
        label_dist = {}
        for s in samples:
            key = round(s['raw_label'], 1)
            label_dist[key] = label_dist.get(key, 0) + 1

        logger.info(f"Label distribution: {label_dist}")

        return {
            'train_dataset': train_dataset,
            'val_dataset': val_dataset,
            'test_dataset': test_dataset,
            'encoder': self.encoder,
            'field_dims': self.encoder.field_dims,
            'label_distribution': label_dist,
        }

    def _build_raw_record(
        self, patient: Dict[str, Any], drug: Dict[str, Any]
    ) -> Dict[str, Any]:
        """构建原始特征记录（使用共享record_builder）"""
        return build_feature_record(patient, drug)

    def _extract_patient_from_record(
        self,
        record: Dict,
        patient_allergies_map: Optional[Dict[str, List[str]]] = None,
        patient_chronic_map: Optional[Dict[str, List[str]]] = None,
        patient_meds_map: Optional[Dict[str, List[str]]] = None,
    ) -> Dict:
        """从原始记录提取患者数据（用于标签计算）"""
        pid = record.get('patient_id', 'unknown')

        allergies: List[str] = []
        if patient_allergies_map and pid in patient_allergies_map:
            allergies = patient_allergies_map[pid]

        chronic_diseases: List[str] = []
        if patient_chronic_map and pid in patient_chronic_map:
            chronic_diseases = patient_chronic_map[pid]

        current_medications: List[str] = []
        if patient_meds_map and pid in patient_meds_map:
            current_medications = patient_meds_map[pid]
        else:
            med1 = record.get('med_class_1', '__unknown__')
            med2 = record.get('med_class_2', '__unknown__')
            med3 = record.get('med_class_3', '__unknown__')
            med4 = record.get('med_class_4', '__unknown__')
            current_medications = [m for m in [med1, med2, med3, med4] if m != '__unknown__']

        return {
            'diseases': [record.get('primary_disease'), record.get('secondary_disease')],
            'chronic_diseases': chronic_diseases,
            'allergies': allergies,
            'current_medications': current_medications,
        }

    def _extract_drug_from_record(self, record: Dict) -> Dict:
        """从原始记录提取药物数据（用于标签计算）"""
        drug_name = record.get('drug_candidate', '__unknown__')
        indications = self.indication_map.get(drug_name, [])

        return {
            'generic_name': drug_name,
            'name': drug_name,
            'drug_class': record.get('drug_class', '__unknown__'),
            'pregnancy_category': record.get('pregnancy_cat', 'N'),
            'indications': indications,
        }
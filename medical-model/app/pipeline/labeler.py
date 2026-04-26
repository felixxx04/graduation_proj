"""标签生成器 — 为 (patient, drug) 配对生成训练标签

v2: 使用clinical_matcher替代子串匹配, 统一安全逻辑

标签逻辑（修订版）：
- 绝对禁忌冲突 → 0.0（硬排除，不可被概率模型或DP噪声绕过）
- 过敏冲突 → 0.0
- 严重药物交互 → 0.0
- 适应症完全匹配（primary/on-label） → 1.0
- 适应症部分匹配（off-label） → 0.7
- 有适应症 + 中度交互 → 1.0 × 0.7 = 0.7（叠加而非独立降权）
- 有适应症 + 相对禁忌 → 1.0 × 0.5 = 0.5
- 无适应症无禁忌 → 0.05（不应推荐无适应症药物）

标签平滑：仅对正标签平滑（1.0→0.95），禁忌/硬排除样本0.0保持不变
"""

import logging
from typing import Dict, List, Set, Tuple, Any, Optional

from app.utils.clinical_matcher import match_condition, match_allergy, match_indication

logger = logging.getLogger(__name__)

# 标签平滑参数
LABEL_SMOOTHING_EPSILON = 0.05


def compute_label(
    patient_data: Dict[str, Any],
    drug_data: Dict[str, Any],
    contraindication_map: Dict[str, List[Dict[str, Any]]],
    interaction_map: Dict[str, List[Dict[str, Any]]],
) -> Tuple[float, Dict[str, Any]]:
    """计算 (patient, drug) 配对的标签值和安全标记

    标签体系（修订版）：
    - 绝对禁忌/过敏/严重交互 → 0.0（硬排除）
    - 适应症匹配: primary=1.0, off_label=0.7
    - 修饰因子叠加: 中度交互×0.7, 相对禁忌×0.5
    - 无适应症无禁忌 → 0.05（不应推荐）

    Args:
        patient_data: 患者数据（含 diseases, allergies, current_medications）
        drug_data: 药物数据（含 indications, drug_class, pregnancy_category）
        contraindication_map: 禁忌症映射 drug_name → [contraindication_list]
        interaction_map: 药物交互映射 drug_name → [interaction_list]
    Returns:
        label: 标签值 (0.0-1.0)
        safety_flags: 安全标记字典
    """
    safety_flags = {
        'has_absolute_contraindication': False,
        'has_relative_contraindication': False,
        'has_allergy_conflict': False,
        'has_major_interaction': False,
        'has_moderate_interaction': False,
        'has_indication_match': False,
        'evidence_level': 'none',
        'efficacy_tier': 'none',  # 疗效层级: high/medium/low/none
        'exclusion_reasons': [],
        'warning_reasons': [],
    }

    drug_name = drug_data.get('generic_name', drug_data.get('name', ''))

    # 收集患者条件集合 (v2: clinical_matcher需标准化集合)
    patient_conditions: Set[str] = set()
    for d in patient_data.get('diseases', []) or []:
        if d and d != '__unknown__':
            patient_conditions.add(str(d).lower())
    for d in patient_data.get('chronic_diseases', []) or []:
        if d and d != '__unknown__':
            patient_conditions.add(str(d).lower())

    # 收集患者过敏集合
    patient_allergies_raw: Set[str] = set()
    for a in patient_data.get('allergies', []) or []:
        if a and a != '__unknown__':
            patient_allergies_raw.add(str(a).lower())

    # 收集当前用药名集合(用于drug_class类禁忌匹配)
    current_meds = patient_data.get('current_medications', []) or []
    patient_current_med_classes: Set[str] = {
        str(m).lower() for m in current_meds if m and m != '__unknown__'
    }

    contraindications = contraindication_map.get(drug_name, [])
    relative_contra_modifiers: List[float] = []

    # 1. 禁忌冲突检查 — absolute → 0.0（硬排除）(v2: clinical_matcher)
    for contra in contraindications:
        contra_name = str(contra.get('contraindication_name', ''))
        severity = contra.get('severity', 'relative')
        contra_type = contra.get('contraindication_type', 'disease')

        if severity == 'absolute':
            # 绝对禁忌 → 立即排除
            matched = False
            if contra_type == 'allergy_type':
                matched = match_allergy(patient_allergies_raw, contra_name)
            elif contra_type == 'drug_class':
                matched = match_condition(patient_current_med_classes, contra_name)
            else:
                matched = match_condition(patient_conditions, contra_name)
            if matched:
                safety_flags['has_absolute_contraindication'] = True
                safety_flags['exclusion_reasons'].append(
                    f"绝对禁忌冲突: {contra_name}"
                )
                return 0.0, safety_flags
        elif severity == 'relative':
            # 相对禁忌 → 修饰因子 ×0.5（叠加）
            matched = False
            if contra_type == 'allergy_type':
                matched = match_allergy(patient_allergies_raw, contra_name)
            elif contra_type == 'drug_class':
                matched = match_condition(patient_current_med_classes, contra_name)
            else:
                matched = match_condition(patient_conditions, contra_name)
            if matched:
                safety_flags['has_relative_contraindication'] = True
                safety_flags['warning_reasons'].append(
                    f"相对禁忌: {contra_name}"
                )
                relative_contra_modifiers.append(0.5)

    # 2. 过敏冲突检查 → 0.0（硬排除）(v2: clinical_matcher精确匹配)
    for contra in contraindications:
        if contra.get('contraindication_type') == 'allergy_type':
            contra_name = str(contra.get('contraindication_name', ''))
            if match_allergy(patient_allergies_raw, contra_name):
                safety_flags['has_allergy_conflict'] = True
                safety_flags['exclusion_reasons'].append(
                    f"过敏冲突: {contra.get('contraindication_name', '')}"
                )
                return 0.0, safety_flags

    # 3. 严重药物交互检查 → 0.0（硬排除）
    interactions = interaction_map.get(drug_name, [])
    moderate_interaction_modifiers: List[float] = []

    for interaction in interactions:
        inter_type = interaction.get('interaction_type', 'minor')
        if inter_type == 'major':
            other_drug = interaction.get('drug_a', interaction.get('drug_b', ''))
            if other_drug == drug_name:
                # 取另一个药物名
                other_drug = interaction.get('drug_b', interaction.get('drug_a', ''))
            # v2: 使用标准化匹配(药物名可能有多种写法)
            other_lower = other_drug.lower()
            if any(str(m).lower() == other_lower for m in current_meds
                   if m and m != '__unknown__'):
                safety_flags['has_major_interaction'] = True
                safety_flags['exclusion_reasons'].append(
                    f"严重交互: {drug_name} + {other_drug}"
                )
                return 0.0, safety_flags
        elif inter_type == 'moderate':
            other_drug = interaction.get('drug_a', interaction.get('drug_b', ''))
            if other_drug == drug_name:
                other_drug = interaction.get('drug_b', interaction.get('drug_a', ''))
            other_lower = other_drug.lower()
            if any(str(m).lower() == other_lower for m in current_meds
                   if m and m != '__unknown__'):
                safety_flags['has_moderate_interaction'] = True
                safety_flags['warning_reasons'].append(
                    f"中度交互: {drug_name} + {other_drug}"
                )
                moderate_interaction_modifiers.append(0.7)

    # 4. 适应症匹配检查 — 引入 evidence_level (v2: clinical_matcher)
    drug_indications: Set[str] = set()
    indication_details: List[Dict[str, Any]] = []

    for ind in drug_data.get('indications', []) or []:
        # 如果 indications 是结构化数据(dict)，提取 condition 字段
        if isinstance(ind, dict):
            ind_str = str(ind.get('condition', '')).lower()
            indication_details.append(ind)
        else:
            ind_str = str(ind).lower()
        if ind_str:
            drug_indications.add(ind_str)

    # v2: 使用match_indication替代简单集合交集
    matching_diseases: Set[str] = set()
    for ind in drug_indications:
        if match_indication(patient_conditions, ind):
            matching_diseases.add(ind)

    if matching_diseases:
        safety_flags['has_indication_match'] = True

        # 确定 evidence_level: primary(on-label)=1.0, off_label=0.7
        best_evidence = 0.7  # 默认 off_label
        for detail in indication_details:
            if detail.get('type', '').lower() == 'on label':
                best_evidence = 1.0
                break

        # 如果没有结构化数据但有字符串匹配，默认为 primary
        if not indication_details and matching_diseases:
            best_evidence = 1.0

        safety_flags['evidence_level'] = 'primary' if best_evidence == 1.0 else 'off_label'

        # 疗效层级判断 — 基于药物类别和证据等级
        drug_class = str(drug_data.get('drug_class_en',
                        drug_data.get('category', ''))).lower()
        # 抗生素/抗感染 → 高疗效（针对性感染治疗）
        high_efficacy_keywords = ('antibiotic', 'antifungal', 'antiviral',
                                  'anti-infective', 'antiparasitic')
        # 辅助/对症 → 低疗效
        low_efficacy_keywords = ('supplement', 'vitamin', 'palliative',
                                 'analgesic', 'antipyretic', 'symptomatic')

        if any(kw in drug_class for kw in high_efficacy_keywords) and best_evidence == 1.0:
            safety_flags['efficacy_tier'] = 'high'
        elif any(kw in drug_class for kw in low_efficacy_keywords):
            safety_flags['efficacy_tier'] = 'low'
        else:
            safety_flags['efficacy_tier'] = 'medium'

        label = best_evidence
    else:
        # 无适应症匹配 → 0.05（不应推荐无适应症药物）
        safety_flags['evidence_level'] = 'none'
        label = 0.05

    # 5. 修饰因子叠加（而非独立降权）
    # 有适应症 + 中度交互 = label × 0.7
    # 有适应症 + 相对禁忌 = label × 0.5
    for modifier in moderate_interaction_modifiers:
        label *= modifier

    for modifier in relative_contra_modifiers:
        label *= modifier

    return label, safety_flags


def apply_label_smoothing(label: float) -> float:
    """应用标签平滑：仅对正标签平滑（1.0→0.95），禁忌/硬排除0.0保持不变

    修订：0.0 不再被平滑到 0.05，因为 0.0 代表硬排除（绝对禁忌/过敏/严重交互）
    不应被模型学习为"有一点推荐价值"。中性样本 0.05 也不需平滑。
    """
    if label >= 1.0:
        return 1.0 - LABEL_SMOOTHING_EPSILON
    return label
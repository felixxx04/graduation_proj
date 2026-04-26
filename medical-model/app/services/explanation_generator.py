"""推荐可解释性生成器 — 利用三层架构信息+DeepFM特征归因生成推荐解释

生成内容:
- 适应症匹配详情 (哪种疾病匹配了哪个适应症, 证据等级)
- 禁忌排除详情 (哪些药物被排除及原因)
- 交互检查详情 (当前用药与候选药物的交互)
- 特征归因 (DeepFM各字段对排序分数的贡献度)
- 证据等级 (On Label / Off Label / 无适应症)
"""

import logging
from typing import Dict, List, Any, Optional, Set

import torch
import numpy as np

from app.utils.clinical_matcher import match_indication, normalize_disease
from app.pipeline.schema import FIELD_ORDER

logger = logging.getLogger(__name__)


def generate_explanation(
    patient_data: Dict[str, Any],
    drug: Dict[str, Any],
    raw_score: float,
    mode: str,
    safety_flags: Optional[Dict[str, Any]] = None,
    embeds: Optional[torch.Tensor] = None,
    field_indices: Optional[List[int]] = None,
    encoder: Optional[Any] = None,
    contraindication_map: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    interaction_map: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> Dict[str, Any]:
    """生成单个药物推荐的结构化解释

    Args:
        patient_data: 患者数据
        drug: 药物数据
        raw_score: 原始排序分(无DP噪声)
        mode: 推荐模式('model'或'demo')
        safety_flags: Layer 2 RuleMarker输出的安全标记
        embeds: DeepFM嵌入向量 [num_fields, embed_dim]
        field_indices: 编码后的字段索引列表
        encoder: FeatureEncoder实例(用于inverse_transform)
        contraindication_map: 禁忌症映射
        interaction_map: 交互映射
    Returns:
        explanation: {features, warnings, indication_detail, safety_detail, evidence_level}
    """
    drug_name = drug.get('generic_name', drug.get('name', ''))

    # 收集患者疾病集合
    patient_conditions = _collect_conditions(patient_data)

    # 1. 适应症匹配详情
    indication_detail = _build_indication_detail(
        patient_conditions, drug, raw_score,
    )

    # 2. 特征归因 (模型模式)
    features = _build_feature_attribution(
        embeds, field_indices, encoder, mode,
    )

    # 3. 安全警告 (从safety_flags整合)
    warnings = _build_safety_warnings(
        drug_name, safety_flags, patient_data, drug,
        contraindication_map, interaction_map,
    )

    # 4. 禁忌症详情
    contraindication_detail = _build_contraindication_detail(
        drug_name, patient_data, drug, contraindication_map,
    )

    # 5. 交互检查详情
    interaction_detail = _build_interaction_detail(
        drug_name, patient_data, interaction_map,
    )

    # 6. 证据等级
    evidence_level = indication_detail.get('evidenceLevel', 'unknown')

    return {
        'features': features,
        'warnings': warnings,
        'indicationDetail': indication_detail,
        'contraindicationDetail': contraindication_detail,
        'interactionDetail': interaction_detail,
        'evidenceLevel': evidence_level,
    }


def _collect_conditions(patient_data: Dict[str, Any]) -> Set[str]:
    """收集患者疾病集合(标准化后)"""
    conditions: Set[str] = set()
    for d in patient_data.get('diseases', []) or []:
        if d and d != '__unknown__':
            conditions.add(normalize_disease(str(d).lower()))
    for d in patient_data.get('chronic_diseases', []) or []:
        if d and d != '__unknown__':
            conditions.add(normalize_disease(str(d).lower()))
    return conditions


def _build_indication_detail(
    patient_conditions: Set[str],
    drug: Dict[str, Any],
    raw_score: float,
) -> Dict[str, Any]:
    """构建适应症匹配详情

    Returns:
        {matched_indications: [...], evidence_level: str, matched_disease: str|None}
    """
    indications = drug.get('indications', []) or []
    matched: List[Dict[str, Any]] = []
    best_evidence = 'unknown'
    matched_disease = None

    for ind in indications:
        if isinstance(ind, dict):
            ind_condition = str(ind.get('condition', '')).lower()
            ind_type = ind.get('type', 'On Label')
        else:
            ind_condition = str(ind).lower()
            ind_type = 'On Label'

        if match_indication(patient_conditions, ind_condition):
            matched.append({
                'condition': ind_condition,
                'evidence': ind_type,
            })
            # 证据等级优先级: On Label > Off Label > Supportive
            if ind_type.lower() == 'on label':
                best_evidence = 'on_label'
                matched_disease = ind_condition
            elif ind_type.lower() == 'off label' and best_evidence != 'on_label':
                best_evidence = 'off_label'
                matched_disease = ind_condition
            elif best_evidence == 'unknown':
                best_evidence = ind_type.lower().replace(' ', '_')
                matched_disease = ind_condition

    if not matched and raw_score <= 0.1:
        best_evidence = 'no_indication'

    return {
        'matchedIndications': matched,
        'evidenceLevel': best_evidence,
        'matchedDisease': matched_disease,
    }


def _build_feature_attribution(
    embeds: Optional[torch.Tensor],
    field_indices: Optional[List[int]],
    encoder: Optional[Any],
    mode: str,
) -> List[Dict[str, Any]]:
    """构建特征归因列表

    利用DeepFM嵌入向量的L2范数衡量各字段对推荐的贡献度。
    范数越大的字段对排序分数影响越大。
    """
    if mode != 'model' or embeds is None or field_indices is None or encoder is None:
        return []

    features: List[Dict[str, Any]] = []

    try:
        # embeds: [num_fields, embed_dim]
        embeds_np = embeds.detach().cpu().numpy()
        norms = np.linalg.norm(embeds_np, axis=1)  # [num_fields]
        total_norm = norms.sum()

        if total_norm < 1e-8:
            return []

        # 按贡献度排序
        for i, field_name in enumerate(FIELD_ORDER):
            if i >= len(norms):
                break

            contribution = float(norms[i] / total_norm)

            # 只展示贡献度 > 5% 的字段
            if contribution < 0.05:
                continue

            # 反向映射获取原始值
            raw_value = None
            if i < len(field_indices):
                raw_value = encoder.inverse_transform(field_name, field_indices[i])

            features.append({
                'field': field_name,
                'contribution': round(contribution, 3),
                'value': raw_value,
            })

        # 按贡献度降序排列
        features.sort(key=lambda x: x['contribution'], reverse=True)

    except Exception as e:
        logger.warning(f"Feature attribution failed: {e}")

    return features


def _build_contraindication_detail(
    drug_name: str,
    patient_data: Dict[str, Any],
    drug: Dict[str, Any],
    contraindication_map: Optional[Dict[str, List[Dict[str, Any]]]],
) -> List[Dict[str, Any]]:
    """构建禁忌症详情列表

    返回与当前患者状态相关的结构化禁忌症信息，包括:
    - 禁忌症名称、严重程度、类型
    - 是否与患者状态匹配
    """
    if not contraindication_map:
        return []

    contraindications = contraindication_map.get(drug_name, [])
    if not contraindications:
        return []

    # 收集患者风险状态关键词
    patient_risk_keywords: Set[str] = set()
    for d in patient_data.get('diseases', []) or []:
        if d and d != '__unknown__':
            patient_risk_keywords.add(str(d).lower())
    for d in patient_data.get('chronic_diseases', []) or []:
        if d and d != '__unknown__':
            patient_risk_keywords.add(str(d).lower())

    pregnancy_status = patient_data.get('pregnancy_status',
                        patient_data.get('pregnancy', 'unknown'))
    if pregnancy_status in ('pregnant', 'confirmed', 'possible'):
        patient_risk_keywords.add('pregnancy')
        patient_risk_keywords.add('pregnant')

    breastfeeding_status = patient_data.get('breastfeeding_status',
                            patient_data.get('breastfeeding', 'unknown'))
    if breastfeeding_status == 'breastfeeding':
        patient_risk_keywords.add('lactation')
        patient_risk_keywords.add('breastfeeding')

    renal_function = patient_data.get('renal_function', 'normal')
    if renal_function in ('severe', 'failure', 'esrd'):
        patient_risk_keywords.add('renal')
        patient_risk_keywords.add('kidney')

    hepatic_function = patient_data.get('hepatic_function', 'normal')
    if hepatic_function in ('severe', 'failure'):
        patient_risk_keywords.add('hepatic')
        patient_risk_keywords.add('liver')

    details: List[Dict[str, Any]] = []
    for contra in contraindications:
        contra_name = str(contra.get('contraindication_name', '')).lower()
        # 判断是否与当前患者状态匹配
        matched = any(kw in contra_name for kw in patient_risk_keywords)

        details.append({
            'name': contra.get('contraindication_name', ''),
            'severity': contra.get('severity', 'unknown'),
            'type': contra.get('contraindication_type', 'unknown'),
            'patientRelevant': matched,
        })

    return details


def _build_safety_warnings(
    drug_name: str,
    safety_flags: Optional[Dict[str, Any]],
    patient_data: Dict[str, Any],
    drug: Dict[str, Any],
    contraindication_map: Optional[Dict[str, List[Dict[str, Any]]]],
    interaction_map: Optional[Dict[str, List[Dict[str, Any]]]],
) -> List[str]:
    """构建安全警告列表

    优先使用RuleMarker的safety_flags，补充特殊人群警告。
    """
    warnings: List[str] = []

    # 从safety_flags获取Layer 2警告
    if safety_flags:
        drug_flags = safety_flags.get(drug_name, {})
        for w in drug_flags.get('warnings', []):
            warnings.append(w)

    # 补充特殊人群警告(即使safety_flags中没有)
    pregnancy_status = patient_data.get('pregnancy_status',
                        patient_data.get('pregnancy', 'unknown'))
    if pregnancy_status in ('pregnant', 'confirmed', 'possible'):
        pregnancy_cat = drug.get('pregnancy_category', 'N')
        if pregnancy_cat == 'C' and '妊娠C级' not in ' '.join(warnings):
            warnings.append('妊娠C级: 动物实验有风险，人类数据不足')
        elif pregnancy_cat == 'D' and '妊娠D级' not in ' '.join(warnings):
            warnings.append('妊娠D级: 仅在获益大于风险时使用')

    # 育龄女性预防性提示
    gender = patient_data.get('gender', '').upper()
    age = patient_data.get('age', 0) or 0
    if gender in ('F', 'FEMALE') and 18 <= age <= 45:
        pregnancy_cat = drug.get('pregnancy_category', 'N')
        if pregnancy_cat in ('D', 'X') and '育龄女性' not in ' '.join(warnings):
            warnings.append(f'育龄女性注意: 妊娠{pregnancy_cat}级药物')

    return warnings


def _build_interaction_detail(
    drug_name: str,
    patient_data: Dict[str, Any],
    interaction_map: Optional[Dict[str, List[Dict[str, Any]]]],
) -> List[Dict[str, Any]]:
    """构建交互检查详情"""
    if not interaction_map:
        return []

    current_meds = [
        str(m).lower()
        for m in (patient_data.get('current_medications', []) or [])
        if m and m != '__unknown__'
    ]

    if not current_meds:
        return []

    details: List[Dict[str, Any]] = []
    interactions = interaction_map.get(drug_name, [])

    for interaction in interactions:
        other_drug = interaction.get('drug_a', interaction.get('drug_b', ''))
        if other_drug == drug_name:
            other_drug = interaction.get('drug_b', interaction.get('drug_a', ''))

        if other_drug.lower() in current_meds:
            details.append({
                'interactingDrug': other_drug,
                'severity': interaction.get('interaction_type', 'unknown'),
                'effect': interaction.get('clinical_effect', ''),
                'mechanism': interaction.get('mechanism', ''),
            })

    return details

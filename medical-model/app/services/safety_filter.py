"""三层推荐架构 — 安全硬排除 → 规则标记 → DeepFM排序

Layer 1: SafetyFilter — 确定性硬排除
  绝对禁忌、过敏冲突、严重药物交互、妊娠X级药物、儿科禁忌 → 100%排除
  DP噪声绝不影响此层排除结果

Layer 2: RuleMarker — 规则标记（非排除，仅附加警告）
  相对禁忌、中度交互、特殊人群提示 → safety_flags标注
  不改变候选药物集合，仅提供临床参考

Layer 3: DeepFM排序 — 个性化排序（仅对安全候选）
  对 Layer 1 未排除的安全候选药物进行 DeepFM 模型排序
  DP噪声仅作用于排序层，不影响安全排除层

v2: 使用clinical_matcher替代子串匹配, 新增儿科/哺乳期硬排除
"""

import logging
from typing import Dict, List, Set, Tuple, Any, Optional
from dataclasses import dataclass, field

from app.utils.clinical_matcher import match_condition, match_allergy

logger = logging.getLogger(__name__)


def _collect_patient_conditions(patient_data: Dict) -> Set[str]:
    """收集患者疾病集合（标准化后）"""
    conditions: Set[str] = set()
    for d in patient_data.get('diseases', []) or []:
        if d and d != '__unknown__':
            conditions.add(str(d).lower())
    for d in patient_data.get('chronic_diseases', []) or []:
        if d and d != '__unknown__':
            conditions.add(str(d).lower())
    return conditions


def _collect_patient_allergies(patient_data: Dict) -> Set[str]:
    """收集患者过敏集合（标准化后）"""
    allergies: Set[str] = set()
    for a in patient_data.get('allergies', []) or []:
        allergies.add(str(a).lower())
    for a in patient_data.get('allergy_list', []) or []:
        allergies.add(str(a).lower())
    return allergies


def _collect_current_medications(patient_data: Dict) -> List[str]:
    """收集患者当前用药列表"""
    meds = patient_data.get('current_medications', []) or []
    meds += patient_data.get('medication_list', []) or []
    return [str(m) for m in meds if m and m != '__unknown__']


@dataclass(frozen=True)
class ExclusionResult:
    """Layer 1 排除结果"""
    safe_candidates: List[Dict[str, Any]]
    excluded_drugs: List[Dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class SafetyFlagResult:
    """Layer 2 规则标记结果"""
    candidate_flags: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    # drug_name → {warnings: [...], contraindication_type: str, requires_review: bool}


@dataclass(frozen=True)
class RecommendationResult:
    """三层架构完整输出"""
    safe_candidates: List[Dict[str, Any]]
    excluded_drugs: List[Dict[str, Any]]
    safety_flags: Dict[str, Dict[str, Any]]
    ranked_results: List[Dict[str, Any]] = field(default_factory=list)


class SafetyFilter:
    """Layer 1: 确定性硬排除

    绝对禁忌、过敏冲突、严重药物交互、妊娠X级 → 100%排除
    不受概率模型或DP噪声影响
    """

    def filter(
        self,
        patient_data: Dict[str, Any],
        drug_candidates: List[Dict[str, Any]],
        contraindication_map: Dict[str, List[Dict[str, Any]]],
        interaction_map: Dict[str, List[Dict[str, Any]]],
        critical_interactions: Optional[Set[Tuple[str, str]]] = None,
    ) -> ExclusionResult:
        """执行安全硬过滤

        Args:
            patient_data: 患者数据（含 diseases, allergies, current_medications,
                          pregnancy_status, renal_function, hepatic_function）
            drug_candidates: 候选药物列表
            contraindication_map: drug_name → [contraindication_list]
            interaction_map: drug_name → [interaction_list]
            critical_interactions: 确认致命交互对集合 (drug_a, drug_b)
        Returns:
            ExclusionResult: safe_candidates + excluded_drugs（含排除原因）
        """
        safe_candidates: List[Dict[str, Any]] = []
        excluded_drugs: List[Dict[str, Any]] = []

        # 收集患者条件集合
        patient_conditions = _collect_patient_conditions(patient_data)
        patient_allergies = _collect_patient_allergies(patient_data)
        current_meds = _collect_current_medications(patient_data)

        # 当前用药的药物分类名集合(用于drug_class类禁忌匹配)
        patient_current_med_classes: Set[str] = set()
        for med in current_meds:
            med_lower = str(med).lower()
            patient_current_med_classes.add(med_lower)

        # 患者年龄(v2: 用于儿科禁忌硬排除)
        patient_age = patient_data.get('age', 0) or 0

        # 特殊人群信息
        pregnancy_status = patient_data.get('pregnancy_status',
                           patient_data.get('pregnancy', 'unknown'))
        breastfeeding_status = patient_data.get('breastfeeding_status', 'unknown')  # v2新增
        renal_function = patient_data.get('renal_function', 'unknown')
        hepatic_function = patient_data.get('hepatic_function', 'unknown')

        for drug in drug_candidates:
            drug_name = drug.get('generic_name', drug.get('name', ''))
            exclusion_reason: Optional[str] = None

            # 1. 绝对禁忌检查 (v2: 使用clinical_matcher标准化匹配)
            contraindications = contraindication_map.get(drug_name, [])
            for contra in contraindications:
                if contra.get('severity') == 'absolute':
                    contra_name = str(contra.get('contraindication_name', ''))
                    contra_type = contra.get('contraindication_type', 'disease')
                    # drug_class类禁忌与患者用药匹配而非疾病
                    if contra_type == 'drug_class':
                        if match_condition(patient_current_med_classes, contra_name):
                            exclusion_reason = f"绝对禁忌(药物类): {contra_name}"
                            break
                    else:
                        if match_condition(patient_conditions, contra_name):
                            exclusion_reason = f"绝对禁忌: {contra_name}"
                            break

            # 1b. 儿科禁忌硬排除 (v2新增)
            if not exclusion_reason and patient_age < 18:
                for contra in contraindications:
                    if contra.get('severity') == 'absolute':
                        contra_name = str(contra.get('contraindication_name', '')).lower()
                        if any(kw in contra_name for kw in
                               ['children', 'pediatric', 'adolescent', 'infant', 'neonatal', 'juvenile']):
                            exclusion_reason = f"儿科禁忌: {contra.get('contraindication_name', '')}"
                            break

            # 2. 过敏冲突检查 (v2: 使用clinical_matcher精确匹配, 过敏可致命)
            if not exclusion_reason:
                for contra in contraindications:
                    if contra.get('contraindication_type') == 'allergy_type':
                        contra_name = str(contra.get('contraindication_name', ''))
                        if match_allergy(patient_allergies, contra_name):
                            exclusion_reason = (
                                f"过敏冲突: {contra.get('contraindication_name', '')}"
                            )
                            break

            # 3. 严重药物交互检查
            if not exclusion_reason:
                interactions = interaction_map.get(drug_name, [])
                for interaction in interactions:
                    if interaction.get('interaction_type') == 'major':
                        other_drug = interaction.get('drug_a', interaction.get('drug_b', ''))
                        if other_drug == drug_name:
                            other_drug = interaction.get('drug_b',
                                         interaction.get('drug_a', ''))
                        if any(str(m).lower() == other_drug.lower()
                               for m in current_meds):
                            exclusion_reason = f"严重交互: {drug_name} + {other_drug}"
                            break

            # 4. 硬编码致命交互检查
            if not exclusion_reason and critical_interactions:
                for med in current_meds:
                    pair_a = (drug_name.lower(), str(med).lower())
                    pair_b = (str(med).lower(), drug_name.lower())
                    if pair_a in critical_interactions or pair_b in critical_interactions:
                        exclusion_reason = f"致命交互: {drug_name} + {med}"
                        break

            # 5. 妊娠X级硬排除 (v2: 扩展到possible状态)
            if not exclusion_reason and pregnancy_status in ('pregnant', 'confirmed', 'possible'):
                pregnancy_cat = drug.get('pregnancy_category', 'N')
                if pregnancy_cat == 'X':
                    exclusion_reason = f"妊娠X级禁用"

            # 5b. 哺乳期硬排除 — 优先检查结构化lactation_category字段
            if not exclusion_reason and breastfeeding_status == 'breastfeeding':
                lactation_cat = str(drug.get('lactation_category', '')).upper()
                if lactation_cat in ('L5', '5', 'CONTRAINDICATED'):
                    exclusion_reason = "哺乳期L5级禁用"
                else:
                    # 降级: 从禁忌症数据中查找lactation相关absolute禁忌
                    for contra in contraindications:
                        contra_name = str(contra.get('contraindication_name', '')).lower()
                        if contra.get('severity') == 'absolute' and any(
                            kw in contra_name for kw in
                            ('lactation', 'breastfeeding', 'breast-feeding',
                             'nursing', 'milk', 'lactating')
                        ):
                            exclusion_reason = f"哺乳期禁忌: {contra.get('contraindication_name', '')}"
                            break

            # 6. 严重肝/肾功能不全硬排除（特定药物）
            if not exclusion_reason:
                renal_severe = renal_function in ('severe', 'failure', 'esrd')
                hepatic_severe = hepatic_function in ('severe', 'failure')
                contra_types = {c.get('contraindication_type', '') for c in contraindications}
                if renal_severe and 'physiological_condition' in contra_types:
                    for contra in contraindications:
                        name_lower = str(contra.get('contraindication_name', '')).lower()
                        if contra.get('severity') == 'absolute' and (
                            'renal' in name_lower or 'kidney' in name_lower
                        ):
                            exclusion_reason = f"肾功能不全禁忌"
                            break
                if hepatic_severe and 'physiological_condition' in contra_types:
                    for contra in contraindications:
                        name_lower = str(contra.get('contraindication_name', '')).lower()
                        if contra.get('severity') == 'absolute' and (
                            'hepatic' in name_lower or 'liver' in name_lower
                        ):
                            exclusion_reason = f"肝功能不全禁忌"
                            break

            # 分类
            if exclusion_reason:
                excluded_drugs.append({
                    'drug_name': drug_name,
                    'reason': exclusion_reason,
                    'drug_data': drug,
                })
            else:
                safe_candidates.append(drug)

        logger.info(
            f"SafetyFilter: {len(safe_candidates)} safe candidates, "
            f"{len(excluded_drugs)} excluded from {len(drug_candidates)} total"
        )
        return ExclusionResult(
            safe_candidates=safe_candidates,
            excluded_drugs=excluded_drugs,
        )



class RuleMarker:
    """Layer 2: 规则标记（非排除，仅附加警告信息）

    相对禁忌、中度交互、特殊人群提示 → safety_flags 标注
    不改变候选药物集合，仅提供临床决策参考
    """

    def mark(
        self,
        patient_data: Dict[str, Any],
        safe_candidates: List[Dict[str, Any]],
        contraindication_map: Dict[str, List[Dict[str, Any]]],
        interaction_map: Dict[str, List[Dict[str, Any]]],
    ) -> SafetyFlagResult:
        """对安全候选药物附加规则标记

        Args:
            patient_data: 患者数据
            safe_candidates: Layer 1 过滤后的安全候选
            contraindication_map: 禁忌症映射
            interaction_map: 交互映射
        Returns:
            SafetyFlagResult: candidate_flags (drug_name → flags)
        """
        patient_conditions = _collect_patient_conditions(patient_data)
        current_meds = patient_data.get('current_medications', []) or []
        pregnancy_status = patient_data.get('pregnancy_status',
                           patient_data.get('pregnancy', 'unknown'))
        renal_function = patient_data.get('renal_function', 'unknown')
        hepatic_function = patient_data.get('hepatic_function', 'unknown')

        candidate_flags: Dict[str, Dict[str, Any]] = {}

        for drug in safe_candidates:
            drug_name = drug.get('generic_name', drug.get('name', ''))
            warnings: List[str] = []
            requires_review = False
            contraindication_type = 'safe'

            # 相对禁忌检查 (v2: 使用clinical_matcher标准化匹配)
            contraindications = contraindication_map.get(drug_name, [])
            for contra in contraindications:
                if contra.get('severity') == 'relative':
                    contra_name = str(contra.get('contraindication_name', ''))
                    contra_type = contra.get('contraindication_type', 'disease')
                    if contra_type == 'allergy_type':
                        # 相对禁忌中的过敏仍需严格匹配
                        patient_allergies = _collect_patient_allergies(patient_data)
                        if match_allergy(patient_allergies, contra_name):
                            warnings.append(f"过敏提示: {contra_name}")
                            requires_review = True
                            contraindication_type = 'relative_contraindication'
                    elif contra_type == 'drug_class':
                        if match_condition(
                            {str(m).lower() for m in current_meds if m and m != '__unknown__'},
                            contra_name,
                        ):
                            warnings.append(f"相对禁忌(药物类): {contra_name}")
                            requires_review = True
                    else:
                        if match_condition(patient_conditions, contra_name):
                            warnings.append(f"相对禁忌: {contra_name}")
                            requires_review = True
                            contraindication_type = 'relative_contraindication'

            # 中度交互检查
            interactions = interaction_map.get(drug_name, [])
            for interaction in interactions:
                if interaction.get('interaction_type') == 'moderate':
                    other_drug = interaction.get('drug_a', interaction.get('drug_b', ''))
                    if other_drug == drug_name:
                        other_drug = interaction.get('drug_b',
                                     interaction.get('drug_a', ''))
                    if any(str(m).lower() == other_drug.lower()
                           for m in current_meds if m and m != '__unknown__'):
                        warnings.append(
                            f"中度交互: {drug_name} + {other_drug} — "
                            f"{interaction.get('clinical_effect', '需监测')}"
                        )
                        requires_review = True
                        if contraindication_type == 'safe':
                            contraindication_type = 'moderate_interaction'

            # 妊娠C/D级提示
            pregnancy_cat = drug.get('pregnancy_category', 'N')
            if pregnancy_status in ('pregnant', 'confirmed', 'possible'):
                if pregnancy_cat == 'D':
                    warnings.append(f"妊娠D级: 仅在获益大于风险时使用")
                    requires_review = True
                elif pregnancy_cat == 'C':
                    warnings.append(f"妊娠C级: 动物实验有风险，人类数据不足")
                    requires_review = True

            # 肾功能不全药物特异性提示
            if renal_function in ('mild', 'moderate', 'severe'):
                renal_warning = _check_renal_warning(drug_name, renal_function, contraindications)
                if renal_warning:
                    warnings.append(renal_warning)
                    if renal_function == 'severe':
                        requires_review = True

            # 肝功能不全药物特异性提示
            if hepatic_function in ('mild', 'moderate', 'severe'):
                hepatic_warning = _check_hepatic_warning(drug_name, hepatic_function, contraindications)
                if hepatic_warning:
                    warnings.append(hepatic_warning)
                    if hepatic_function == 'severe':
                        requires_review = True

            # 育龄女性预防性提示 (gender=F, age 18-45)
            patient_gender = str(patient_data.get('gender', '')).upper()
            patient_age = patient_data.get('age', 0) or 0
            if patient_gender in ('F', 'FEMALE') and 18 <= patient_age <= 45:
                pregnancy_cat = drug.get('pregnancy_category', 'N')
                if pregnancy_cat in ('D', 'X'):
                    warnings.append(f"育龄女性注意: 妊娠{pregnancy_cat}级药物")
                    requires_review = True

            candidate_flags[drug_name] = {
                'warnings': warnings,
                'contraindication_type': contraindication_type,
                'requires_review': requires_review,
            }

        flagged_count = sum(1 for f in candidate_flags.values() if f['requires_review'])
        logger.info(
            f"RuleMarker: {len(candidate_flags)} candidates marked, "
            f"{flagged_count} require clinical review"
        )
        return SafetyFlagResult(candidate_flags=candidate_flags)


def _check_renal_warning(
    drug_name: str,
    renal_function: str,
    contraindications: List[Dict[str, Any]],
) -> Optional[str]:
    """检查药物特异性的肾功能不全警告

    仅对该药物有肾相关禁忌/注意事项的才触发警告，
    而非对所有药物统一触发。
    """
    # 从禁忌症中查找肾相关条目
    has_renal_contra = False
    contra_detail = ''
    for contra in contraindications:
        name_lower = str(contra.get('contraindication_name', '')).lower()
        is_renal = 'renal' in name_lower or 'kidney' in name_lower
        if not is_renal:
            continue
        severity = contra.get('severity', '')
        if severity == 'absolute':
            # 严重肾功能不全时，absolute禁忌已在Layer 1排除
            # 此处仅对mild/moderate触发警告
            if renal_function in ('mild', 'moderate'):
                has_renal_contra = True
                contra_detail = contra.get('contraindication_name', '')
                break
        elif severity == 'relative':
            has_renal_contra = True
            contra_detail = contra.get('contraindication_name', '')
            break

    if has_renal_contra:
        if renal_function == 'severe':
            return f"严重肾功能不全: {drug_name}需避免使用({contra_detail})"
        elif renal_function == 'moderate':
            return f"中度肾功能不全: {drug_name}需调整剂量({contra_detail})"
        else:
            return f"轻度肾功能不全: {drug_name}需监测肾功能({contra_detail})"

    # 无肾相关禁忌时，对severe仍给通用提醒
    if renal_function == 'severe':
        return f"严重肾功能不全: {drug_name}需谨慎使用，建议监测肾功能"

    return None


def _check_hepatic_warning(
    drug_name: str,
    hepatic_function: str,
    contraindications: List[Dict[str, Any]],
) -> Optional[str]:
    """检查药物特异性的肝功能不全警告

    仅对该药物有肝相关禁忌/注意事项的才触发警告，
    而非对所有药物统一触发。
    """
    has_hepatic_contra = False
    contra_detail = ''
    for contra in contraindications:
        name_lower = str(contra.get('contraindication_name', '')).lower()
        is_hepatic = 'hepatic' in name_lower or 'liver' in name_lower
        if not is_hepatic:
            continue
        severity = contra.get('severity', '')
        if severity == 'absolute':
            if hepatic_function in ('mild', 'moderate'):
                has_hepatic_contra = True
                contra_detail = contra.get('contraindication_name', '')
                break
        elif severity == 'relative':
            has_hepatic_contra = True
            contra_detail = contra.get('contraindication_name', '')
            break

    if has_hepatic_contra:
        if hepatic_function == 'severe':
            return f"严重肝功能不全: {drug_name}需避免使用({contra_detail})"
        elif hepatic_function == 'moderate':
            return f"中度肝功能不全: {drug_name}需调整剂量({contra_detail})"
        else:
            return f"轻度肝功能不全: {drug_name}需监测肝功能({contra_detail})"

    # 无肝相关禁忌时，对severe仍给通用提醒
    if hepatic_function == 'severe':
        return f"严重肝功能不全: {drug_name}需谨慎使用，建议监测肝功能"

    return None


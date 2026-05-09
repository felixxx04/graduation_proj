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
from enum import Enum
from typing import Dict, List, Set, Tuple, Any, Optional
from dataclasses import dataclass, field

from app.utils.clinical_matcher import match_condition, match_allergy


class SafetyLevel(Enum):
    SAFE = "safe"
    WARNING = "warning"
    OFF_LABEL = "off_label"
    UNVERIFIED = "unverified"
    EXCLUDED = "excluded"

logger = logging.getLogger(__name__)


def _collect_patient_conditions(patient_data: Dict) -> Set[str]:
    """收集患者疾病集合（标准化后）

    优先使用 indication_match_conditions（包含所有映射结果，不受vocab过滤），
    确保PAH等关键疾病不被遗漏。
    """
    conditions: Set[str] = set()
    # 优先使用 indication_match_conditions（完整映射结果）
    for d in patient_data.get('indication_match_conditions', []) or []:
        if d and d != '__unknown__':
            conditions.add(str(d).lower())
    if not conditions:
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


def _is_hard_exclude(reason: str) -> bool:
    """Determine if an exclusion reason warrants hard exclusion (can't override)."""
    hard_keywords = [
        "过敏冲突",
        "妊娠X级",
        "致命交互",
        "MAOI+SSRI",
        "绝对禁忌",
        "儿科禁忌",
        "哺乳期L5",
        "草药补充剂",
        "加重真菌感染",
        "加重感染",
        "感染性肠炎不适当",
        "对病毒性",
    ]
    return any(kw in reason for kw in hard_keywords)


def _extract_safety_tag(reason: str) -> str:
    """Extract a short safety tag from a longer exclusion reason."""
    if "off_label" in reason.lower() or "无适应症" in reason:
        return "off_label"
    if "数据未验证" in reason:
        return "unverified"
    if "相对禁忌" in reason:
        return "relative_contraindication"
    return "marked_for_review"


@dataclass(frozen=True)
class ExclusionResult:
    """Layer 1 排除结果"""
    safe_candidates: List[Dict[str, Any]]
    excluded_drugs: List[Dict[str, Any]] = field(default_factory=list)
    marked_candidates: List[Dict[str, Any]] = field(default_factory=list)


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
        marked_drugs: List[Dict[str, Any]] = []

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

            # 6. MAOI+SSRI致命交互硬排除
            # MAOI与SSRI联用可致5-羟色胺综合征(致命), 属于绝对禁忌
            # 方向: 患者正在用MAOI → 排除所有SSRI候选; 患者正在用SSRI → 排除所有MAOI候选
            if not exclusion_reason:
                maoi_drugs = {
                    'phenelzine', 'tranylcypromine', 'isocarboxazid',
                    'selegiline', 'rasagiline', 'moclobemide',
                }
                ssri_drugs = {
                    'fluoxetine', 'sertraline', 'paroxetine',
                    'citalopram', 'escitalopram', 'fluvoxamine',
                    'vilazodone', 'dapoxetine',
                }
                drug_lower = drug_name.lower()
                current_meds_lower = {str(m).lower() for m in current_meds if m and m != '__unknown__'}
                # 患者正在用MAOI → 排除SSRI候选
                if drug_lower in ssri_drugs:
                    for med in current_meds_lower:
                        if med in maoi_drugs or any(maoi in med for maoi in maoi_drugs):
                            exclusion_reason = f"致命交互: MAOI+SSRI(5-羟色胺综合征风险)"
                            break
                # 患者正在用SSRI → 排除MAOI候选
                if drug_lower in maoi_drugs and not exclusion_reason:
                    for med in current_meds_lower:
                        if med in ssri_drugs or any(ssri in med for ssri in ssri_drugs):
                            exclusion_reason = f"致命交互: SSRI+MAOI(5-羟色胺综合征风险)"
                            break

            # 7. PAH药物误用于普通高血压硬排除
            # Bosentan等肺动脉高压(PAH)专用药不应推荐给普通高血压患者
            # 仅当患者有PAH时才允许使用
            if not exclusion_reason:
                pah_specific_drugs = {
                    'bosentan', 'ambrisentan', 'macitentan',
                    'riociguat', 'selexipag', 'epoprostenol',
                    'treprostinil', 'iloprost',
                }
                if drug_lower in pah_specific_drugs:
                    patient_has_pah = any(
                        kw in ' '.join(patient_conditions)
                        for kw in ('pulmonary arterial hypertension', 'pah', 'pulmonary hypertension')
                    )
                    if not patient_has_pah:
                        exclusion_reason = f"PAH专用药不可用于普通高血压: {drug_name}"

            # 8. 严重肝/肾功能不全硬排除（特定药物）
            if not exclusion_reason:
                renal_severe = renal_function in ('severe', 'severe_impairment', 'failure', 'esrd')
                hepatic_severe = hepatic_function in ('severe', 'severe_impairment', 'failure')
                renal_impaired = renal_function in ('mild', 'mild_impairment', 'moderate', 'moderate_impairment', 'severe', 'severe_impairment', 'failure', 'esrd')
                hepatic_impaired = hepatic_function in ('mild', 'mild_impairment', 'moderate', 'moderate_impairment', 'severe', 'severe_impairment', 'failure')
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

            # 9. 草药/补充剂排除 — 感染性疾病不应推荐无抗菌证据的草药
            # Echinacea等草药被标注为"Herbal Supplement"/"Dietary Supplement"
            # 其适应症仅为"immune support"/"common cold prophylaxis"等辅助用途
            # 对bacterial/viral/fungal等感染性疾病无治疗证据，推荐属于医学错误
            if not exclusion_reason:
                drug_class_lower = str(drug.get('drug_class_en', '')).lower()
                supplement_keywords = ('herbal supplement', 'dietary supplement', 'supplement')
                if any(kw in drug_class_lower for kw in supplement_keywords):
                    # 检查患者是否有感染性疾病
                    infection_keywords = (
                        'infection', 'bacterial', 'viral', 'fungal', 'parasitic',
                        'sepsis', 'abscess', 'cellulitis', 'pneumonia',
                    )
                    patient_condition_text = ' '.join(patient_conditions)
                    if any(kw in patient_condition_text for kw in infection_keywords):
                        exclusion_reason = f"草药补充剂无抗菌证据，不可用于感染性疾病: {drug_name}"

            # 10. 抗生素误用于病毒性疾病硬排除
            # 支气管炎、感冒、上呼吸道感染等多为病毒性
            # 抗生素对病毒无效，不应作为主要推荐
            # 仅排除口服/注射系统性抗生素，保留局部外用抗生素
            if not exclusion_reason:
                drug_class_lower = str(drug.get('drug_class_en', '')).lower()
                antibiotic_keywords = (
                    'antibiotic', 'antibacterial', 'quinolone', 'fluoroquinolone',
                    'macrolide', 'cephalosporin', 'penicillin', 'tetracycline',
                    'lincosamide', 'nitroimidazole', 'sulfonamide antibiotic',
                    'glycopeptide', 'oxazolidinone', 'carbapenem', 'monobactam',
                )
                systemic_form_keywords = ('tablet', 'capsule', 'oral', 'injection', 'intravenous')
                dosage_form = str(drug.get('dosage_form', '')).lower()
                drug_name_lower = drug_name.lower()
                # Some drugs have empty dosage_form but the route is in the name
                # e.g. "erythromycin (oral/injection)" has dosage_form=""
                is_systemic = (
                    any(kw in dosage_form for kw in systemic_form_keywords)
                    or any(kw in drug_name_lower for kw in systemic_form_keywords)
                )
                is_systemic_antibiotic = (
                    any(kw in drug_class_lower for kw in antibiotic_keywords)
                    and is_systemic
                )
                if is_systemic_antibiotic:
                    viral_disease_keywords = (
                        'common cold', 'cold', 'upper respiratory infection',
                        'uri', 'urti', 'bronchitis', 'flu', 'influenza',
                        'viral infection', 'cough',
                    )
                    # Check primary_input_diseases first (original user input)
                    primary_input = set(
                        str(d).lower() for d in patient_data.get('primary_input_diseases', []) or []
                        if d and d != '__unknown__'
                    )
                    original_mapped = set(
                        str(d).lower() for d in patient_data.get('original_mapped_diseases', []) or []
                        if d and d != '__unknown__'
                    )
                    check_diseases = primary_input or original_mapped
                    for disease in check_diseases:
                        if any(kw in disease for kw in viral_disease_keywords):
                            exclusion_reason = f"抗生素对病毒性疾病无效，不应推荐: {drug_name}"
                            break

            # 11. PPI误用于胆囊疾病硬排除
            # 胆囊炎/胆结石需要抗感染或手术，PPI(质子泵抑制剂)对胆囊疾病无效
            if not exclusion_reason:
                drug_class_lower = str(drug.get('drug_class_en', '')).lower()
                is_ppi = 'proton pump inhibitor' in drug_class_lower or 'ppi' in drug_class_lower
                if is_ppi:
                    primary_input = set(
                        str(d).lower() for d in patient_data.get('primary_input_diseases', []) or []
                        if d and d != '__unknown__'
                    )
                    original_mapped = set(
                        str(d).lower() for d in patient_data.get('original_mapped_diseases', []) or []
                        if d and d != '__unknown__'
                    )
                    check_diseases = primary_input or original_mapped
                    gallbladder_keywords = ('cholecystitis', 'gallstone', 'cholelithiasis', 'biliary', 'gallbladder')
                    for disease in check_diseases:
                        if any(kw in disease for kw in gallbladder_keywords):
                            exclusion_reason = f"PPI对胆囊疾病无效，不应推荐: {drug_name}"
                            break

            # 12. 抗生素误用于尿路结石硬排除
            # 尿路结石需要排石/碎石治疗，抗生素仅在合并感染时使用
            # 不应作为结石的主要推荐药物
            if not exclusion_reason:
                drug_class_lower = str(drug.get('drug_class_en', '')).lower()
                antibiotic_keywords = (
                    'antibiotic', 'antibacterial', 'quinolone', 'fluoroquinolone',
                    'cephalosporin', 'penicillin', 'sulfonamide antibiotic',
                )
                is_antibiotic = any(kw in drug_class_lower for kw in antibiotic_keywords)
                dosage_form = str(drug.get('dosage_form', '')).lower()
                drug_name_lower = drug_name.lower()
                is_systemic = (
                    any(kw in dosage_form for kw in ('tablet', 'capsule', 'oral', 'injection'))
                    or any(kw in drug_name_lower for kw in ('tablet', 'capsule', 'oral', 'injection'))
                )
                if is_antibiotic and is_systemic:
                    primary_input = set(
                        str(d).lower() for d in patient_data.get('primary_input_diseases', []) or []
                        if d and d != '__unknown__'
                    )
                    original_mapped = set(
                        str(d).lower() for d in patient_data.get('original_mapped_diseases', []) or []
                        if d and d != '__unknown__'
                    )
                    check_diseases = primary_input or original_mapped
                    stone_keywords = ('kidney stone', 'urinary calculi', 'nephrolithiasis', 'cholelithiasis', 'gallstone', 'urolithiasis')
                    # Skip if patient also has UTI (antibiotics are appropriate for UTI)
                    has_uti = any('urinary tract infection' in d or 'uti' in d for d in check_diseases)
                    if not has_uti:
                        for disease in check_diseases:
                            if any(kw in disease for kw in stone_keywords):
                                exclusion_reason = f"抗生素对尿路结石无直接治疗作用(除非合并感染): {drug_name}"
                                break

            # 13. IBD药物误用于感染性肠炎硬排除
            # 感染性肠炎需要抗感染或支持治疗，不应推荐生物制剂/免疫抑制剂等IBD药物
            # 仅当患者明确诊断为IBD(溃疡性结肠炎/Crohn病)时才允许使用
            if not exclusion_reason:
                ibd_drug_keywords = (
                    'biologic', 'anti-tnf', 'tnf inhibitor', 'immunosuppressant',
                    'anti-integrin', 'jak inhibitor', 'il inhibitor',
                )
                drug_class_lower = str(drug.get('drug_class_en', '')).lower()
                drug_gn_lower = drug_name.lower()
                ibd_specific_drugs = {
                    'infliximab', 'adalimumab', 'golimumab', 'vedolizumab',
                    'ustekinumab', 'tofacitinib', 'upadacitinib',
                    'mesalamine', 'sulfasalazine', 'balsalazide',
                    'olsalazine', 'budesonide', 'mercaptopurine',
                    'azathioprine', 'methotrexate',
                }
                is_ibd_drug = (
                    drug_gn_lower in ibd_specific_drugs
                    or any(kw in drug_class_lower for kw in ibd_drug_keywords)
                )
                if is_ibd_drug:
                    primary_input = set(
                        str(d).lower() for d in patient_data.get('primary_input_diseases', []) or []
                        if d and d != '__unknown__'
                    )
                    original_mapped = set(
                        str(d).lower() for d in patient_data.get('original_mapped_diseases', []) or []
                        if d and d != '__unknown__'
                    )
                    check_diseases = primary_input or original_mapped
                    ibd_keywords = ('ulcerative colitis', 'crohn', 'inflammatory bowel disease', 'ibd')
                    enteritis_keywords = ('enteritis', 'gastroenteritis', 'food poisoning')
                    # 如果是IBD则允许，如果是普通肠炎则排除
                    has_ibd = any(any(kw in d for kw in ibd_keywords) for d in check_diseases)
                    if not has_ibd:
                        for disease in check_diseases:
                            if any(kw in disease for kw in enteritis_keywords):
                                exclusion_reason = f"IBD药物对感染性肠炎不适当: {drug_name}"
                                break

            # 14. 糖尿病药物误用于尿路结石硬排除
            # 尿路结石需要排石/碎石/止痛治疗，降糖药(DPP-4/SGLT2/GLP-1/胰岛素)与结石无关
            if not exclusion_reason:
                drug_class_lower = str(drug.get('drug_class_en', '')).lower()
                drug_gn_lower = drug_name.lower()
                diabetes_drug_keywords = (
                    'dpp-4 inhibitor', 'dpp-4', 'sglt2 inhibitor', 'sglt2',
                    'glp-1', 'incretin mimetic', 'insulin', 'antidiabetic',
                    'biguanide', 'metformin', 'sulfonylurea', 'thiazolidinedione',
                )
                diabetes_specific_drugs = {
                    'linagliptin', 'empagliflozin', 'canagliflozin', 'dapagliflozin',
                    'semaglutide', 'liraglutide', 'exenatide', 'tirzepatide',
                    'sitagliptin', 'saxagliptin', 'alogliptin', 'vildagliptin',
                    'metformin', 'glipizide', 'glyburide', 'pioglitazone',
                    'rosiglitazone', 'colesevelam', 'acarbose', 'pramlintide',
                }
                is_diabetes_drug = (
                    drug_gn_lower in diabetes_specific_drugs
                    or any(kw in drug_class_lower for kw in diabetes_drug_keywords)
                )
                if is_diabetes_drug:
                    primary_input = set(
                        str(d).lower() for d in patient_data.get('primary_input_diseases', []) or []
                        if d and d != '__unknown__'
                    )
                    original_mapped = set(
                        str(d).lower() for d in patient_data.get('original_mapped_diseases', []) or []
                        if d and d != '__unknown__'
                    )
                    check_diseases = primary_input or original_mapped
                    stone_keywords = ('kidney stone', 'urinary calculi', 'nephrolithiasis', 'urolithiasis')
                    diabetes_keywords = ('diabetes', 'type 2 diabetes', 'type 1 diabetes', 'diabetic')
                    has_diabetes = any(any(kw in d for kw in diabetes_keywords) for d in check_diseases)
                    if not has_diabetes:
                        for disease in check_diseases:
                            if any(kw in disease for kw in stone_keywords):
                                exclusion_reason = f"降糖药对尿路结石无治疗作用: {drug_name}"
                                break

            # 15. 苯二氮卓类误用于胆囊疾病硬排除
            # 胆囊炎/胆结石需要镇痛和抗感染，镇静剂(苯二氮卓)有肝损伤风险，不适当
            if not exclusion_reason:
                drug_class_lower = str(drug.get('drug_class_en', '')).lower()
                is_benzodiazepine = 'benzodiazepine' in drug_class_lower
                if is_benzodiazepine:
                    primary_input = set(
                        str(d).lower() for d in patient_data.get('primary_input_diseases', []) or []
                        if d and d != '__unknown__'
                    )
                    original_mapped = set(
                        str(d).lower() for d in patient_data.get('original_mapped_diseases', []) or []
                        if d and d != '__unknown__'
                    )
                    check_diseases = primary_input or original_mapped
                    gallbladder_keywords = ('cholecystitis', 'gallstone', 'cholelithiasis', 'biliary', 'gallbladder')
                    anxiety_keywords = ('anxiety', 'panic', 'insomnia', 'seizure', 'epilepsy')
                    has_anxiety_need = any(any(kw in d for kw in anxiety_keywords) for d in check_diseases)
                    if not has_anxiety_need:
                        for disease in check_diseases:
                            if any(kw in disease for kw in gallbladder_keywords):
                                exclusion_reason = f"镇静剂对胆囊疾病不适当且有肝损伤风险: {drug_name}"
                                break

            # 16. 糖皮质激素误用于感染性肠炎硬排除
            # 感染性肠炎需要抗感染/支持治疗，激素会抑制免疫加重感染
            if not exclusion_reason:
                drug_class_lower = str(drug.get('drug_class_en', '')).lower()
                drug_gn_lower = drug_name.lower()
                corticosteroid_keywords = ('corticosteroid', 'glucocorticoid', 'steroid', 'cortisone')
                corticosteroid_drugs = {
                    'prednisone', 'prednisolone', 'dexamethasone', 'methylprednisolone',
                    'hydrocortisone', 'betamethasone', 'triamcinolone', 'budesonide',
                    'fludrocortisone', 'cortisone',
                }
                is_corticosteroid = (
                    drug_gn_lower in corticosteroid_drugs
                    or any(kw in drug_class_lower for kw in corticosteroid_keywords)
                )
                if is_corticosteroid:
                    primary_input = set(
                        str(d).lower() for d in patient_data.get('primary_input_diseases', []) or []
                        if d and d != '__unknown__'
                    )
                    original_mapped = set(
                        str(d).lower() for d in patient_data.get('original_mapped_diseases', []) or []
                        if d and d != '__unknown__'
                    )
                    check_diseases = primary_input or original_mapped
                    ibd_keywords = ('ulcerative colitis', 'crohn', 'inflammatory bowel disease', 'ibd')
                    enteritis_keywords = ('enteritis', 'gastroenteritis', 'food poisoning')
                    has_ibd = any(any(kw in d for kw in ibd_keywords) for d in check_diseases)
                    if not has_ibd:
                        for disease in check_diseases:
                            if any(kw in disease for kw in enteritis_keywords):
                                exclusion_reason = f"糖皮质激素对感染性肠炎不适当，会加重感染: {drug_name}"
                                break

            # 17. 促尿酸排泄药(Probenecid等)误用于感染性肠炎排除
            # Probenecid是促尿酸排泄药，仅作为抗生素辅助增强疗效，不应作为肠炎主要推荐
            if not exclusion_reason:
                drug_class_lower = str(drug.get('drug_class_en', '')).lower()
                drug_gn_lower = drug_name.lower()
                uricosuric_keywords = ('uricosuric', 'probenecid', 'sulfinpyrazone')
                is_uricosuric = (
                    drug_gn_lower in uricosuric_keywords
                    or any(kw in drug_class_lower for kw in uricosuric_keywords)
                )
                if is_uricosuric:
                    primary_input = set(
                        str(d).lower() for d in patient_data.get('primary_input_diseases', []) or []
                        if d and d != '__unknown__'
                    )
                    original_mapped = set(
                        str(d).lower() for d in patient_data.get('original_mapped_diseases', []) or []
                        if d and d != '__unknown__'
                    )
                    check_diseases = primary_input or original_mapped
                    gout_keywords = ('gout', 'hyperuricemia', 'uric acid')
                    enteritis_keywords = ('enteritis', 'gastroenteritis', 'food poisoning', 'diarrhea')
                    has_gout = any(any(kw in d for kw in gout_keywords) for d in check_diseases)
                    if not has_gout:
                        for disease in check_diseases:
                            if any(kw in disease for kw in enteritis_keywords):
                                exclusion_reason = f"促尿酸排泄药不适用于肠炎: {drug_name}"
                                break

            # 18. 糖皮质激素误用于真菌感染硬排除
            # 糖皮质激素会抑制免疫系统，加重真菌感染，属于严重临床错误
            if not exclusion_reason:
                drug_class_lower = str(drug.get('drug_class_en', '')).lower()
                drug_gn_lower = drug_name.lower()
                corticosteroid_keywords = ('corticosteroid', 'glucocorticoid', 'steroid', 'cortisone')
                corticosteroid_drugs = {
                    'prednisone', 'prednisolone', 'dexamethasone', 'methylprednisolone',
                    'hydrocortisone', 'betamethasone', 'triamcinolone', 'budesonide',
                    'fludrocortisone', 'cortisone',
                }
                is_corticosteroid = (
                    drug_gn_lower in corticosteroid_drugs
                    or any(kw in drug_class_lower for kw in corticosteroid_keywords)
                )
                if is_corticosteroid:
                    primary_input = set(
                        str(d).lower() for d in patient_data.get('primary_input_diseases', []) or []
                        if d and d != '__unknown__'
                    )
                    original_mapped = set(
                        str(d).lower() for d in patient_data.get('original_mapped_diseases', []) or []
                        if d and d != '__unknown__'
                    )
                    check_diseases = primary_input or original_mapped
                    fungal_keywords = ('fungal infection', 'candidiasis', 'candida', 'fungal', 'mycosis', 'ringworm', 'tinea')
                    for disease in check_diseases:
                        if any(kw in disease for kw in fungal_keywords):
                            exclusion_reason = f"糖皮质激素会加重真菌感染，绝对禁忌: {drug_name}"
                            break

            # 19. 青光眼药物误用于白内障硬排除
            # 白内障需要手术治疗，降眼压药(青光眼药)对白内障无治疗作用
            if not exclusion_reason:
                drug_class_lower = str(drug.get('drug_class_en', '')).lower()
                drug_gn_lower = drug_name.lower()
                glaucoma_drug_keywords = (
                    'carbonic anhydrase inhibitor', 'beta-blocker eye', 'prostaglandin analogue',
                    'alpha agonist eye', 'cholinergic eye', 'miotic',
                )
                glaucoma_specific_drugs = {
                    'acetazolamide', 'dorzolamide', 'brinzolamide',
                    'timolol', 'betaxolol', 'levobunolol',
                    'latanoprost', 'travoprost', 'bimatoprost',
                    'brimonidine', 'apraclonidine',
                    'pilocarpine', 'echothiophate',
                }
                is_glaucoma_drug = (
                    drug_gn_lower in glaucoma_specific_drugs
                    or any(kw in drug_class_lower for kw in glaucoma_drug_keywords)
                )
                if is_glaucoma_drug:
                    primary_input = set(
                        str(d).lower() for d in patient_data.get('primary_input_diseases', []) or []
                        if d and d != '__unknown__'
                    )
                    original_mapped = set(
                        str(d).lower() for d in patient_data.get('original_mapped_diseases', []) or []
                        if d and d != '__unknown__'
                    )
                    check_diseases = primary_input or original_mapped
                    glaucoma_keywords = ('glaucoma', 'ocular hypertension', 'intraocular pressure')
                    cataract_keywords = ('cataract')
                    has_glaucoma = any(any(kw in d for kw in glaucoma_keywords) for d in check_diseases)
                    if not has_glaucoma:
                        for disease in check_diseases:
                            if any(kw in disease for kw in cataract_keywords):
                                exclusion_reason = f"青光眼药物对白内障无治疗作用: {drug_name}"
                                break

            # 20. 抗生素误用于真菌感染硬排除
            # 真菌感染需要抗真菌药，抗生素对真菌无效且可能加重病情
            if not exclusion_reason:
                drug_class_lower = str(drug.get('drug_class_en', '')).lower()
                antibiotic_keywords = (
                    'antibiotic', 'antibacterial', 'quinolone', 'fluoroquinolone',
                    'macrolide', 'cephalosporin', 'penicillin', 'tetracycline',
                    'lincosamide', 'nitroimidazole', 'sulfonamide antibiotic',
                    'glycopeptide', 'oxazolidinone', 'carbapenem', 'monobactam',
                )
                is_antibiotic = any(kw in drug_class_lower for kw in antibiotic_keywords)
                if is_antibiotic:
                    primary_input = set(
                        str(d).lower() for d in patient_data.get('primary_input_diseases', []) or []
                        if d and d != '__unknown__'
                    )
                    original_mapped = set(
                        str(d).lower() for d in patient_data.get('original_mapped_diseases', []) or []
                        if d and d != '__unknown__'
                    )
                    check_diseases = primary_input or original_mapped
                    fungal_keywords = ('fungal infection', 'candidiasis', 'candida', 'fungal', 'mycosis', 'ringworm', 'tinea', 'vaginal yeast')
                    bacterial_keywords = ('bacterial infection', 'bacterial', 'sepsis', 'cellulitis', 'pneumonia')
                    has_bacterial = any(any(kw in d for kw in bacterial_keywords) for d in check_diseases)
                    if not has_bacterial:
                        for disease in check_diseases:
                            if any(kw in disease for kw in fungal_keywords):
                                exclusion_reason = f"抗生素对真菌感染无效，需要抗真菌药: {drug_name}"
                                break

            # 21. 苯二氮卓类误用于OCD/强迫症硬排除
            # OCD一线治疗为SSRI(氟伏沙明/氟西汀/舍曲林)，苯二氮卓类不适用
            # 苯二氮卓类仅短期缓解焦虑症状，不治疗OCD核心病理
            if not exclusion_reason:
                drug_class_lower = str(drug.get('drug_class_en', '')).lower()
                is_benzodiazepine = 'benzodiazepine' in drug_class_lower
                if is_benzodiazepine:
                    primary_input = set(
                        str(d).lower() for d in patient_data.get('primary_input_diseases', []) or []
                        if d and d != '__unknown__'
                    )
                    original_mapped = set(
                        str(d).lower() for d in patient_data.get('original_mapped_diseases', []) or []
                        if d and d != '__unknown__'
                    )
                    check_diseases = primary_input or original_mapped
                    ocd_keywords = ('obsessive compulsive disorder', 'ocd', '强迫症')
                    anxiety_keywords = ('anxiety', 'panic', 'insomnia', 'seizure', 'epilepsy', 'alcohol withdrawal')
                    has_anxiety_need = any(any(kw in d for kw in anxiety_keywords) for d in check_diseases)
                    if not has_anxiety_need:
                        for disease in check_diseases:
                            if any(kw in disease for kw in ocd_keywords):
                                exclusion_reason = f"苯二氮卓类不是OCD一线治疗，需SSRI: {drug_name}"
                                break

            # Categorize: exclude (hard) or mark (soft, for doctor review)
            if exclusion_reason:
                if _is_hard_exclude(exclusion_reason):
                    excluded_drugs.append({
                        'drug_name': drug_name,
                        'reason': exclusion_reason,
                        'drug_data': drug,
                    })
                else:
                    # Soft exclude → mark for doctor review, keep in safe_candidates
                    marked_drugs.append({
                        'drug_name': drug_name,
                        'drug_data': drug,
                        'safety_tag': _extract_safety_tag(exclusion_reason),
                        'review_reason': exclusion_reason,
                    })
                    # Also keep in safe_candidates so it reaches ranking layer
                    safe_candidates.append(drug)
            else:
                safe_candidates.append(drug)

        logger.info(
            f"SafetyFilter: {len(safe_candidates)} safe (incl. {len(marked_drugs)} marked), "
            f"{len(excluded_drugs)} hard-excluded from {len(drug_candidates)} total"
        )
        return ExclusionResult(
            safe_candidates=safe_candidates,
            excluded_drugs=excluded_drugs,
            marked_candidates=marked_drugs,
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
            if renal_function in ('mild', 'mild_impairment', 'moderate', 'moderate_impairment', 'severe', 'severe_impairment'):
                renal_warning = _check_renal_warning(drug_name, renal_function, contraindications)
                if renal_warning:
                    warnings.append(renal_warning)
                    if renal_function in ('severe', 'severe_impairment'):
                        requires_review = True

            # 肝功能不全药物特异性提示
            if hepatic_function in ('mild', 'mild_impairment', 'moderate', 'moderate_impairment', 'severe', 'severe_impairment'):
                hepatic_warning = _check_hepatic_warning(drug_name, hepatic_function, contraindications)
                if hepatic_warning:
                    warnings.append(hepatic_warning)
                    if hepatic_function in ('severe', 'severe_impairment'):
                        requires_review = True

            # 育龄女性预防性提示 (gender=F, age 18-45)
            patient_gender = str(patient_data.get('gender', '')).upper()
            patient_age = patient_data.get('age', 0) or 0
            if patient_gender in ('F', 'FEMALE') and 18 <= patient_age <= 45:
                pregnancy_cat = drug.get('pregnancy_category', 'N')
                if pregnancy_cat in ('D', 'X'):
                    warnings.append(f"育龄女性注意: 妊娠{pregnancy_cat}级药物")
                    requires_review = True

            # 安全数据未验证检查: 药物不在禁忌症映射且不在交互映射中，
            # 说明其安全数据未经专业验证，需临床确认后方可使用
            # 注意: 不硬排除，仅标记警告和requires_review
            if drug_name not in contraindication_map and drug_name not in interaction_map:
                contraindication_type = 'data_unverified'
                warnings.append(f"安全数据未验证: {drug_name}")
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


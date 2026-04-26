"""临床匹配标准化器 — 统一禁忌症/过敏/疾病匹配逻辑

解决评审团发现的核心安全问题: 子串匹配可导致
(1) 过敏漏匹配→过敏性休克 (2) 禁忌误匹配→不必要排除

策略: 匹配前先标准化疾病名/过敏名, 然后做精确匹配+保守包含检查
过敏匹配使用更严格的精确匹配(可致命); 禁忌匹配使用标准化后包含检查
"""

import logging
from typing import Dict, Set, List, Any, Optional

logger = logging.getLogger(__name__)

# ── 标准化同义词映射表 ──
# 医学缩写/俗名 → 标准化全称(小写)

DISEASE_NORMALIZE: Dict[str, str] = {
    # 心血管
    'chf': 'congestive heart failure',
    'hf': 'heart failure',
    'htn': 'hypertension',
    'cad': 'coronary artery disease',
    'mi': 'myocardial infarction',
    'af': 'atrial fibrillation',
    'afl': 'atrial flutter',
    'dvt': 'deep vein thrombosis',
    'pe': 'pulmonary embolism',
    'pad': 'peripheral arterial disease',
    'pvd': 'peripheral vascular disease',
    # 呼吸
    'copd': 'chronic obstructive pulmonary disease',
    'asthma': 'asthma',
    'pneumonia': 'pneumonia',
    'bronchitis': 'bronchitis',
    'uri': 'upper respiratory infection',
    'urti': 'upper respiratory tract infection',
    # 内分泌
    'dm': 'diabetes mellitus',
    't2dm': 'type 2 diabetes mellitus',
    't1dm': 'type 1 diabetes mellitus',
    't2d': 'type 2 diabetes',
    't1d': 'type 1 diabetes',
    'hypothyroid': 'hypothyroidism',
    'hyperthyroid': 'hyperthyroidism',
    # 神经/精神
    'ms': 'multiple sclerosis',
    'adhd': 'attention deficit hyperactivity disorder',
    'gad': 'generalized anxiety disorder',
    'mdd': 'major depressive disorder',
    'sz': 'schizophrenia',
    'pd': 'parkinson disease',
    'epilepsy': 'epilepsy',
    'als': 'amyotrophic lateral sclerosis',
    # 肾/肝
    'ckd': 'chronic kidney disease',
    'esrd': 'end stage renal disease',
    'akd': 'acute kidney disease',
    'pud': 'peptic ulcer disease',
    'gerd': 'gastroesophageal reflux disease',
    'nash': 'nonalcoholic steatohepatitis',
    # 风湿/骨骼
    'ra': 'rheumatoid arthritis',
    'oa': 'osteoarthritis',
    'sle': 'systemic lupus erythematosus',
    'gout': 'gout',
    # 胃肠
    'ibd': 'inflammatory bowel disease',
    'uc': 'ulcerative colitis',
    'cd': 'crohn disease',
    'ibs': 'irritable bowel syndrome',
    # 传染病
    'hiv': 'human immunodeficiency virus',
    'hpv': 'human papillomavirus',
    'hsv': 'herpes simplex virus',
    'tb': 'tuberculosis',
    'utd': 'urinary tract disease',
    'uti': 'urinary tract infection',
    # 其他
    'bph': 'benign prostatic hyperplasia',
}

ALLERGY_NORMALIZE: Dict[str, str] = {
    # 过敏缩写/俗名 → 标准化全称
    'pcn': 'penicillin',
    'pen': 'penicillin',
    'asa': 'aspirin',
    'nsaid': 'nonsteroidal anti-inflammatory drug',
    'nsaids': 'nonsteroidal anti-inflammatory drug',
    'sulfa': 'sulfonamide',
    'sulfonamides': 'sulfonamide',
    'beta-lactam': 'beta-lactam',
    'beta lactam': 'beta-lactam',
    'statins': 'statin',
    'opiates': 'opioid',
    'opioids': 'opioid',
    'benzodiazepines': 'benzodiazepine',
    'ssris': 'selective serotonin reuptake inhibitor',
    'maois': 'monoamine oxidase inhibitor',
    'iodine': 'iodine',
    'latex': 'latex',
    'contrast': 'radiocontrast media',
    'contrast dye': 'radiocontrast media',
}


def normalize_disease(name: str) -> str:
    """标准化疾病名称

    Args:
        name: 疾病名(可为缩写/俗名)
    Returns:
        标准化后的全称(小写)
    """
    key = name.strip().lower()
    return DISEASE_NORMALIZE.get(key, key)


def normalize_allergy(name: str) -> str:
    """标准化过敏名称

    Args:
        name: 过敏名(可为缩写/俗名)
    Returns:
        标准化后的全称(小写)
    """
    key = name.strip().lower()
    return ALLERGY_NORMALIZE.get(key, key)


def match_allergy(
    patient_allergies: Set[str],
    contraindication_name: str,
) -> bool:
    """过敏匹配 — 使用精确匹配+保守策略(宁可误排不漏)

    过敏漏匹配可导致过敏性休克，必须严格:
    1. 标准化后精确相等匹配
    2. 标准化后包含匹配(仅当过敏名>=4字符，避免短名误匹配)
    3. 原始名精确相等匹配(fallback)

    Args:
        patient_allergies: 患者过敏集合(已小写)
        contraindication_name: 禁忌症名(原始)
    Returns:
        True if 匹配成功(应排除)
    """
    contra_normalized = normalize_allergy(contraindication_name.lower())

    for allergy in patient_allergies:
        allergy_normalized = normalize_allergy(allergy)

        # 1. 精确相等匹配(最安全)
        if allergy_normalized == contra_normalized:
            return True

        # 2. 包含匹配 — 仅当标准化名>=4字符(避免"sul"匹配"sulfonamide"等误匹配)
        #    且方向限定: 过敏名包含在禁忌名中 或 禁忌名包含在过敏名中
        if len(allergy_normalized) >= 4 and len(contra_normalized) >= 4:
            if allergy_normalized in contra_normalized or contra_normalized in allergy_normalized:
                return True

        # 3. 原始名精确匹配(fallback)
        if allergy.lower() == contraindication_name.lower():
            return True

    return False


def match_condition(
    patient_conditions: Set[str],
    contraindication_name: str,
) -> bool:
    """禁忌症/疾病匹配 — 使用标准化+包含检查

    禁忌匹配不如过敏严格(不会立即致命), 但仍需标准化:
    1. 标准化后精确相等匹配
    2. 标准化后包含匹配(双向，需>=4字符)
    3. 原始名包含匹配(保守fallback，标注"疑似匹配需确认")

    Args:
        patient_conditions: 患者疾病集合(已小写)
        contraindication_name: 禁忌症名
    Returns:
        True if 匹配成功
    """
    contra_normalized = normalize_disease(contraindication_name.lower())

    for condition in patient_conditions:
        cond_normalized = normalize_disease(condition)

        # 1. 精确相等匹配
        if cond_normalized == contra_normalized:
            return True

        # 2. 标准化后包含匹配(双向，>=4字符防误匹配)
        if len(cond_normalized) >= 4 and len(contra_normalized) >= 4:
            if cond_normalized in contra_normalized or contra_normalized in cond_normalized:
                return True

        # 3. 原始名包含匹配(fallback，保守)
        cond_lower = condition.lower()
        contra_lower = contraindication_name.lower()
        if len(cond_lower) >= 4 and len(contra_lower) >= 4:
            if cond_lower in contra_lower or contra_lower in cond_lower:
                return True

    return False


def match_indication(
    patient_conditions: Set[str],
    indication_condition: str,
) -> bool:
    """适应症匹配 — 使用标准化+包含检查

    Args:
        patient_conditions: 患者疾病集合(已小写)
        indication_condition: 适应症疾病名
    Returns:
        True if 匹配成功
    """
    ind_normalized = normalize_disease(indication_condition.lower())

    for condition in patient_conditions:
        cond_normalized = normalize_disease(condition)

        # 精确相等
        if cond_normalized == ind_normalized:
            return True

        # 包含匹配(双向)
        if len(cond_normalized) >= 4 and len(ind_normalized) >= 4:
            if cond_normalized in ind_normalized or ind_normalized in cond_normalized:
                return True

    return False
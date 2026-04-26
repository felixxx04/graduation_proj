"""共享特征记录构建器 — 消除runner/predictor代码重复

DRY原则: runner._build_raw_record() 和 predictor._build_record() 逻辑几乎完全相同,
两处副本可能产生不一致。抽取为公共函数。

build_feature_record() 统一构建特征记录字典(编码前)
"""

from typing import Dict, Any


def build_feature_record(
    patient_data: Dict[str, Any],
    drug_data: Dict[str, Any],
) -> Dict[str, Any]:
    """构建特征记录字典（编码前）

    Args:
        patient_data: 患者数据（含age, gender, diseases, allergies, current_medications等）
        drug_data: 药物数据（含generic_name, drug_class, pregnancy_category等）
    Returns:
        特征记录字典（字段名与schema.py FIELD_SCHEMA一致）
    """
    age = patient_data.get('age', 0) or 0
    if age < 10:
        age_group = '0-9'
    elif age < 20:
        age_group = '10-19'
    elif age < 30:
        age_group = '20-29'
    elif age < 40:
        age_group = '30-39'
    elif age < 50:
        age_group = '40-49'
    elif age < 60:
        age_group = '50-59'
    elif age < 70:
        age_group = '60-69'
    elif age < 80:
        age_group = '70-79'
    elif age < 90:
        age_group = '80-89'
    else:
        age_group = '90+'

    bmi = patient_data.get('bmi')
    if bmi is None or bmi == 0:
        bmi_group = 'unknown'
    elif bmi < 18.5:
        bmi_group = '<18.5'
    elif bmi < 24:
        bmi_group = '18.5-24'
    elif bmi < 28:
        bmi_group = '24-28'
    elif bmi < 32:
        bmi_group = '28-32'
    else:
        bmi_group = '32+'

    allergy_severity = 'none'
    allergies = patient_data.get('allergies', []) or patient_data.get('allergy_list', []) or []
    if allergies:
        allergy_severity = patient_data.get('allergy_severity', 'moderate') or 'moderate'

    diseases = patient_data.get('diseases', []) or []
    primary_disease = diseases[0] if diseases else '__unknown__'
    secondary_disease = diseases[1] if len(diseases) > 1 else '__unknown__'

    meds = patient_data.get('current_medications', []) or patient_data.get('medication_list', []) or []
    med_name_1 = str(meds[0]) if len(meds) > 0 else '__unknown__'
    med_name_2 = str(meds[1]) if len(meds) > 1 else '__unknown__'
    med_name_3 = str(meds[2]) if len(meds) > 2 else '__unknown__'
    med_name_4 = str(meds[3]) if len(meds) > 3 else '__unknown__'

    return {
        'patient_id': patient_data.get('id', patient_data.get('patient_id', 'unknown')),
        'age_group': age_group,
        'gender': patient_data.get('gender', 'UNKNOWN'),
        'bmi_group': bmi_group,
        'renal_function': patient_data.get('renal_function', 'unknown') or 'unknown',
        'hepatic_function': patient_data.get('hepatic_function', 'unknown') or 'unknown',
        'primary_disease': primary_disease,
        'secondary_disease': secondary_disease,
        'allergy_severity': allergy_severity,
        'drug_class': drug_data.get('drug_class', drug_data.get('drug_class_en', '__unknown__')),
        'med_class_1': med_name_1,
        'med_class_2': med_name_2,
        'med_class_3': med_name_3,
        'med_class_4': med_name_4,
        'pregnancy_cat': drug_data.get('pregnancy_category', 'N') or 'N',
        'rx_otc': drug_data.get('rx_otc', drug_data.get('is_otc', 'RX')) or 'RX',
        'drug_candidate': drug_data.get('generic_name', drug_data.get('name', '__unknown__')),
        # 连续特征
        'age_raw': float(age),
        'bmi_raw': float(bmi) if bmi else 0.0,
        'gfr_raw': float(patient_data.get('gfr', patient_data.get('egfr', 0)) or 0),
        'liver_score_raw': float(patient_data.get('liver_score', patient_data.get('alt', 0)) or 0),
    }
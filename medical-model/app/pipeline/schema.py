"""字段定义与 field_dims schema

v2: 删除contra_flag(零信息量), 重新校准DATA_SIZE_CONFIGS
注意: drug_candidate dim标注为预估值, 实际值由FeatureEncoder.fit()确定
"""

# 字段 schema 定义 (v2: 删除contra_flag)
FIELD_SCHEMA = {
    'age_group': {
        'dim': 10,
        'type': 'categorical',
        'source': 'patient.age → 分桶',
    },
    'gender': {
        'dim': 3,
        'type': 'categorical',
        'source': 'patient.gender (MALE/FEMALE/UNKNOWN)',
    },
    'bmi_group': {
        'dim': 6,
        'type': 'categorical',
        'source': 'BMI分桶',
    },
    'renal_function': {
        'dim': 5,
        'type': 'categorical',
        'source': 'health_record.renal_function',
    },
    'hepatic_function': {
        'dim': 5,
        'type': 'categorical',
        'source': 'health_record.hepatic_function',
    },
    'primary_disease': {
        'dim': 80,
        'type': 'categorical',
        'source': 'disease.id',
    },
    'secondary_disease': {
        'dim': 80,
        'type': 'categorical',
        'source': 'disease.id',
    },
    'allergy_severity': {
        'dim': 5,
        'type': 'categorical',
        'source': 'allergy.severity',
    },
    'drug_class': {
        'dim': 50,
        'type': 'categorical',
        'source': 'drug_category.id',
    },
    'med_class_1': {
        'dim': 50,
        'type': 'categorical',
        'source': 'patient_medication → drug name',
    },
    'med_class_2': {
        'dim': 50,
        'type': 'categorical',
        'source': 'patient_medication → drug name',
    },
    'med_class_3': {
        'dim': 50,
        'type': 'categorical',
        'source': 'patient_medication → drug name',
    },
    'med_class_4': {
        'dim': 50,
        'type': 'categorical',
        'source': 'patient_medication → drug name',
    },
    'pregnancy_cat': {
        'dim': 6,
        'type': 'categorical',
        'source': 'drug.pregnancy_category',
    },
    'rx_otc': {
        'dim': 3,
        'type': 'categorical',
        'source': 'drug.rx_otc',
    },
    'drug_candidate': {
        'dim': 719,
        'type': 'categorical',
        'source': 'drug.generic_name (718+1 unknown, 预估值)',
    },
}

# 连续特征旁路
CONTINUOUS_FEATURES = ['age_raw', 'bmi_raw', 'gfr_raw', 'liver_score_raw']

# 字段顺序（与 field_indices 数组索引对应）
FIELD_ORDER = list(FIELD_SCHEMA.keys())

# 默认 field_dims（预估值，实际值由 FeatureEncoder.fit() 确定）
# ⚠️ 重要: 不要直接用DEFAULT_FIELD_DIMS初始化模型，必须从encoder.field_dims获取
DEFAULT_FIELD_DIMS = [f['dim'] for f in FIELD_SCHEMA.values()]

# v2: 重新校准DATA_SIZE_CONFIGS — 考虑drug_candidate vocab占比
DATA_SIZE_CONFIGS = {
    'small': {    # < 5000 samples
        'embed_dim': 4,
        'hidden_dims': [32, 16],
        'dropout': 0.05,
        'weight_decay': 1e-3,
    },
    'medium': {  # 5000-30000 samples
        'embed_dim': 8,
        'hidden_dims': [64, 32],
        'dropout': 0.1,
        'weight_decay': 5e-4,
    },
    'large': {   # > 30000 samples
        'embed_dim': 8,
        'hidden_dims': [128, 64],
        'dropout': 0.2,
        'weight_decay': 1e-4,
    },
}


def get_data_size_category(num_samples: int) -> str:
    """根据样本量返回数据规模分类"""
    if num_samples < 5000:
        return 'small'
    elif num_samples < 30000:
        return 'medium'
    else:
        return 'large'


def get_model_config_for_data_size(num_samples: int) -> dict:
    """根据样本量返回适配的模型配置"""
    category = get_data_size_category(num_samples)
    return DATA_SIZE_CONFIGS[category]
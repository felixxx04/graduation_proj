-- =============================================
-- 差分隐私保护的医疗用药推荐系统 - 数据库迁移V2
-- 新增15+标准表 + 现有表字段扩展
-- 执行前请先备份现有数据库
-- =============================================

SET NAMES utf8mb4;
USE medical_recommendation;

-- =============================================
-- 一、新增标准表
-- =============================================

-- 1. 疾病/症状/生理状态标准表（名称映射权威来源）
CREATE TABLE IF NOT EXISTS disease (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '疾病ID',
    name VARCHAR(100) NOT NULL COMMENT '中文名称',
    name_en VARCHAR(200) NOT NULL COMMENT '英文名称',
    type ENUM('disease', 'symptom', 'physiological_condition', 'allergy_type') NOT NULL COMMENT '类型',
    category VARCHAR(50) COMMENT '疾病分类(心血管/内分泌/呼吸等)',
    icd10_code VARCHAR(20) COMMENT 'ICD-10编码',
    severity_default VARCHAR(20) DEFAULT 'moderate' COMMENT '默认严重程度(mild/moderate/severe/critical)',
    is_chronic BOOLEAN DEFAULT FALSE COMMENT '是否慢性病',
    description TEXT COMMENT '描述',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_name_en (name_en),
    INDEX idx_type (type),
    INDEX idx_category (category),
    INDEX idx_icd10 (icd10_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='疾病/症状/生理状态标准表';

-- 2. 疾病别名映射表
CREATE TABLE IF NOT EXISTS disease_alias (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '别名ID',
    disease_id BIGINT NOT NULL COMMENT '疾病ID',
    alias_name VARCHAR(100) NOT NULL COMMENT '别名',
    source VARCHAR(50) COMMENT '来源(FDA/ICD10/clinical/common)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (disease_id) REFERENCES disease(id) ON DELETE CASCADE,
    UNIQUE KEY uk_alias (alias_name),
    INDEX idx_disease_id (disease_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='疾病别名映射表';

-- 3. 药物分类标准表
CREATE TABLE IF NOT EXISTS drug_category (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '分类ID',
    name VARCHAR(100) NOT NULL COMMENT '中文分类名',
    name_en VARCHAR(200) NOT NULL COMMENT '英文分类名',
    atc_level1 VARCHAR(10) COMMENT 'ATC一级编码',
    description TEXT COMMENT '描述',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_name_en (name_en),
    INDEX idx_atc (atc_level1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='药物分类标准表';

-- =============================================
-- 二、药物关联表（拆解drug JSON字段）
-- =============================================

-- 4. 药物-适应症映射
CREATE TABLE IF NOT EXISTS drug_indication (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '映射ID',
    drug_id BIGINT NOT NULL COMMENT '药物ID',
    disease_id BIGINT NOT NULL COMMENT '疾病ID',
    evidence_level ENUM('primary', 'secondary', 'off_label') DEFAULT 'primary' COMMENT '证据等级',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (drug_id) REFERENCES drug(id) ON DELETE CASCADE,
    FOREIGN KEY (disease_id) REFERENCES disease(id) ON DELETE CASCADE,
    UNIQUE KEY uk_drug_disease (drug_id, disease_id),
    INDEX idx_drug_id (drug_id),
    INDEX idx_disease_id (disease_id),
    INDEX idx_evidence (evidence_level)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='药物-适应症映射';

-- 5. 药物禁忌映射（核心安全表）
CREATE TABLE IF NOT EXISTS drug_contraindication (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '禁忌ID',
    drug_id BIGINT NOT NULL COMMENT '药物ID',
    disease_id BIGINT COMMENT '疾病ID(对应disease表)',
    contraindication_name VARCHAR(200) NOT NULL COMMENT '禁忌名称(英文原始值)',
    contraindication_type ENUM('disease', 'allergy_type', 'physiological_condition', 'drug_class') NOT NULL COMMENT '禁忌类型',
    severity ENUM('absolute', 'relative') NOT NULL COMMENT '严重程度(绝对禁忌/相对禁忌)',
    reason TEXT COMMENT '禁忌原因',
    clinical_note TEXT COMMENT '临床备注',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (drug_id) REFERENCES drug(id) ON DELETE CASCADE,
    FOREIGN KEY (disease_id) REFERENCES disease(id) ON DELETE SET NULL,
    UNIQUE KEY uk_drug_disease_severity (drug_id, disease_id, severity),
    INDEX idx_drug_severity (drug_id, severity),
    INDEX idx_type (contraindication_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='药物禁忌映射（核心安全表）';

-- 6. 药物-药物相互作用
CREATE TABLE IF NOT EXISTS drug_interaction (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '交互ID',
    drug_id_a BIGINT NOT NULL COMMENT '药物A ID',
    drug_id_b BIGINT NOT NULL COMMENT '药物B ID',
    interaction_type ENUM('major', 'moderate', 'minor') NOT NULL COMMENT '交互严重程度',
    mechanism TEXT COMMENT '交互机制',
    clinical_effect TEXT COMMENT '临床效果',
    management_note TEXT COMMENT '管理建议',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (drug_id_a) REFERENCES drug(id) ON DELETE CASCADE,
    FOREIGN KEY (drug_id_b) REFERENCES drug(id) ON DELETE CASCADE,
    UNIQUE KEY uk_drug_pair (drug_id_a, drug_id_b),
    INDEX idx_drug_a (drug_id_a),
    INDEX idx_drug_b (drug_id_b),
    INDEX idx_type (interaction_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='药物-药物相互作用';

-- 7. 药物副作用
CREATE TABLE IF NOT EXISTS drug_side_effect (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '副作用ID',
    drug_id BIGINT NOT NULL COMMENT '药物ID',
    effect_name VARCHAR(200) NOT NULL COMMENT '副作用名称(英文)',
    effect_name_cn VARCHAR(200) COMMENT '副作用中文名',
    severity ENUM('common_mild', 'uncommon_moderate', 'rare_severe', 'very_rare_critical') DEFAULT 'common_mild' COMMENT '严重程度',
    frequency VARCHAR(50) COMMENT '发生频率',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (drug_id) REFERENCES drug(id) ON DELETE CASCADE,
    INDEX idx_drug_id (drug_id),
    INDEX idx_severity (severity)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='药物副作用';

-- =============================================
-- 三、患者关联表（拆解health_record JSON字段）
-- =============================================

-- 8. 患者-疾病关联
CREATE TABLE IF NOT EXISTS patient_disease (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '关联ID',
    patient_id BIGINT NOT NULL COMMENT '患者ID',
    disease_id BIGINT NOT NULL COMMENT '疾病ID',
    health_record_id BIGINT COMMENT '健康档案ID',
    diagnosed_date DATE COMMENT '诊断日期',
    severity ENUM('mild', 'moderate', 'severe', 'critical') DEFAULT 'moderate' COMMENT '严重程度',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否活跃',
    source ENUM('diagnosed', 'inferred') DEFAULT 'diagnosed' COMMENT '来源',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (patient_id) REFERENCES patient(id) ON DELETE CASCADE,
    FOREIGN KEY (disease_id) REFERENCES disease(id) ON DELETE CASCADE,
    FOREIGN KEY (health_record_id) REFERENCES patient_health_record(id) ON DELETE SET NULL,
    INDEX idx_patient_active (patient_id, is_active),
    INDEX idx_disease_id (disease_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='患者-疾病关联';

-- 9. 患者-过敏关联
CREATE TABLE IF NOT EXISTS patient_allergy (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '过敏ID',
    patient_id BIGINT NOT NULL COMMENT '患者ID',
    allergy_type ENUM('drug', 'food', 'environmental', 'other') DEFAULT 'drug' COMMENT '过敏类型',
    allergy_name VARCHAR(200) NOT NULL COMMENT '过敏名称',
    disease_id BIGINT COMMENT '对应疾病ID(如penicillin allergy映射到disease表)',
    severity ENUM('mild', 'moderate', 'severe', 'anaphylaxis') DEFAULT 'moderate' COMMENT '严重程度',
    reaction VARCHAR(200) COMMENT '过敏反应描述',
    confirmed BOOLEAN DEFAULT FALSE COMMENT '是否确诊',
    health_record_id BIGINT COMMENT '健康档案ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (patient_id) REFERENCES patient(id) ON DELETE CASCADE,
    FOREIGN KEY (disease_id) REFERENCES disease(id) ON DELETE SET NULL,
    FOREIGN KEY (health_record_id) REFERENCES patient_health_record(id) ON DELETE SET NULL,
    INDEX idx_patient_id (patient_id),
    INDEX idx_severity (severity)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='患者-过敏关联';

-- 10. 患者-当前用药关联
CREATE TABLE IF NOT EXISTS patient_medication (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '用药ID',
    patient_id BIGINT NOT NULL COMMENT '患者ID',
    drug_id BIGINT NOT NULL COMMENT '药物ID',
    health_record_id BIGINT COMMENT '健康档案ID',
    dosage VARCHAR(50) COMMENT '剂量',
    frequency VARCHAR(100) COMMENT '用药频率',
    start_date DATE COMMENT '开始日期',
    end_date DATE COMMENT '结束日期',
    is_current BOOLEAN DEFAULT TRUE COMMENT '是否当前用药',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (patient_id) REFERENCES patient(id) ON DELETE CASCADE,
    FOREIGN KEY (drug_id) REFERENCES drug(id) ON DELETE CASCADE,
    FOREIGN KEY (health_record_id) REFERENCES patient_health_record(id) ON DELETE SET NULL,
    INDEX idx_patient_current (patient_id, is_current),
    INDEX idx_drug_id (drug_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='患者-当前用药关联';

-- =============================================
-- 四、推荐明细表
-- =============================================

-- 11. 推荐药物明细
CREATE TABLE IF NOT EXISTS recommendation_detail (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '明细ID',
    recommendation_id BIGINT NOT NULL COMMENT '推荐ID',
    drug_id BIGINT NOT NULL COMMENT '药物ID',
    score DECIMAL(10,4) COMMENT '原始分数',
    score_with_dp DECIMAL(10,4) COMMENT 'DP噪声后分数',
    dp_noise_value DECIMAL(10,6) COMMENT 'DP噪声值',
    confidence DECIMAL(5,2) COMMENT '置信度百分比',
    rank_position INT COMMENT '排名位置',
    reason TEXT COMMENT '推荐理由',
    matched_disease_id BIGINT COMMENT '匹配疾病ID',
    is_excluded BOOLEAN DEFAULT FALSE COMMENT '是否被排除',
    exclusion_reason VARCHAR(200) COMMENT '排除原因',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (recommendation_id) REFERENCES recommendation(id) ON DELETE CASCADE,
    FOREIGN KEY (drug_id) REFERENCES drug(id) ON DELETE CASCADE,
    FOREIGN KEY (matched_disease_id) REFERENCES disease(id) ON DELETE SET NULL,
    INDEX idx_drug_excluded (drug_id, is_excluded),
    INDEX idx_recommendation_id (recommendation_id),
    INDEX idx_rank (rank_position)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='推荐药物明细';

-- =============================================
-- 五、推断映射表
-- =============================================

-- 12. 药物类别推断疾病
CREATE TABLE IF NOT EXISTS disease_category_inference (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '推断ID',
    category_id BIGINT NOT NULL COMMENT '药物分类ID',
    disease_id BIGINT NOT NULL COMMENT '推断疾病ID',
    confidence ENUM('high', 'medium') DEFAULT 'medium' COMMENT '推断置信度',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (category_id) REFERENCES drug_category(id) ON DELETE CASCADE,
    FOREIGN KEY (disease_id) REFERENCES disease(id) ON DELETE CASCADE,
    UNIQUE KEY uk_category_disease (category_id, disease_id),
    INDEX idx_category_id (category_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='药物类别推断疾病';

-- =============================================
-- 六、修改现有表
-- =============================================

-- patient — 新增字段
ALTER TABLE patient
    ADD COLUMN blood_type VARCHAR(5) COMMENT '血型' AFTER id_card,
    ADD COLUMN height DECIMAL(5,2) COMMENT '身高(cm)' AFTER blood_type,
    ADD COLUMN weight DECIMAL(5,2) COMMENT '体重(kg)' AFTER height,
    ADD COLUMN bmi DECIMAL(5,2) COMMENT 'BMI指数' AFTER weight,
    ADD COLUMN is_smoker BOOLEAN DEFAULT FALSE COMMENT '是否吸烟' AFTER bmi,
    ADD COLUMN is_drinker BOOLEAN DEFAULT FALSE COMMENT '是否饮酒' AFTER is_smoker,
    ADD COLUMN primary_diagnosis VARCHAR(200) COMMENT '主要诊断' AFTER is_drinker;

-- drug — 新增字段，扩展为完整药物信息
ALTER TABLE drug
    ADD COLUMN atc_code VARCHAR(20) COMMENT 'ATC编码' AFTER generic_name,
    ADD COLUMN mechanism_of_action TEXT COMMENT '作用机制' AFTER atc_code,
    ADD COLUMN route_of_administration VARCHAR(100) COMMENT '给药途径' AFTER mechanism_of_action,
    ADD COLUMN pregnancy_category ENUM('A', 'B', 'C', 'D', 'X', 'N') DEFAULT 'N' COMMENT '妊娠分级' AFTER route_of_administration,
    ADD COLUMN is_otc ENUM('RX', 'OTC', 'RX-OTC') DEFAULT 'RX' COMMENT '处方类型' AFTER pregnancy_category,
    ADD COLUMN category_id BIGINT COMMENT '药物分类ID' AFTER is_otc,
    ADD COLUMN approval_status ENUM('approved', 'investigational', 'discontinued') DEFAULT 'approved' COMMENT '审批状态' AFTER category_id,
    ADD COLUMN dosage_form VARCHAR(100) COMMENT '剂型' AFTER approval_status,
    ADD COLUMN strength VARCHAR(100) COMMENT '规格' AFTER dosage_form,
    ADD COLUMN drug_class_en VARCHAR(200) COMMENT '英文药物分类(Drug Class from dataset)' AFTER strength,
    ADD FOREIGN KEY (category_id) REFERENCES drug_category(id) ON DELETE SET NULL;

-- patient_health_record — 新增生化指标字段
ALTER TABLE patient_health_record
    ADD COLUMN smoking_status ENUM('never', 'former', 'current', 'unknown') DEFAULT 'unknown' COMMENT '吸烟状态' AFTER symptoms,
    ADD COLUMN drinking_status ENUM('none', 'occasional', 'regular', 'heavy', 'unknown') DEFAULT 'unknown' COMMENT '饮酒状态' AFTER smoking_status,
    ADD COLUMN renal_function ENUM('normal', 'mild_impairment', 'moderate_impairment', 'severe_impairment', 'unknown') DEFAULT 'unknown' COMMENT '肾功能' AFTER drinking_status,
    ADD COLUMN hepatic_function ENUM('normal', 'mild_impairment', 'moderate_impairment', 'severe_impairment', 'unknown') DEFAULT 'unknown' COMMENT '肝功能' AFTER renal_function,
    ADD COLUMN blood_pressure_systolic INT COMMENT '收缩压(mmHg)' AFTER hepatic_function,
    ADD COLUMN blood_pressure_diastolic INT COMMENT '舒张压(mmHg)' AFTER blood_pressure_systolic,
    ADD COLUMN fasting_glucose DECIMAL(5,2) COMMENT '空腹血糖(mmol/L)' AFTER blood_pressure_diastolic,
    ADD COLUMN hba1c DECIMAL(5,2) COMMENT '糖化血红蛋白(%)' AFTER fasting_glucose,
    ADD COLUMN cholesterol_total DECIMAL(5,2) COMMENT '总胆固醇(mmol/L)' AFTER hba1c,
    ADD COLUMN cholesterol_ldl DECIMAL(5,2) COMMENT 'LDL胆固醇(mmol/L)' AFTER cholesterol_total,
    ADD COLUMN heart_rate INT COMMENT '心率(bpm)' AFTER cholesterol_ldl;

-- recommendation — 新增字段
ALTER TABLE recommendation
    ADD COLUMN dp_noise_mechanism VARCHAR(20) COMMENT 'DP噪声机制(laplace/gaussian/geometric)' AFTER epsilon_used,
    ADD COLUMN total_candidates INT COMMENT '候选药物总数' AFTER dp_noise_mechanism,
    ADD COLUMN total_excluded INT COMMENT '排除药物数' AFTER total_candidates,
    ADD COLUMN inferred_diseases_json JSON COMMENT '推断疾病列表' AFTER total_excluded,
    ADD COLUMN excluded_drugs_json JSON COMMENT '排除药物列表(含原因)' AFTER inferred_diseases_json,
    ADD COLUMN status ENUM('pending', 'accepted', 'rejected') DEFAULT 'pending' COMMENT '推荐状态' AFTER excluded_drugs_json,
    ADD COLUMN feedback_note TEXT COMMENT '反馈备注' AFTER status,
    ADD COLUMN model_version VARCHAR(50) COMMENT '模型版本' AFTER feedback_note,
    ADD COLUMN duration_ms INT COMMENT '推理耗时(ms)' AFTER model_version;

-- privacy_config — 调整为双层DP配置
ALTER TABLE privacy_config
    ADD COLUMN epsilon_per_inference DECIMAL(10,4) DEFAULT 0.1 COMMENT '单次推理epsilon' AFTER user_id,
    ADD COLUMN epsilon_training DECIMAL(10,4) DEFAULT 1.0 COMMENT '训练epsilon' AFTER epsilon_per_inference,
    ADD COLUMN dp_max_grad_norm DECIMAL(10,4) DEFAULT 1.0 COMMENT 'DP-SGD最大梯度裁剪范数' AFTER epsilon_training,
    MODIFY COLUMN noise_mechanism ENUM('laplace', 'gaussian', 'geometric') DEFAULT 'laplace' COMMENT '噪声机制',
    MODIFY COLUMN privacy_budget DECIMAL(10,4) DEFAULT 10.0 COMMENT '总隐私预算';

-- privacy_ledger — 新增application_stage字段
ALTER TABLE privacy_ledger
    ADD COLUMN application_stage ENUM('inference', 'training', 'data_collection') DEFAULT 'inference' COMMENT '应用阶段' AFTER event_type;

-- 注意：旧列 epsilon 保留但标记deprecated，新列 epsilon_per_inference 和 epsilon_training 替代
-- 未来清理时删除旧 epsilon 列

-- =============================================
-- 七、数据一致性约束
-- =============================================

-- drug_interaction: 确保 drug_id_a < drug_id_b（防止重复）
-- 应用层确保插入时 drug_id_a < drug_id_b

-- drug: 确保 generic_name 有值（数据集主键）
ALTER TABLE drug
    MODIFY COLUMN generic_name VARCHAR(100) NOT NULL COMMENT '通用名(英文，数据集主键)',
    ADD UNIQUE KEY uk_generic_name (generic_name);
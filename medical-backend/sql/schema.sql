-- =============================================
-- 差分隐私保护的医疗用药推荐系统 - 数据库表结构
-- 数据库名: medical_recommendation
-- 字符集: utf8mb4
-- =============================================

SET NAMES utf8mb4;

-- 创建数据库
CREATE DATABASE IF NOT EXISTS medical_recommendation
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE medical_recommendation;

-- =============================================
-- 1. 系统用户表
-- =============================================
CREATE TABLE sys_user (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '用户ID',
    username VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
    password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希(BCrypt)',
    role ENUM('admin', 'doctor', 'researcher') DEFAULT 'doctor' COMMENT '角色',
    enabled BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统用户表';

-- =============================================
-- 2. 患者表
-- =============================================
CREATE TABLE patient (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '患者ID',
    name VARCHAR(100) NOT NULL COMMENT '姓名',
    gender ENUM('MALE', 'FEMALE', 'UNKNOWN') DEFAULT 'UNKNOWN' COMMENT '性别',
    birth_date DATE COMMENT '出生日期',
    phone VARCHAR(20) COMMENT '联系电话',
    id_card VARCHAR(18) COMMENT '身份证号(加密存储)',
    address VARCHAR(255) COMMENT '地址',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_name (name),
    INDEX idx_gender (gender)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='患者表';

-- =============================================
-- 3. 患者健康档案表
-- =============================================
CREATE TABLE patient_health_record (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '记录ID',
    patient_id BIGINT NOT NULL COMMENT '患者ID',
    record_date DATE NOT NULL COMMENT '记录日期',
    age INT COMMENT '年龄',
    height DECIMAL(5,2) COMMENT '身高(cm)',
    weight DECIMAL(5,2) COMMENT '体重(kg)',
    blood_type VARCHAR(5) COMMENT '血型',
    chronic_diseases JSON COMMENT '慢性病列表 ["高血压", "糖尿病"]',
    allergies JSON COMMENT '过敏史列表 ["青霉素", "磺胺类"]',
    current_medications JSON COMMENT '当前用药列表 ["二甲双胍", "氨氯地平"]',
    medical_history TEXT COMMENT '病史描述',
    symptoms TEXT COMMENT '当前症状',
    is_latest BOOLEAN DEFAULT TRUE COMMENT '是否最新记录',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (patient_id) REFERENCES patient(id) ON DELETE CASCADE,
    INDEX idx_patient_id (patient_id),
    INDEX idx_record_date (record_date),
    INDEX idx_patient_latest (patient_id, is_latest)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='患者健康档案表';

-- =============================================
-- 4. 药物表
-- =============================================
CREATE TABLE drug (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '药物ID',
    drug_code VARCHAR(20) UNIQUE COMMENT '药物编码',
    name VARCHAR(100) NOT NULL UNIQUE COMMENT '药物名称',
    generic_name VARCHAR(100) COMMENT '通用名',
    category VARCHAR(50) COMMENT '药物分类',
    indications JSON COMMENT '适应症列表',
    contraindications JSON COMMENT '禁忌症列表',
    side_effects JSON COMMENT '副作用列表',
    interactions JSON COMMENT '相互作用列表',
    typical_dosage VARCHAR(50) COMMENT '常用剂量',
    typical_frequency VARCHAR(100) COMMENT '用药频率',
    description TEXT COMMENT '药物说明',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_name (name),
    INDEX idx_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='药物表';

-- =============================================
-- 5. 推荐记录表
-- =============================================
CREATE TABLE recommendation (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '推荐ID',
    patient_id BIGINT COMMENT '患者ID(可为空，匿名推荐)',
    user_id BIGINT NOT NULL COMMENT '操作用户ID',
    input_data JSON COMMENT '输入特征(脱敏后)',
    result_data JSON COMMENT '推荐结果',
    dp_enabled BOOLEAN DEFAULT TRUE COMMENT '是否启用差分隐私',
    epsilon_used DECIMAL(10,4) COMMENT '消耗的隐私预算',
    recommendation_type ENUM('realtime', 'batch') DEFAULT 'realtime' COMMENT '推荐类型',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (patient_id) REFERENCES patient(id) ON DELETE SET NULL,
    FOREIGN KEY (user_id) REFERENCES sys_user(id),
    INDEX idx_patient_id (patient_id),
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='推荐记录表';

-- =============================================
-- 6. 隐私预算账本
-- =============================================
CREATE TABLE privacy_ledger (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '账本ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    session_id VARCHAR(50) COMMENT '会话ID',
    event_type ENUM('recommendation', 'training', 'query') COMMENT '事件类型',
    epsilon_spent DECIMAL(10,6) COMMENT '消耗的epsilon',
    delta_spent DECIMAL(20,12) COMMENT '消耗的delta',
    noise_mechanism VARCHAR(20) COMMENT '噪声机制',
    note VARCHAR(255) COMMENT '备注',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (user_id) REFERENCES sys_user(id),
    INDEX idx_user_id (user_id),
    INDEX idx_session_id (session_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='隐私预算账本';

-- =============================================
-- 7. 隐私配置表
-- =============================================
CREATE TABLE privacy_config (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '配置ID',
    user_id BIGINT NOT NULL UNIQUE COMMENT '用户ID',
    epsilon DECIMAL(10,4) DEFAULT 0.1 COMMENT '单次推理epsilon',
    delta DECIMAL(20,12) DEFAULT 0.00001 COMMENT 'delta参数',
    sensitivity DECIMAL(10,4) DEFAULT 1.0 COMMENT '敏感度',
    noise_mechanism ENUM('laplace', 'gaussian') DEFAULT 'laplace' COMMENT '噪声机制',
    application_stage ENUM('data', 'gradient', 'model') DEFAULT 'model' COMMENT '应用阶段',
    privacy_budget DECIMAL(10,4) DEFAULT 1.0 COMMENT '总隐私预算',
    budget_used DECIMAL(10,4) DEFAULT 0.0 COMMENT '已使用预算',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (user_id) REFERENCES sys_user(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='隐私配置表';

-- =============================================
-- 8. 系统配置表
-- =============================================
CREATE TABLE system_config (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '配置ID',
    config_key VARCHAR(100) NOT NULL UNIQUE COMMENT '配置键',
    config_value TEXT COMMENT '配置值',
    description VARCHAR(255) COMMENT '配置说明',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统配置表';

-- =============================================
-- 9. 操作日志表
-- =============================================
CREATE TABLE operation_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '日志ID',
    user_id BIGINT COMMENT '操作用户ID',
    action VARCHAR(50) NOT NULL COMMENT '操作类型',
    target_type VARCHAR(50) COMMENT '目标类型',
    target_id BIGINT COMMENT '目标ID',
    detail JSON COMMENT '操作详情',
    ip_address VARCHAR(45) COMMENT 'IP地址',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (user_id) REFERENCES sys_user(id) ON DELETE SET NULL,
    INDEX idx_user_id (user_id),
    INDEX idx_action (action),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='操作日志表';

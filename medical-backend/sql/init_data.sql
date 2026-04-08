-- =============================================
-- 初始数据 - 管理员账户和默认配置
-- =============================================

SET NAMES utf8mb4;
USE medical_recommendation;

-- 插入默认管理员账户
-- 默认密码请查看部署文档
INSERT INTO sys_user (username, password_hash, role, enabled) VALUES
('admin', '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBOsl7iAt9P5C.', 'admin', TRUE),
('doctor1', '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBOsl7iAt9P5C.', 'doctor', TRUE),
('researcher1', '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBOsl7iAt9P5C.', 'researcher', TRUE);

-- 为每个用户创建默认隐私配置
INSERT INTO privacy_config (user_id, epsilon, delta, sensitivity, noise_mechanism, application_stage, privacy_budget, budget_used)
SELECT id, 0.1, 0.00001, 1.0, 'laplace', 'model', 1.0, 0.0
FROM sys_user;

-- 插入系统默认配置
INSERT INTO system_config (config_key, config_value, description) VALUES
('system.name', '差分隐私保护的医疗用药推荐系统', '系统名称'),
('system.version', '1.0.0', '系统版本'),
('privacy.default_epsilon', '0.1', '默认单次推理隐私预算'),
('privacy.default_budget', '1.0', '默认总会话隐私预算'),
('privacy.default_mechanism', 'laplace', '默认噪声机制'),
('recommendation.top_k', '4', '默认推荐数量'),
('recommendation.confidence_threshold', '70', '推荐置信度阈值');

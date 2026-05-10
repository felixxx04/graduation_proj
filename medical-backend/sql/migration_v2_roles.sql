-- =============================================
-- 迁移脚本：v2 三角色重构 (admin/doctor/patient)
-- 执行方式: mysql -u root -p medical_recommendation < migration_v2_roles.sql
-- =============================================

SET NAMES utf8mb4;
USE medical_recommendation;

-- 1. 删除 researcher 账号（如存在）
DELETE FROM privacy_config WHERE user_id IN (SELECT id FROM sys_user WHERE username = 'researcher1');
DELETE FROM sys_user WHERE username = 'researcher1';

-- 2. 修改 sys_user.role 枚举
ALTER TABLE sys_user MODIFY COLUMN role ENUM('admin', 'doctor', 'patient') DEFAULT 'patient';

-- 3. 将原 doctor1 改为 patient1
UPDATE sys_user SET username = 'patient1', role = 'patient' WHERE username = 'doctor1';

-- 4. 新增真正的 doctor 账号（密码 admin123 的 BCrypt hash）
INSERT INTO sys_user (username, password_hash, role, enabled) VALUES
('doctor1', '$2a$10$lut2nnnjykVjZ.8lPGoyPuwr9q1LnGVK8tMLJ0tNc20L59nqk1QBm', 'doctor', TRUE);

-- 5. 为新 doctor1 创建隐私配置
INSERT INTO privacy_config (user_id, epsilon, delta, sensitivity, noise_mechanism, application_stage, privacy_budget, budget_used)
SELECT id, 0.1, 0.00001, 1.0, 'laplace', 'model', 10.0, 0.0
FROM sys_user WHERE username = 'doctor1';

-- 6. recommendation 表新增审核状态字段
ALTER TABLE recommendation ADD COLUMN review_status ENUM('pending', 'confirmed', 'modified', 'rejected') DEFAULT 'pending' COMMENT '审核状态';

-- 7. review_log 表新增诊疗建议字段
ALTER TABLE review_log ADD COLUMN treatment_advice TEXT COMMENT '医生诊疗建议（自由文本）';
ALTER TABLE review_log ADD COLUMN treatment_template VARCHAR(50) COMMENT '使用的诊疗模板名称';

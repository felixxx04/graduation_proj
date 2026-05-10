-- =============================================
-- 迁移脚本：v2.1 recommendation_id 类型统一
-- 前置条件：migration_v2_roles.sql 已执行
-- 执行方式: mysql -u root -p medical_recommendation < migration_v2_1_type_fix.sql
-- =============================================

SET NAMES utf8mb4;
USE medical_recommendation;

-- 校验：检查是否有无法转为数字的 recommendation_id（如返回行则需先手动清理）
SELECT COUNT(*) AS non_numeric_rows FROM review_log WHERE recommendation_id IS NOT NULL AND recommendation_id NOT REGEXP '^[0-9]+$';

START TRANSACTION;

ALTER TABLE review_log MODIFY COLUMN recommendation_id BIGINT;
ALTER TABLE review_log ADD CONSTRAINT fk_review_recommendation FOREIGN KEY (recommendation_id) REFERENCES recommendation(id);

COMMIT;

-- =============================================
-- 患者v2健康数据补充（20个典型患者）
-- 为肾功能不全、肝功能不全、妊娠、糖尿病等场景填充有意义的器官功能数据
-- 运行此脚本前需先运行 patient_data.sql 和 migration_v2.sql
--
-- IMPORTANT: patient_id 编号基于实际DB自增ID
-- =============================================

SET NAMES utf8mb4;
USE medical_recommendation;

-- =============================================
-- 肾功能不全患者（3人）- 选取高血压女性患者
-- =============================================

-- 尹艳: 77岁女性,高血压+骨质疏松 → 轻度肾功能不全
UPDATE patient_health_record SET
  renal_function = 'mild_impairment',
  hepatic_function = 'normal',
  smoking_status = 'never',
  drinking_status = 'none',
  blood_pressure_systolic = 145,
  blood_pressure_diastolic = 92,
  fasting_glucose = 5.2,
  hba1c = 5.1,
  cholesterol_total = 4.8,
  cholesterol_ldl = 2.9,
  heart_rate = 78
WHERE patient_id = 186 AND is_latest = TRUE;

-- 段霞: 77岁女性,高血压+骨质疏松+脑卒中后遗症 → 中度肾功能不全
UPDATE patient_health_record SET
  renal_function = 'moderate_impairment',
  hepatic_function = 'normal',
  smoking_status = 'former',
  drinking_status = 'occasional',
  blood_pressure_systolic = 160,
  blood_pressure_diastolic = 100,
  fasting_glucose = 6.1,
  hba1c = 5.8,
  cholesterol_total = 5.6,
  cholesterol_ldl = 3.4,
  heart_rate = 82
WHERE patient_id = 182 AND is_latest = TRUE;

-- 康霞: 63岁女性,高血压+骨质疏松 → 重度肾功能不全
UPDATE patient_health_record SET
  renal_function = 'severe_impairment',
  hepatic_function = 'normal',
  smoking_status = 'never',
  drinking_status = 'none',
  blood_pressure_systolic = 170,
  blood_pressure_diastolic = 105,
  fasting_glucose = 7.8,
  hba1c = 6.8,
  cholesterol_total = 6.2,
  cholesterol_ldl = 4.1,
  heart_rate = 88
WHERE patient_id = 170 AND is_latest = TRUE;

-- =============================================
-- 肝功能不全患者（2人）
-- =============================================

-- 陈明: 34岁男性,高血压 → 轻度肝功能不全
UPDATE patient_health_record SET
  renal_function = 'normal',
  hepatic_function = 'mild_impairment',
  smoking_status = 'current',
  drinking_status = 'regular',
  blood_pressure_systolic = 128,
  blood_pressure_diastolic = 82,
  fasting_glucose = 8.5,
  hba1c = 7.2,
  cholesterol_total = 5.4,
  cholesterol_ldl = 3.2,
  heart_rate = 72
WHERE patient_id = 5 AND is_latest = TRUE;

-- 尹艳: 77岁女性,高血压+骨质疏松 → 重度肝功能不全（同时有轻度肾不全）
-- 注意：尹艳已在肾功能段落被更新，此处改为同时有肾和肝功能不全
-- 使用MODERATE肾+SEVERE肝的组合（与原SQL患者182的设定一致）
UPDATE patient_health_record SET
  renal_function = 'moderate_impairment',
  hepatic_function = 'severe_impairment',
  smoking_status = 'former',
  drinking_status = 'none',
  blood_pressure_systolic = 165,
  blood_pressure_diastolic = 95,
  fasting_glucose = 9.2,
  hba1c = 8.0,
  cholesterol_total = 6.8,
  cholesterol_ldl = 4.5,
  heart_rate = 90
WHERE patient_id = 186 AND is_latest = TRUE;

-- =============================================
-- 妊娠相关女性患者（5人）- 更改慢性病JSON加入妊娠关键词
-- =============================================

-- 刘芳: 31岁女性,健康 → 妊娠期
UPDATE patient_health_record SET
  chronic_diseases = '["妊娠"]',
  renal_function = 'normal',
  hepatic_function = 'normal',
  smoking_status = 'never',
  drinking_status = 'none',
  blood_pressure_systolic = 118,
  blood_pressure_diastolic = 75,
  fasting_glucose = 4.6,
  hba1c = 4.8,
  cholesterol_total = 4.2,
  cholesterol_ldl = 2.5,
  heart_rate = 80
WHERE patient_id = 4 AND is_latest = TRUE;

-- 杨静: 32岁女性 → 妊娠期高血压
UPDATE patient_health_record SET
  chronic_diseases = '["妊娠期高血压", "妊娠"]',
  renal_function = 'normal',
  hepatic_function = 'normal',
  smoking_status = 'never',
  drinking_status = 'none',
  blood_pressure_systolic = 140,
  blood_pressure_diastolic = 90,
  fasting_glucose = 5.3,
  hba1c = 5.2,
  cholesterol_total = 4.8,
  cholesterol_ldl = 2.9,
  heart_rate = 85
WHERE patient_id = 6 AND is_latest = TRUE;

-- 黄丽: 30岁女性 → 妊娠糖尿病
UPDATE patient_health_record SET
  chronic_diseases = '["妊娠糖尿病", "妊娠"]',
  renal_function = 'normal',
  hepatic_function = 'normal',
  smoking_status = 'never',
  drinking_status = 'none',
  blood_pressure_systolic = 122,
  blood_pressure_diastolic = 78,
  fasting_glucose = 6.5,
  hba1c = 5.8,
  cholesterol_total = 4.5,
  cholesterol_ldl = 2.7,
  heart_rate = 82
WHERE patient_id = 8 AND is_latest = TRUE;

-- 朱红: 34岁女性 → 哮喘+妊娠
UPDATE patient_health_record SET
  chronic_diseases = '["哮喘", "妊娠"]',
  allergies = '["磺胺类"]',
  renal_function = 'normal',
  hepatic_function = 'normal',
  smoking_status = 'never',
  drinking_status = 'none',
  blood_pressure_systolic = 115,
  blood_pressure_diastolic = 72,
  fasting_glucose = 4.5,
  hba1c = 4.6,
  cholesterol_total = 4.0,
  cholesterol_ldl = 2.3,
  heart_rate = 78
WHERE patient_id = 14 AND is_latest = TRUE;

-- 何雪: 33岁女性 → 备孕期贫血
UPDATE patient_health_record SET
  chronic_diseases = '["贫血", "备孕"]',
  renal_function = 'normal',
  hepatic_function = 'normal',
  smoking_status = 'never',
  drinking_status = 'occasional',
  blood_pressure_systolic = 110,
  blood_pressure_diastolic = 68,
  fasting_glucose = 4.3,
  hba1c = 4.5,
  cholesterol_total = 3.8,
  cholesterol_ldl = 2.1,
  heart_rate = 72
WHERE patient_id = 18 AND is_latest = TRUE;

-- =============================================
-- 糖尿病患者（3人，无肾/肝功能不全）
-- =============================================

-- 郑宇: 33岁男性,2型糖尿病
UPDATE patient_health_record SET
  chronic_diseases = '["2型糖尿病"]',
  renal_function = 'normal',
  hepatic_function = 'normal',
  smoking_status = 'former',
  drinking_status = 'occasional',
  blood_pressure_systolic = 135,
  blood_pressure_diastolic = 85,
  fasting_glucose = 8.9,
  hba1c = 7.5,
  cholesterol_total = 5.6,
  cholesterol_ldl = 3.5,
  heart_rate = 75
WHERE patient_id = 21 AND is_latest = TRUE;

-- 秦涛: 63岁男性,高血压+2型糖尿病
UPDATE patient_health_record SET
  renal_function = 'normal',
  hepatic_function = 'normal',
  smoking_status = 'current',
  drinking_status = 'regular',
  blood_pressure_systolic = 150,
  blood_pressure_diastolic = 95,
  fasting_glucose = 9.5,
  hba1c = 8.2,
  cholesterol_total = 5.8,
  cholesterol_ldl = 3.8,
  heart_rate = 80
WHERE patient_id = 173 AND is_latest = TRUE;

-- 万伟: 75岁男性,高血压+冠心病+心力衰竭+2型糖尿病 → 多重慢性病
UPDATE patient_health_record SET
  renal_function = 'normal',
  hepatic_function = 'normal',
  smoking_status = 'former',
  drinking_status = 'occasional',
  blood_pressure_systolic = 155,
  blood_pressure_diastolic = 98,
  fasting_glucose = 10.2,
  hba1c = 8.8,
  cholesterol_total = 6.5,
  cholesterol_ldl = 4.2,
  heart_rate = 82
WHERE patient_id = 181 AND is_latest = TRUE;

-- =============================================
-- 正常健康档案（7人，所有v2字段填入正常值）
-- =============================================

-- 张伟: 33岁男性,体检正常
UPDATE patient_health_record SET
  renal_function = 'normal',
  hepatic_function = 'normal',
  smoking_status = 'never',
  drinking_status = 'occasional',
  blood_pressure_systolic = 120,
  blood_pressure_diastolic = 78,
  fasting_glucose = 4.8,
  hba1c = 4.9,
  cholesterol_total = 4.2,
  cholesterol_ldl = 2.5,
  heart_rate = 70
WHERE patient_id = 1 AND is_latest = TRUE;

-- 周杰: 38岁男性,2型糖尿病 → 改为正常体检
-- (注意：DB中周杰原为2型糖尿病，此处改chronic_diseases为体检正常)
UPDATE patient_health_record SET
  chronic_diseases = '[]',
  renal_function = 'normal',
  hepatic_function = 'normal',
  smoking_status = 'never',
  drinking_status = 'occasional',
  blood_pressure_systolic = 125,
  blood_pressure_diastolic = 80,
  fasting_glucose = 5.0,
  hba1c = 5.0,
  cholesterol_total = 4.4,
  cholesterol_ldl = 2.7,
  heart_rate = 72
WHERE patient_id = 9 AND is_latest = TRUE;

-- 徐涛: 35岁男性,高血压 → 改为健康
UPDATE patient_health_record SET
  chronic_diseases = '[]',
  renal_function = 'normal',
  hepatic_function = 'normal',
  smoking_status = 'never',
  drinking_status = 'none',
  blood_pressure_systolic = 118,
  blood_pressure_diastolic = 76,
  fasting_glucose = 4.6,
  hba1c = 4.7,
  cholesterol_total = 4.0,
  cholesterol_ldl = 2.3,
  heart_rate = 68
WHERE patient_id = 11 AND is_latest = TRUE;

-- 侯波: 65岁男性,高血压+冠心病（肾功能正常）
UPDATE patient_health_record SET
  renal_function = 'normal',
  hepatic_function = 'normal',
  smoking_status = 'current',
  drinking_status = 'regular',
  blood_pressure_systolic = 148,
  blood_pressure_diastolic = 92,
  fasting_glucose = 5.5,
  hba1c = 5.3,
  cholesterol_total = 5.2,
  cholesterol_ldl = 3.2,
  heart_rate = 78
WHERE patient_id = 177 AND is_latest = TRUE;

-- 黎涛: 73岁男性,高血压+脑卒中后遗症+糖尿病 → 多重慢性病（肾功能正常）
UPDATE patient_health_record SET
  renal_function = 'normal',
  hepatic_function = 'normal',
  smoking_status = 'former',
  drinking_status = 'occasional',
  blood_pressure_systolic = 155,
  blood_pressure_diastolic = 95,
  fasting_glucose = 7.5,
  hba1c = 6.5,
  cholesterol_total = 5.8,
  cholesterol_ldl = 3.6,
  heart_rate = 80
WHERE patient_id = 187 AND is_latest = TRUE;

-- 万伟: 75岁男性 → 老年人轻度肾功能偏低
-- (注意：万伟在糖尿病段落已设为normal renal，此处改为mild_impairment覆盖)
UPDATE patient_health_record SET
  renal_function = 'mild_impairment',
  hepatic_function = 'normal',
  smoking_status = 'former',
  drinking_status = 'none',
  blood_pressure_systolic = 160,
  blood_pressure_diastolic = 90,
  fasting_glucose = 7.2,
  hba1c = 6.3,
  cholesterol_total = 5.4,
  cholesterol_ldl = 3.3,
  heart_rate = 76
WHERE patient_id = 181 AND is_latest = TRUE;

-- 罗琳: 37岁女性,健康体检
UPDATE patient_health_record SET
  renal_function = 'normal',
  hepatic_function = 'normal',
  smoking_status = 'never',
  drinking_status = 'occasional',
  blood_pressure_systolic = 115,
  blood_pressure_diastolic = 72,
  fasting_glucose = 4.5,
  hba1c = 4.6,
  cholesterol_total = 3.9,
  cholesterol_ldl = 2.2,
  heart_rate = 68
WHERE patient_id = 20 AND is_latest = TRUE;
-- =============================================
-- 差分隐私保护的医疗用药推荐系统 - 标准数据初始化
-- disease表（约100条） + drug_category表（24条ATC一级分类）
-- =============================================

SET NAMES utf8mb4;
USE medical_recommendation;

-- =============================================
-- 一、drug_category 标准数据（24条 ATC一级分类）
-- =============================================

INSERT INTO drug_category (id, name, name_en, atc_level1, description) VALUES
(1,  '消化系统与代谢药', 'Alimentary tract and metabolism', 'A', '消化系统疾病用药、抗糖尿病药、维生素、矿物质补充剂'),
(2,  '血液与造血器官药', 'Blood and blood forming organs', 'B', '抗凝药、抗血小板药、造血刺激剂'),
(3,  '心血管系统药', 'Cardiovascular system', 'C', '降压药、降脂药、抗心律失常药、冠心病用药'),
(4,  '皮肤科用药', 'Dermatologicals', 'D', '外用抗感染药、皮质类固醇、痤疮治疗药'),
(5,  '生殖系统与性激素', 'Genito-urinary system and sex hormones', 'G', '避孕药、子宫收缩药、性激素'),
(6,  '全身性抗感染药', 'Systemic anti-infectives', 'J', '抗生素、抗病毒药、抗真菌药、抗寄生虫药'),
(7,  '抗肿瘤与免疫调节药', 'Antineoplastic and immunomodulating agents', 'L', '化疗药、靶向药、免疫调节剂'),
(8,  '肌肉骨骼系统药', 'Musculo-skeletal system', 'M', '抗炎药、抗痛风药、骨代谢调节药'),
(9,  '神经系统药', 'Nervous system', 'N', '镇痛药、抗癫痫药、抗帕金森药、抗抑郁药、抗精神病药'),
(10, '呼吸系统药', 'Respiratory system', 'R', '平喘药、镇咳药、抗过敏药'),
(11, '感觉器官药', 'Sensory organs', 'S', '眼科用药、耳科用药'),
(12, '各种制剂', 'Various', 'V', '造影剂、其他杂类');

-- 扩展分类（覆盖数据集中常见组合药和特殊类别）
INSERT INTO drug_category (id, name, name_en, atc_level1, description) VALUES
(13, '复方心血管药', 'Cardiovascular combinations', 'C', 'ACE+利尿、ARB+利尿、氨氯地平+缬沙坦等组合制剂'),
(14, '复方抗感染药', 'Anti-infective combinations', 'J', '阿莫西林+克拉维酸、氨苄西林+舒巴坦等'),
(15, '内分泌系统药', 'Endocrine system', 'H', '甲状腺药、皮质类固醇（全身）、胰岛素'),
(16, '泌尿系统药', 'Urologicals', 'G', '利尿药、膀胱松弛药'),
(17, '免疫抑制剂', 'Immunossuppressants', 'L', '环孢素、硫唑嘌呤、TNF抑制剂'),
(18, '镇痛与麻醉药', 'Analgesics and anesthetics', 'N', '阿片类镇痛药、非甾体抗炎药、局部麻醉药'),
(19, '精神科用药', 'Psycholeptics', 'N', '抗焦虑药、催眠药、抗精神病药'),
(20, '抗寄生虫药', 'Antiparasitic products', 'P', '驱虫药、抗疟药'),
(21, '血液替代物与灌注液', 'Blood substitutes and perfusion solutions', 'B', '血浆替代品'),
(22, '诊断用药', 'Diagnostic agents', 'V', '造影剂、诊断试剂'),
(23, '顺势疗法', 'Homeopathy', 'V', '顺势疗法制剂'),
(24, '中药及天然药', 'Herbal and natural products', 'V', '植物药、天然产物提取物');

-- =============================================
-- 二、disease 标准数据（约100条）
-- 涵盖：心血管、内分泌、呼吸、消化、肾脏、神经、
--       骨骼肌肉、皮肤免疫、血液、眼科、特殊生理状态、过敏类型
-- =============================================

-- 心血管系统疾病
INSERT INTO disease (name, name_en, type, category, icd10_code, severity_default, is_chronic) VALUES
('高血压', 'Hypertension', 'disease', '心血管', 'I10', 'moderate', TRUE),
('冠心病', 'Coronary artery disease', 'disease', '心血管', 'I25', 'severe', TRUE),
('心绞痛', 'Angina pectoris', 'disease', '心血管', 'I20', 'moderate', TRUE),
('心力衰竭', 'Heart failure', 'disease', '心血管', 'I50', 'severe', TRUE),
('心律失常', 'Arrhythmia', 'disease', '心血管', 'I49', 'moderate', TRUE),
('心房颤动', 'Atrial fibrillation', 'disease', '心血管', 'I48', 'severe', TRUE),
('深静脉血栓', 'Deep vein thrombosis', 'disease', '心血管', 'I82', 'severe', FALSE),
('肺栓塞', 'Pulmonary embolism', 'disease', '心血管', 'I26', 'critical', FALSE),
('外周动脉疾病', 'Peripheral arterial disease', 'disease', '心血管', 'I70', 'moderate', TRUE),
('高脂血症', 'Hyperlipidemia', 'disease', '心血管', 'E78', 'moderate', TRUE),
('心肌梗死', 'Myocardial infarction', 'disease', '心血管', 'I21', 'critical', FALSE);

-- 内分泌系统疾病
INSERT INTO disease (name, name_en, type, category, icd10_code, severity_default, is_chronic) VALUES
('2型糖尿病', 'Type 2 diabetes mellitus', 'disease', '内分泌', 'E11', 'moderate', TRUE),
('1型糖尿病', 'Type 1 diabetes mellitus', 'disease', '内分泌', 'E10', 'severe', TRUE),
('甲状腺功能亢进', 'Hyperthyroidism', 'disease', '内分泌', 'E05', 'moderate', FALSE),
('甲状腺功能减退', 'Hypothyroidism', 'disease', '内分泌', 'E03', 'mild', TRUE),
('痛风', 'Gout', 'disease', '内分泌', 'M10', 'moderate', TRUE),
('高尿酸血症', 'Hyperuricemia', 'disease', '内分泌', 'E79', 'mild', TRUE),
('骨质疏松', 'Osteoporosis', 'disease', '内分泌', 'M81', 'moderate', TRUE),
('代谢综合征', 'Metabolic syndrome', 'disease', '内分泌', 'E88', 'moderate', TRUE);

-- 呼吸系统疾病
INSERT INTO disease (name, name_en, type, category, icd10_code, severity_default, is_chronic) VALUES
('哮喘', 'Asthma', 'disease', '呼吸', 'J45', 'moderate', TRUE),
('慢性阻塞性肺疾病', 'Chronic obstructive pulmonary disease', 'disease', '呼吸', 'J44', 'severe', TRUE),
('肺炎', 'Pneumonia', 'disease', '呼吸', 'J18', 'severe', FALSE),
('支气管炎', 'Bronchitis', 'disease', '呼吸', 'J40', 'moderate', FALSE),
('肺结核', 'Tuberculosis', 'disease', '呼吸', 'A15', 'severe', TRUE),
('过敏性鼻炎', 'Allergic rhinitis', 'disease', '呼吸', 'J30', 'mild', TRUE),
('慢性咳嗽', 'Chronic cough', 'symptom', '呼吸', 'R05', 'mild', FALSE);

-- 消化系统疾病
INSERT INTO disease (name, name_en, type, category, icd10_code, severity_default, is_chronic) VALUES
('胃溃疡', 'Peptic ulcer disease', 'disease', '消化', 'K25', 'moderate', TRUE),
('胃食管反流病', 'Gastroesophageal reflux disease', 'disease', '消化', 'K21', 'mild', TRUE),
('肠易激综合征', 'Irritable bowel syndrome', 'disease', '消化', 'K58', 'mild', TRUE),
('克罗恩病', 'Crohn disease', 'disease', '消化', 'K50', 'severe', TRUE),
('溃疡性结肠炎', 'Ulcerative colitis', 'disease', '消化', 'K51', 'moderate', TRUE),
('肝硬化', 'Liver cirrhosis', 'disease', '消化', 'K74', 'severe', TRUE),
('慢性肝炎', 'Chronic hepatitis', 'disease', '消化', 'K73', 'moderate', TRUE),
('恶心呕吐', 'Nausea and vomiting', 'symptom', '消化', 'R11', 'mild', FALSE),
('腹泻', 'Diarrhea', 'symptom', '消化', 'R19', 'mild', FALSE),
('便秘', 'Constipation', 'symptom', '消化', 'K59', 'mild', FALSE);

-- 肾脏与泌尿系统疾病
INSERT INTO disease (name, name_en, type, category, icd10_code, severity_default, is_chronic) VALUES
('慢性肾病', 'Chronic kidney disease', 'disease', '肾脏', 'N18', 'severe', TRUE),
('急性肾损伤', 'Acute kidney injury', 'disease', '肾脏', 'N17', 'critical', FALSE),
('肾功能不全', 'Renal insufficiency', 'disease', '肾脏', 'N19', 'severe', TRUE),
('尿路感染', 'Urinary tract infection', 'disease', '肾脏', 'N30', 'moderate', FALSE),
('肾结石', 'Kidney stone', 'disease', '肾脏', 'N20', 'moderate', FALSE);

-- 神经系统疾病
INSERT INTO disease (name, name_en, type, category, icd10_code, severity_default, is_chronic) VALUES
('癫痫', 'Epilepsy', 'disease', '神经', 'G40', 'severe', TRUE),
('帕金森病', 'Parkinson disease', 'disease', '神经', 'G20', 'severe', TRUE),
('偏头痛', 'Migraine', 'disease', '神经', 'G43', 'moderate', TRUE),
('多发性硬化', 'Multiple sclerosis', 'disease', '神经', 'G35', 'severe', TRUE),
('阿尔茨海默病', 'Alzheimer disease', 'disease', '神经', 'G30', 'severe', TRUE),
('失眠', 'Insomnia', 'symptom', '神经', 'G47', 'mild', TRUE),
('焦虑症', 'Anxiety disorder', 'disease', '神经', 'F41', 'moderate', TRUE),
('抑郁症', 'Major depressive disorder', 'disease', '神经', 'F32', 'severe', TRUE),
('双相障碍', 'Bipolar disorder', 'disease', '神经', 'F31', 'severe', TRUE),
('精神分裂症', 'Schizophrenia', 'disease', '神经', 'F20', 'severe', TRUE),
('注意缺陷多动障碍', 'Attention deficit hyperactivity disorder', 'disease', '神经', 'F90', 'moderate', TRUE),
('神经病理性疼痛', 'Neuropathic pain', 'symptom', '神经', 'G63', 'moderate', TRUE);

-- 骨骼肌肉系统疾病
INSERT INTO disease (name, name_en, type, category, icd10_code, severity_default, is_chronic) VALUES
('类风湿关节炎', 'Rheumatoid arthritis', 'disease', '骨骼肌肉', 'M05', 'severe', TRUE),
('骨关节炎', 'Osteoarthritis', 'disease', '骨骼肌肉', 'M19', 'moderate', TRUE),
('强直性脊柱炎', 'Ankylosing spondylitis', 'disease', '骨骼肌肉', 'M45', 'severe', TRUE),
('肌肉痉挛', 'Muscle spasm', 'symptom', '骨骼肌肉', 'R25', 'mild', FALSE),
('纤维肌痛', 'Fibromyalgia', 'disease', '骨骼肌肉', 'M79', 'moderate', TRUE);

-- 皮肤免疫系统疾病
INSERT INTO disease (name, name_en, type, category, icd10_code, severity_default, is_chronic) VALUES
('银屑病', 'Psoriasis', 'disease', '皮肤免疫', 'L40', 'moderate', TRUE),
('湿疹', 'Eczema', 'disease', '皮肤免疫', 'L30', 'mild', TRUE),
('痤疮', 'Acne vulgaris', 'disease', '皮肤免疫', 'L70', 'mild', TRUE),
('系统性红斑狼疮', 'Systemic lupus erythematosus', 'disease', '皮肤免疫', 'M32', 'severe', TRUE),
('皮肤真菌感染', 'Dermatophytosis', 'disease', '皮肤免疫', 'B35', 'mild', FALSE),
('过敏性皮炎', 'Allergic dermatitis', 'disease', '皮肤免疫', 'L23', 'mild', FALSE);

-- 血液系统疾病
INSERT INTO disease (name, name_en, type, category, icd10_code, severity_default, is_chronic) VALUES
('缺铁性贫血', 'Iron deficiency anemia', 'disease', '血液', 'D50', 'moderate', TRUE),
('血友病', 'Hemophilia', 'disease', '血液', 'D66', 'severe', TRUE),
('深静脉血栓形成', 'Deep vein thrombosis', 'disease', '血液', 'I82', 'severe', FALSE);

-- 眼科疾病
INSERT INTO disease (name, name_en, type, category, icd10_code, severity_default, is_chronic) VALUES
('青光眼', 'Glaucoma', 'disease', '眼科', 'H40', 'severe', TRUE),
('干眼症', 'Dry eye syndrome', 'disease', '眼科', 'H04', 'mild', TRUE),
('过敏性结膜炎', 'Allergic conjunctivitis', 'disease', '眼科', 'H10', 'mild', FALSE),
('黄斑变性', 'Macular degeneration', 'disease', '眼科', 'H35', 'severe', TRUE);

-- 肿瘤疾病
INSERT INTO disease (name, name_en, type, category, icd10_code, severity_default, is_chronic) VALUES
('乳腺癌', 'Breast cancer', 'disease', '肿瘤', 'C50', 'critical', FALSE),
('肺癌', 'Lung cancer', 'disease', '肿瘤', 'C34', 'critical', FALSE),
('结肠癌', 'Colorectal cancer', 'disease', '肿瘤', 'C18', 'critical', FALSE),
('前列腺癌', 'Prostate cancer', 'disease', '肿瘤', 'C61', 'critical', FALSE),
('淋巴瘤', 'Lymphoma', 'disease', '肿瘤', 'C85', 'critical', FALSE);

-- 传染病
INSERT INTO disease (name, name_en, type, category, icd10_code, severity_default, is_chronic) VALUES
('流感', 'Influenza', 'disease', '传染', 'J11', 'moderate', FALSE),
('单纯疱疹', 'Herpes simplex', 'disease', '传染', 'B00', 'mild', TRUE),
('带状疱疹', 'Herpes zoster', 'disease', '传染', 'B02', 'moderate', FALSE),
('HIV感染', 'HIV infection', 'disease', '传染', 'B20', 'severe', TRUE),
('丙型肝炎', 'Hepatitis C', 'disease', '传染', 'B18', 'severe', TRUE),
('细菌性感染', 'Bacterial infection', 'disease', '传染', 'A49', 'moderate', FALSE),
('真菌感染', 'Fungal infection', 'disease', '传染', 'B49', 'moderate', FALSE),
('寄生虫感染', 'Parasitic infection', 'disease', '传染', 'B89', 'moderate', FALSE);

-- 特殊生理状态（用药禁忌的关键条件）
INSERT INTO disease (name, name_en, type, category, icd10_code, severity_default, is_chronic) VALUES
('妊娠期', 'Pregnancy', 'physiological_condition', '特殊生理', 'Z34', 'moderate', FALSE),
('哺乳期', 'Breastfeeding', 'physiological_condition', '特殊生理', 'Z39', 'moderate', FALSE),
('新生儿', 'Neonate', 'physiological_condition', '特殊生理', 'Z38', 'severe', FALSE),
('儿童', 'Pediatric', 'physiological_condition', '特殊生理', 'Z02', 'moderate', FALSE),
('老年人', 'Geriatric', 'physiological_condition', '特殊生理', 'Z78', 'moderate', TRUE);

-- 过敏类型（药物禁忌匹配的关键）
INSERT INTO disease (name, name_en, type, category, icd10_code, severity_default, is_chronic) VALUES
('青霉素过敏', 'Penicillin allergy', 'allergy_type', '过敏', 'Z88', 'severe', TRUE),
('磺胺类过敏', 'Sulfonamide allergy', 'allergy_type', '过敏', 'Z88', 'severe', TRUE),
('头孢类过敏', 'Cephalosporin allergy', 'allergy_type', '过敏', 'Z88', 'severe', TRUE),
('非甾体抗炎药过敏', 'NSAID allergy', 'allergy_type', '过敏', 'Z88', 'severe', TRUE),
('阿司匹林过敏', 'Aspirin allergy', 'allergy_type', '过敏', 'Z88', 'severe', TRUE),
('喹诺酮类过敏', 'Fluoroquinolone allergy', 'allergy_type', '过敏', 'Z88', 'moderate', TRUE),
('造影剂过敏', 'Contrast media allergy', 'allergy_type', '过敏', 'Z88', 'severe', TRUE),
('花生过敏', 'Peanut allergy', 'allergy_type', '过敏', 'Z91', 'severe', TRUE),
('乳糖不耐受', 'Lactose intolerance', 'allergy_type', '过敏', 'Z91', 'mild', TRUE),
('药物过敏（未指定）', 'Drug allergy unspecified', 'allergy_type', '过敏', 'Z88', 'severe', TRUE);

-- 器官功能障碍（禁忌匹配的关键条件）
INSERT INTO disease (name, name_en, type, category, icd10_code, severity_default, is_chronic) VALUES
('严重肝功能不全', 'Severe hepatic impairment', 'physiological_condition', '器官功能', 'K74', 'critical', TRUE),
('严重肾功能不全', 'Severe renal impairment', 'physiological_condition', '器官功能', 'N19', 'critical', TRUE),
('QT间期延长', 'QT prolongation', 'physiological_condition', '器官功能', 'R00', 'severe', TRUE),
('粒细胞缺乏症', 'Agranulocytosis', 'disease', '血液', 'D70', 'critical', FALSE),
('重症肌无力', 'Myasthenia gravis', 'disease', '神经', 'G70', 'severe', TRUE),
('卟啉病', 'Porphyria', 'disease', '血液', 'E80', 'severe', TRUE);

-- 疾病别名映射
INSERT INTO disease_alias (disease_id, alias_name, source) VALUES
-- 2型糖尿病别名
((SELECT id FROM disease WHERE name_en='Type 2 diabetes mellitus'), 'T2DM', 'common'),
((SELECT id FROM disease WHERE name_en='Type 2 diabetes mellitus'), '糖尿病', 'common'),
((SELECT id FROM disease WHERE name_en='Type 2 diabetes mellitus'), 'Diabetes', 'common'),
((SELECT id FROM disease WHERE name_en='Type 2 diabetes mellitus'), 'NIDDM', 'clinical'),
-- 高血压别名
((SELECT id FROM disease WHERE name_en='Hypertension'), 'HTN', 'common'),
((SELECT id FROM disease WHERE name_en='Hypertension'), '高压', 'common'),
-- COPD别名
((SELECT id FROM disease WHERE name_en='Chronic obstructive pulmonary disease'), 'COPD', 'common'),
-- GERD别名
((SELECT id FROM disease WHERE name_en='Gastroesophageal reflux disease'), 'GERD', 'common'),
((SELECT id FROM disease WHERE name_en='Gastroesophageal reflux disease'), '反流性食管炎', 'common'),
-- CHF别名
((SELECT id FROM disease WHERE name_en='Heart failure'), 'CHF', 'common'),
((SELECT id FROM disease WHERE name_en='Heart failure'), '充血性心力衰竭', 'common'),
-- AF别名
((SELECT id FROM disease WHERE name_en='Atrial fibrillation'), 'AF', 'common'),
((SELECT id FROM disease WHERE name_en='Atrial fibrillation'), '房颤', 'common'),
-- CKD别名
((SELECT id FROM disease WHERE name_en='Chronic kidney disease'), 'CKD', 'common'),
-- DVT别名
((SELECT id FROM disease WHERE name_en='Deep vein thrombosis'), 'DVT', 'common'),
-- MS别名
((SELECT id FROM disease WHERE name_en='Multiple sclerosis'), 'MS', 'common'),
-- SLE别名
((SELECT id FROM disease WHERE name_en='Systemic lupus erythematosus'), 'SLE', 'common'),
-- RA别名
((SELECT id FROM disease WHERE name_en='Rheumatoid arthritis'), 'RA', 'common'),
-- ADHD别名
((SELECT id FROM disease WHERE name_en='Attention deficit hyperactivity disorder'), 'ADHD', 'common');
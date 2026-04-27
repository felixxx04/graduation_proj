"""英→中翻译映射模块

解决推荐结果中英文字段直接展示给用户的问题。
映射覆盖:
1. safetyType 枚举 (safe → 安全)
2. qualityWarning 枚举 (NO_RELIABLE_RECOMMENDATION → 无可信推荐)
3. drug_class_en (Antiviral → 抗病毒药) — 493类
4. matchedDisease (herpes simplex virus infection → 单纯疱疹病毒感染) — 1420种
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

from app.config import settings

logger = logging.getLogger(__name__)

# ── 枚举映射: 安全类型和质量警告 ──

SAFETY_TYPE_ZH: Dict[str, str] = {
    "safe": "安全",
    "relative_contraindication": "相对禁忌",
    "moderate_interaction": "中度交互",
    "severe_interaction": "严重交互",
    "absolute_contraindication": "绝对禁忌",
}

QUALITY_WARNING_ZH: Dict[str, str] = {
    "NO_RELIABLE_RECOMMENDATION": "无可信推荐",
    "LOW_CONFIDENCE": "置信度低",
}

# ── 关键药物类别映射 (高频、常见类别) ──
# 493个类别中, 手动映射最常见的前100个
# 其余类别由缓存文件补充 (data/translations/drug_class_translations.json)

DRUG_CLASS_ZH_CORE: Dict[str, str] = {
    # 抗感染
    "Antiviral": "抗病毒药",
    "Antibiotic": "抗生素",
    "Antibacterial": "抗菌药",
    "Antifungal": "抗真菌药",
    "Antimalarial": "抗疟药",
    "Antiprotozoal": "抗原虫药",
    "Anthelmintic": "驱虫药",
    "Antimycobacterial": "抗分枝杆菌药",
    "Amebicides": "抗阿米巴药",
    "Scabicidal / Pediculicidal": "杀螨杀虱药",

    # 抗感染细类
    "Fluoroquinolone Antibiotic": "氟喹诺酮类抗生素",
    "Macrolide Antibiotic": "大环内酯类抗生素",
    "Penicillin Antibiotic": "青霉素类抗生素",
    "Cephalosporin Antibiotic": "头孢菌素类抗生素",
    "Aminoglycoside Antibiotic": "氨基糖苷类抗生素",
    "Tetracycline Antibiotic": "四环素类抗生素",
    "Glycopeptide Antibiotic": "糖肽类抗生素",
    "Lincosamide Antibiotic": "林可酰胺类抗生素",
    "Carbapenem Antibiotic": "碳青霉烯类抗生素",
    "Sulfonamide Antibiotic": "磺胺类抗生素",
    "Oxazolidinone Antibiotic": "恶唑烷酮类抗生素",
    "Ketolide Antibiotic": "酮内酯类抗生素",
    "Glycylcycline Antibiotic": "甘氨环素类抗生素",
    "Lipopeptide Antibiotic": "脂肽类抗生素",
    "Lipoglycopeptide Antibiotic": "脂糖肽类抗生素",
    "Polypeptide Antibiotic": "多肽类抗生素",
    "Anthracenedione Antibiotic": "蒽二酮类抗生素",
    "Anthracycline Antibiotic": "蒽环类抗生素",
    "Antibiotic Combination": "抗生素组合",
    "Antiviral combinations": "抗病毒组合药",
    "Antiviral boosters": "抗病毒增强剂",
    "Antiviral / Antiparkinsonian": "抗病毒/抗帕金森药",
    "Antifungal / Antiseborrheic": "抗真菌/抗脂溢药",
    "Antimalarial / Antiprotozoal": "抗疟/抗原虫药",
    "Antimalarial / DMARD": "抗疟/抗风湿药",

    # 细菌类细分
    "Aminoglycosides": "氨基糖苷类",
    "Aminopenicillins": "氨苄青霉素类",
    "Carbapenems": "碳青霉烯类",
    "Cephalosporins / beta-lactamase inhibitors": "头孢/β-内酰胺酶抑制剂",
    "First generation cephalosporins": "第一代头孢菌素",
    "Second generation cephalosporins": "第二代头孢菌素",
    "Third generation cephalosporins": "第三代头孢菌素",
    "Fourth generation cephalosporins": "第四代头孢菌素",
    "Other cephalosporins": "其他头孢菌素",
    "Macrolides": "大环内酯类",
    "Natural penicillins": "天然青霉素类",
    "Penicillin Antibiotic + Beta-Lactamase Inhibitor": "青霉素+β-内酰胺酶抑制剂",
    "Penicillinase resistant penicillins": "耐青霉素酶青霉素类",
    "Antipseudomonal penicillins": "抗假单胞菌青霉素类",
    "Beta-lactamase inhibitors": "β-内酰胺酶抑制剂",
    "Carbapenems / beta-lactamase inhibitors": "碳青霉烯/β-内酰胺酶抑制剂",
    "Fluoroquinolone Antibiotic": "氟喹诺酮类",
    "Quinolones": "喹诺酮类",
    "Sulfonamides": "磺胺类",
    "Tetracyclines": "四环素类",
    "Lincomycin derivatives": "林可霉素衍生物",
    "Azole Antifungal": "唑类抗真菌药",
    "Echinocandin Antifungal": "棘白菌素类抗真菌药",
    "Nitroimidazole Antibiotic": "硝基咪唑类抗生素",

    # 心血管
    "ACE Inhibitor": "ACE抑制剂",
    "ARB": "ARB(血管紧张素受体阻断剂)",
    "ARNI": "ARNI(血管紧张素受体脑啡肽酶抑制剂)",
    "Beta-Blocker": "β受体阻断剂",
    "Calcium channel blocking agents": "钙通道阻滞剂",
    "Dihydropyridine CCB": "二氢吡啶类钙通道阻滞剂",
    "Non-Dihydropyridine CCB": "非二氢吡啶类钙通道阻滞剂",
    "Statin": "他汀类",
    "Statins": "他汀类",
    "Fibrate": "贝特类",
    "Fibric acid derivatives": "贝特类衍生物",
    "Anticoagulant": "抗凝药",
    "Anticoagulant (Vitamin K Antagonist)": "抗凝药(维生素K拮抗剂)",
    "Direct Oral Anticoocagulant (Factor Xa Inhibitor)": "直接口服抗凝药(Xa因子抑制剂)",
    "Direct Thrombin Inhibitor": "直接凝血酶抑制剂",
    "Antiplatelet": "抗血小板药",
    "P2Y12 Inhibitor": "P2Y12抑制剂",
    "Platelet aggregation inhibitors": "血小板聚集抑制剂",
    "Glycoprotein IIb/IIIa Inhibitor": "糖蛋白IIb/IIIa抑制剂",
    "Thrombolytic": "溶栓药",
    "Thrombolytics": "溶栓药",
    "Thrombin inhibitors": "凝血酶抑制剂",
    "Nitrate": "硝酸酯类",
    "Cardiac Glycoside": "强心苷",
    "Loop Diuretic": "袢利尿剂",
    "Thiazide Diuretic": "噻嗪类利尿剂",
    "Thiazide-like Diuretic": "噻嗪样利尿剂",
    "Potassium-Sparing Diuretic": "保钾利尿剂",
    "Aldosterone Antagonist": "醛固酮拮抗剂",
    "Antianginal agents": "抗心绞痛药",
    "Vasodilator": "血管扩张剂",
    "Vasodilators": "血管扩张剂",
    "Agents for pulmonary hypertension": "肺动脉高压用药",
    "Antiarrhythmic (Class Ia)": "抗心律失常药(Ia类)",
    "Antiarrhythmic (Class Ic)": "抗心律失常药(Ic类)",
    "Antiarrhythmic (Class III)": "抗心律失常药(III类)",
    "Group I antiarrhythmics": "I类抗心律失常药",
    "Group II antiarrhythmics": "II类抗心律失常药",
    "Group IV antiarrhythmics": "IV类抗心律失常药",
    "Heparins": "肝素类",
    "Low Molecular Weight Heparin": "低分子量肝素",
    "ACE inhibitors with calcium channel blocking agents": "ACE抑制剂+钙通道阻滞剂",
    "ACE inhibitors with thiazides": "ACE抑制剂+噻嗪类",
    "ACE Inhibitor + Thiazide Diuretic": "ACE抑制剂+噻嗪利尿剂",
    "Angiotensin Converting Enzyme Inhibitors": "血管紧张素转换酶抑制剂",
    "Angiotensin receptor blockers": "血管紧张素受体阻断剂",
    "Angiotensin II inhibitors with calcium channel blockers": "ARB+钙通道阻滞剂",
    "Angiotensin II inhibitors with thiazides": "ARB+噻嗪类",
    "Beta blockers with thiazides": "β受体阻断剂+噻嗪类",
    "Beta-Blocker + Thiazide Diuretic": "β受体阻断剂+噻嗪利尿剂",
    "CCB + ACE Inhibitor": "钙通道阻滞剂+ACE抑制剂",
    "CCB + ARB": "钙通道阻滞剂+ARB",
    "Potassium sparing diuretics with thiazides": "保钾利尿剂+噻嗪类",
    "Potassium-Sparing Diuretic + Thiazide Diuretic": "保钾利尿剂+噻嗪利尿剂",
    "Renin inhibitors": "肾素抑制剂",
    "Antihyperlipidemic combinations": "降脂组合药",
    "Cholesterol Absorption Inhibitor": "胆固醇吸收抑制剂",
    "PCSK9 inhibitors": "PCSK9抑制剂",
    "Bile Acid Sequestrant": "胆酸螯合剂",
    "Antihyperuricemic agents": "降尿酸药",

    # 神经/精神
    "SSRI": "SSRI(选择性5-羟色胺再摄取抑制剂)",
    "SNRI": "SNRI(5-羟色胺去甲肾上腺素再摄取抑制剂)",
    "MAOI": "MAOI(单胺氧化酶抑制剂)",
    "Atypical Antipsychotic": "非典型抗精神病药",
    "Atypical antipsychotics": "非典型抗精神病药",
    "Typical Antipsychotic": "典型抗精神病药",
    "Antipsychotic": "抗精神病药",
    "Antidepressant": "抗抑郁药",
    "Tricyclic Antidepressant": "三环类抗抑郁药",
    "Tricyclic antidepressants": "三环类抗抑郁药",
    "Atypical Antidepressant": "非典型抗抑郁药",
    "Multimodal Antidepressant": "多模式抗抑郁药",
    "Tetracyclic Antidepressant": "四环类抗抑郁药",
    "Benzodiazepine": "苯二氮卓类",
    "Benzodiazepines": "苯二氮卓类",
    "Anxiolytic": "抗焦虑药",
    "Anticonvulsant": "抗惊厥药",
    "Antimanic": "抗躁狂药",
    "CNS Stimulant": "中枢兴奋药",
    "CNS stimulants": "中枢兴奋药",
    "CNS Depressant": "中枢抑制药",
    "Barbiturate": "巴比妥类",
    "Barbiturates": "巴比妥类",
    "Non-Benzodiazepine Hypnotic": "非苯二氮卓类催眠药",
    "Opioid Agonist": "阿片激动剂",
    "Opioids (narcotic analgesics)": "阿片类(麻醉镇痛药)",
    "Opioid Antagonist": "阿片拮抗剂",
    "Opioid Partial Agonist": "阿片部分激动剂",
    "Opioid Agonist-Antagonist": "阿片激动-拮抗剂",
    "Dopamine Agonist": "多巴胺激动剂",
    "Dopamine Antagonist": "多巴胺拮抗剂",
    "Dopamine Precursor": "多巴胺前体",
    "Cholinesterase Inhibitor": "胆碱酯酶抑制剂",
    "Anticholinergic": "抗胆碱药",
    "Antiparkinsonian": "抗帕金森药",
    "Dopaminergic antiparkinsonism agents": "多巴胺类抗帕金森药",
    "Anticholinergic antiparkinson agents": "抗胆碱类抗帕金森药",
    "Antimigraine agents": "抗偏头痛药",
    "CGRP inhibitors": "CGRP抑制剂",
    "Antihistamine": "抗组胺药",
    "Antihistamines": "抗组胺药",

    # 内分泌
    "Insulin": "胰岛素",
    "Insulin (Long-Acting)": "长效胰岛素",
    "Insulin (Rapid-Acting)": "速效胰岛素",
    "GLP-1 Receptor Agonist": "GLP-1受体激动剂",
    "Incretin mimetics": "肠促胰岛素模拟物",
    "DPP-4 Inhibitor": "DPP-4抑制剂",
    "Dipeptidyl peptidase 4 inhibitors": "二肽基肽酶4抑制剂",
    "SGLT-2 inhibitors": "SGLT-2抑制剂",
    "SGLT2 Inhibitor": "SGLT2抑制剂",
    "Sulfonylurea": "磺酰脲类",
    "Sulfonylureas": "磺酰脲类",
    "Biguanide": "双胍类",
    "Thiazolidinedione": "噻唑烷二酮类",
    "Thiazolidinediones": "噻唑烷二酮类",
    "Meglitinide": "格列奈类",
    "Meglitinides": "格列奈类",
    "Alpha-Glucosidase Inhibitor": "α-葡萄糖苷酶抑制剂",
    "Alpha-glucosidase inhibitors": "α-葡萄糖苷酶抑制剂",
    "Amylin analogs": "胰淀素类似物",
    "Thyroid Hormone": "甲状腺激素",
    "Thyroid drugs": "甲状腺药物",
    "Antithyroid Agent": "抗甲状腺药",
    "Estrogen": "雌激素",
    "Estrogens": "雌激素类",
    "Progestin": "孕激素",
    "Progestin + Estrogen": "孕激素+雌激素",
    "Contraceptives": "避孕药",
    "Corticosteroid": "皮质类固醇",
    "Glucocorticoids": "糖皮质激素",
    "Androgen": "雄激素",
    "Antiandrogen": "抗雄激素药",
    "Androgen Receptor Inhibitor": "雄激素受体抑制剂",
    "Estrogen Receptor Antagonist": "雌激素受体拮抗剂",

    # 呼吸
    "Adrenergic bronchodilators": "肾上腺素能支气管扩张剂",
    "Beta-2 Agonist": "β2受体激动剂",
    "LABA": "长效β2受体激动剂",
    "SABA": "短效β2受体激动剂",
    "Anticholinergic bronchodilators": "抗胆碱支气管扩张剂",
    "Inhaled Corticosteroid": "吸入性皮质类固醇",
    "Inhaled corticosteroids": "吸入性皮质类固醇",
    "Inhaled anti-infectives": "吸入性抗感染药",
    "Leukotriene Receptor Antagonist": "白三烯受体拮抗剂",
    "Mast Cell Stabilizer": "肥大细胞稳定剂",
    "Mast cell stabilizers": "肥大细胞稳定剂",
    "Mucolytic": "黏液溶解药",
    "Expectorants": "祛痰药",
    "Antitussive": "镇咳药",
    "Antitussives": "镇咳药",
    "Xanthine Derivative": "黄嘌呤衍生物",

    # 消化
    "Proton Pump Inhibitor": "质子泵抑制剂",
    "Proton pump inhibitors": "质子泵抑制剂",
    "H2 Blocker": "H2受体阻断剂",
    "H2 antagonists": "H2受体拮抗剂",
    "Antacid": "抗酸药",
    "Antacids": "抗酸药",
    "Laxatives": "泻药",
    "Bulk-Forming Laxative": "容积性泻药",
    "Stool Softener": "大便软化剂",
    "Antidiarrheal": "止泻药",
    "Antidiarrheals": "止泻药",
    "GI Protectant": "胃肠保护剂",
    "GI stimulants": "胃肠刺激药",
    "Miscellaneous GI agents": "其他胃肠药",
    "Antiemetic": "止吐药",
    "Miscellaneous antiemetics": "其他止吐药",
    "Anticholinergic antiemetics": "抗胆碱类止吐药",

    # 皮肤
    "Topical Corticosteroid": "外用皮质类固醇",
    "Topical acne agents": "外用痤疮药",
    "Topical Antiacne": "外用抗痤疮药",
    "Topical antipsoriatics": "外用抗银屑病药",
    "Topical anti-rosacea agents": "外用抗玫瑰痤疮药",
    "Topical antibiotics": "外用抗生素",
    "Topical antihistamines": "外用抗组胺药",
    "Topical antivirals": "外用抗病毒药",
    "Topical anesthetics": "外用麻醉药",
    "Topical emollients": "外用润肤剂",
    "Topical keratolytics": "外用角质溶解剂",
    "Keratolytic": "角质溶解剂",
    "Topical steroids": "外用类固醇",
    "Topical steroids with anti-infectives": "外用类固醇+抗感染药",
    "Topical non-steroidal anti-inflammatories": "外用非甾体抗炎药",
    "Topical rubefacient": "外用发红剂",
    "Vaginal anti-infectives": "阴道抗感染药",
    "Anorectal preparations": "肛肠制剂",
    "Retinoid": "维A酸类",
    "Psoralen": "补骨脂素",
    "Psoralens": "补骨脂素类",

    # 免疫/抗风湿
    "TNF Blocker": "TNF阻断剂",
    "TNF alfa inhibitors": "TNFα抑制剂",
    "DMARD": "抗风湿药(DMARD)",
    "Antirheumatics": "抗风湿药",
    "Immunosuppressant": "免疫抑制剂",
    "Selective immunosuppressants": "选择性免疫抑制剂",
    "Other immunosuppressants": "其他免疫抑制剂",
    "Calcineurin Inhibitor": "钙调神经磷酸酶抑制剂",
    "Calcineurin inhibitors": "钙调神经磷酸酶抑制剂",
    "JAK Inhibitor": "JAK抑制剂",
    "Interleukin inhibitors": "白介素抑制剂",
    "IL-6 Receptor Antagonist": "IL-6受体拮抗剂",
    "Monoclonal Antibody": "单克隆抗体",
    "CD20 monoclonal antibodies": "CD20单克隆抗体",
    "CD52 monoclonal antibodies": "CD52单克隆抗体",
    "Immunomodulator": "免疫调节剂",
    "Immunomodulatory Agent": "免疫调节剂",

    # 抗肿瘤
    "Alkylating Agent": "烷化剂",
    "Alkylating agents": "烷化剂",
    "Antimetabolite": "抗代谢药",
    "Antimetabolites": "抗代谢药",
    "Antimicrotubule Agent": "抗微管药",
    "Mitotic inhibitors": "有丝分裂抑制剂",
    "Antitumor Antibiotic": "抗肿瘤抗生素",
    "Topoisomerase Inhibitor": "拓扑异构酶抑制剂",
    "Proteasome Inhibitor": "蛋白酶体抑制剂",
    "Kinase Inhibitor": "激酶抑制剂",
    "Aromatase Inhibitor": "芳香酶抑制剂",
    "CDK4/6 Inhibitor": "CDK4/6抑制剂",
    "BTK Inhibitor": "BTK抑制剂",
    "PD-1 Inhibitor": "PD-1抑制剂",
    "Vinca Alkaloid": "长春花碱类",
    "Fusion Inhibitor": "融合抑制剂",

    # 骨/关节
    "Bisphosphonate": "双膦酸盐类",
    "Bisphosphonates": "双膦酸盐类",
    "RANK Ligand Inhibitor": "RANK配体抑制剂",
    "Calcitonin": "降钙素",
    "Calcium Regulator": "钙调节剂",
    "Uricosuric": "促尿酸排泄药",
    "Urate Oxidase Enzyme": "尿酸氧化酶",
    "Antigout": "抗痛风药",
    "Antigout agents": "抗痛风药",

    # 生殖/泌尿
    "Impotence agents": "勃起功能障碍药",
    "Urinary anti-infectives": "泌尿抗感染药",
    "Urinary antispasmodics": "泌尿解痉药",
    "Urinary Analgesic": "泌尿镇痛药",
    "Urinary pH modifiers": "尿液pH调节剂",
    "Uterotonic agents": "子宫收缩药",
    "GnRH Agonist": "GnRH激动剂",
    "Gonadotropins": "促性腺激素",
    "Prolactin inhibitors": "催乳素抑制剂",
    "Posterior Pituitary Hormone": "垂体后叶激素",
    "Vasopressin Analog": "加压素类似物",
    "Osmotic Diuretic": "渗透性利尿剂",

    # 血液
    "Antifibrinolytic": "抗纤溶药",
    "Iron Supplement": "铁补充剂",
    "Iron Chelator": "铁螯合剂",
    "Heavy Metal Chelator": "重金属螯合剂",
    "Erythropoiesis-Stimulating Agent": "促红细胞生成药",
    "Vitamin": "维生素",
    "Vitamins": "维生素类",
    "Vitamin D": "维生素D",
    "Vitamin D Analog": "维生素D类似物",
    "Vitamin D Supplement": "维生素D补充剂",
    "Vitamin B3": "维生素B3",
    "Vitamin and mineral combinations": "维生素矿物质组合",
    "Carnitine Supplement": "肉碱补充剂",
    "Electrolyte": "电解质",
    "Minerals and electrolytes": "矿物质和电解质",
    "Phosphate Binder": "磷结合剂",
    "Phosphate binders": "磷结合剂",

    # 其他
    "NSAID": "非甾体抗炎药",
    "NSAID / Antiplatelet": "非甾体抗炎药/抗血小板",
    "Nonsteroidal anti-inflammatory drugs": "非甾体抗炎药",
    "COX-2 Inhibitor": "COX-2抑制剂",
    "Cox-2 inhibitors": "COX-2抑制剂",
    "Salicylates": "水杨酸类",
    "Analgesic combinations": "镇痛组合药",
    "Narcotic analgesic combinations": "麻醉镇痛组合药",
    "Miscellaneous analgesics": "其他镇痛药",
    "Local Anesthetic": "局部麻醉药",
    "Local injectable anesthetics": "局部注射麻醉药",
    "General Anesthetic": "全身麻醉药",
    "General anesthetics": "全身麻醉药",
    "Skeletal Muscle Relaxant": "骨骼肌松弛剂",
    "Skeletal muscle relaxants": "骨骼肌松弛剂",
    "Skeletal muscle relaxant combinations": "骨骼肌松弛组合药",
    "Vaccine": "疫苗",
    "Viral vaccines": "病毒疫苗",
    "Allergenics": "过敏原制剂",
    "Contrast Agent": "造影剂",
    "Probiotics": "益生菌",
    "Herbal Supplement": "草药补充剂",
    "Nutraceutical products": "营养保健品",
    "5-aminosalicylates": "5-氨基水杨酸类",
    "Sedatives and hypnotics": "镇静催眠药",
    "Upper respiratory combinations": "上呼吸道组合药",
    "Nasal antihistamines and decongestants": "鼻腔抗组胺减充血药",
    "Nasal steroids": "鼻腔类固醇",
    "Antispasmodic": "解痉药",
    "Antispasmodics / antispasmodics": "解痉药",
    "Otic steroids": "耳用类固醇",
    "Mouth and throat products": "口腔咽喉产品",
    "Anorexiants": "食欲抑制剂",
    "Carbonic Anhydrase Inhibitor": "碳酸酐酶抑制剂",
    "Xanthine Oxidase Inhibitor": "黄嘌呤氧化酶抑制剂",
    "PDE5 Inhibitor": "PDE5抑制剂",
    "PDE4 Inhibitor": "PDE4抑制剂",
    "Phosphodiesterase Inhibitor": "磷酸二酯酶抑制剂",
    "COMT Inhibitor": "COMT抑制剂",
    "Decarboxylase Inhibitor": "脱羧酶抑制剂",
    "5-HT1 Agonist": "5-HT1激动剂",
    "5-HT3 Antagonist": "5-HT3拮抗剂",
    "Cannabinoid": "大麻素类",
    "Sympathomimetic": "拟交感药",
    "Sympathomimetic Amine": "拟交感胺类",
    "Adrenolytic Agent": "肾上腺溶解剂",
    "Alpha-1 Blocker": "α1受体阻断剂",
    "Alpha-2 Adrenergic Agonist": "α2肾上腺素能激动剂",
    "Alpha-2 Agonist": "α2激动剂",
    "Alpha/Beta-Blocker": "α/β受体阻断剂",
    "Alpha/Beta Agonist": "α/β受体激动剂",
    "Parathyroid Hormone Analog": "甲状旁腺激素类似物",
    "Prostacyclin Analog": "前列环素类似物",
    "Prostaglandin Analog": "前列腺素类似物",
    "Prostaglandin": "前列腺素",
    "Vasodilator / Hair Growth Stimulant": "血管扩张/促毛发生长剂",
    "Somatostatin and somatostatin analogs": "生长抑素及其类似物",
    "Protease Inhibitor": "蛋白酶抑制剂",
    "Protease inhibitors": "蛋白酶抑制剂",
    "Integrase Strand Transfer Inhibitor": "整合酶链转移抑制剂",
    "NNRTI": "NNRTI(非核苷逆转录酶抑制剂)",
    "NNRTIs": "非核苷逆转录酶抑制剂",
    "NRTI": "NRTI(核苷逆转录酶抑制剂)",
    "Nucleoside Reverse Transcriptase Inhibitor": "核苷逆转录酶抑制剂",
    "Nucleoside reverse transcriptase inhibitors (NRTIs)": "核苷逆转录酶抑制剂",
    "NS5B Polymerase Inhibitor": "NS5B聚合酶抑制剂",
    "CCR5 Antagonist": "CCR5拮抗剂",
    "Amylin Analog": "胰淀素类似物",
    "G-CSF Analog": "G-CSF类似物",
    "Recombinant Human IGF-1": "重组人IGF-1",
    "Growth Hormone": "生长激素",
    "Interferons": "干扰素类",
    "Immune globulins": "免疫球蛋白类",
    "Fumaric Acid Ester": "富马酸酯类",
    "Uroprotectant": "泌尿保护剂",
    "Urea Cycle Disorder Agent": "尿素循环障碍用药",
    "CFTR Potentiator": "CFTR增强剂",
    "Aldehyde Dehydrogenase Inhibitor": "醛脱氢酶抑制剂",
    "Alkalinizing Agent": "碱化剂",
    "Calcimimetic": "拟钙剂",
    "Antidiabetic combinations": "降糖组合药",
    "SABA + Anticholinergic": "短效β2激动剂+抗胆碱药",
    "Bronchodilator combinations": "支气管扩张组合药",
    "Anticholinergics / antispasmodics": "抗胆碱/解痉药",
    "Sex hormone combinations": "性激素组合药",
    "Psychotherapeutic combinations": "精神治疗组合药",
    "Antidiabetic combinations": "降糖组合药",
    "Miscellaneous antihyperlipidemic agents": "其他降脂药",
    "Miscellaneous antihypertensive combinations": "其他降压组合药",
    "Miscellaneous antineoplastics": "其他抗肿瘤药",
    "Miscellaneous antipsychotic agents": "其他抗精神病药",
    "Miscellaneous antivirals": "其他抗病毒药",
    "Miscellaneous anxiolytics": "其他抗焦虑药",
    "Miscellaneous bone resorption inhibitors": "其他骨吸收抑制剂",
    "Miscellaneous central nervous system agents": "其他中枢神经系统药",
    "Miscellaneous genitourinary tract agents": "其他泌尿生殖道药",
    "Miscellaneous topical agents": "其他外用药",
    "Miscellaneous uncategorized agents": "其他未分类药",
    "Miscellaneous antimalarials": "其他抗疟药",
    "Miscellaneous antidepressants": "其他抗抑郁药",
    "Miscellaneous anticonvulsants": "其他抗惊厥药",
    "Miscellaneous antibiotics": "其他抗生素",
    "Peripheral Opioid Receptor Antagonist": "外周阿片受体拮抗剂",
    "Peripheral opioid receptor antagonists": "外周阿片受体拮抗剂",
    "Vesicular Monoamine Transporter 2 (VMAT2) Inhibitor": "VMAT2抑制剂",
    "Anticholinergic antiemetics": "抗胆碱类止吐药",
    "Phenothiazine antiemetics": "吩噻嗪类止吐药",
    "Phenothiazine antipsychotics": "吩噻嗪类抗精神病药",
    "Thioxanthenes": "硫蒽类",
    "Serotonin Antagonist and Reuptake Inhibitor (SARI)": "5-HT拮抗再摄取抑制剂",
    "Serotonin Inverse Agonist": "5-HT反向激动剂",
    "Serotonin Partial Agonist and Reuptake Inhibitor (SPARI)": "5-HT部分激动再摄取抑制剂",
    "Serotonin-norepinephrine reuptake inhibitors": "5-HT-NE再摄取抑制剂",
    "Phenylpiperazine antidepressants": "苯基哌嗪类抗抑郁药",
    "Benzodiazepine Antagonist": "苯二氮卓拮抗剂",
    "Benzodiazepine anticonvulsants": "苯二氮卓类抗惊厥药",
    "Carbamate anticonvulsants": "氨基甲酸酯类抗惊厥药",
    "Dibenzazepine anticonvulsants": "二苯并氮杂卓类抗惊厥药",
    "Fatty acid derivative anticonvulsants": "脂肪酸衍生物类抗惊厥药",
    "Hydantoin anticonvulsants": "乙内酰脲类抗惊厥药",
    "Succinimide anticonvulsants": "琥珀酰亚胺类抗惊厥药",
    "Triazine anticonvulsants": "三嗪类抗惊厥药",
    "Pyrrolidine anticonvulsants": "吡咯烷类抗惊厥药",
    "Gamma-aminobutyric acid analogs": "γ-氨基丁酸类似物",
    "Selective phosphodiesterase-4 inhibitors": "选择性PDE4抑制剂",
    "Purine nucleosides": "嘌呤核苷类",
    "5-ASA Derivative": "5-ASA衍生物",
    "5-Lipoxygenase Inhibitor": "5-脂氧合酶抑制剂",
    "5-alpha Reductase Inhibitor": "5α还原酶抑制剂",
    "Adrenergic uptake inhibitors for ADHD": "肾上腺素摄取抑制剂(ADHD)",
    "Nicotinic Acetylcholine Receptor Partial Agonist": "烟碱乙酰胆碱受体部分激动剂",
    "Hyperpolarization-Activated Cyclic Nucleotide–Gated (HCN) Channel Blocker": "HCN通道阻滞剂",
    "Gallstone Dissolution Agent": "溶石药",
    "Adrenergic bronchodilators": "肾上腺素能支气管扩张药",
    "Antiadrenergic agents": "抗肾上腺素能药",
    "Antiadrenergic agents (central) with thiazides": "中枢抗肾上腺素能药+噻嗪类",
    "Antacid / Calcium Supplement": "抗酸药/钙补充剂",
    "Antacid / Laxative": "抗酸药/泻药",
    "Barbiturate + Analgesic": "巴比妥类+镇痛药",
    "Hyperglycemic Agent": "升血糖药",
    "AMPA Receptor Antagonist": "AMPA受体拮抗剂",
    "Glutamate Inhibitor": "谷氨酸抑制剂",
    "NMDA Receptor Antagonist": "NMDA受体拮抗剂",
    "Catecholamine": "儿茶酚胺类",
    "Local Anesthetic / Antiarrhythmic (Class Ib)": "局麻药/抗心律失常药(Ib类)",
    "Antiaderenergic": "抗肾上腺素能药",
    "centrally acting": "中枢作用药",
    "peripherally acting": "外周作用药",
    "mTOR Inhibitor": "mTOR抑制剂",
    "Melanocortin receptor agonists": "黑皮质素受体激动剂",
    "Viscosupplementation agents": "黏液补充剂",
    "Gallstone Dissolution Agent": "溶石药",
}

# ── 条件名映射 (高频疾病名手动映射) ──
# 1420种条件名中, 手动映射最常见的约200种
# 其余由缓存文件补充 (data/translations/condition_translations.json)

CONDITION_ZH_CORE: Dict[str, str] = {
    # 心血管
    "hypertension": "高血压",
    "high blood pressure": "高血压",
    "coronary artery disease": "冠心病",
    "angina": "心绞痛",
    "angina pectoris": "心绞痛",
    "myocardial infarction": "心肌梗死",
    "heart attack": "心肌梗死",
    "heart failure": "心力衰竭",
    "congestive heart failure": "充血性心力衰竭",
    "atrial fibrillation": "心房颤动",
    "arrhythmia": "心律失常",
    "deep vein thrombosis": "深静脉血栓",
    "pulmonary embolism": "肺栓塞",
    "peripheral arterial disease": "外周动脉疾病",
    "hyperlipidemia": "高脂血症",
    "high cholesterol": "高胆固醇血症",
    "hypercholesterolemia": "高胆固醇血症",
    "atherosclerosis": "动脉粥样硬化",

    # 内分泌
    "type 2 diabetes mellitus": "2型糖尿病",
    "type 2 diabetes": "2型糖尿病",
    "diabetes mellitus": "糖尿病",
    "diabetes": "糖尿病",
    "type 1 diabetes mellitus": "1型糖尿病",
    "type 1 diabetes": "1型糖尿病",
    "hypothyroidism": "甲状腺功能减退",
    "hyperthyroidism": "甲状腺功能亢进",
    "obesity": "肥胖",
    "hypertriglyceridemia": "高甘油三酯血症",
    "homozygous familial hypercholesterolemia": "纯合子家族性高胆固醇血症",

    # 呼吸
    "asthma": "哮喘",
    "chronic obstructive pulmonary disease": "慢性阻塞性肺疾病",
    "copd": "慢阻肺",
    "bronchitis": "支气管炎",
    "pneumonia": "肺炎",
    "upper respiratory infection": "上呼吸道感染",
    "common cold": "感冒",
    "tuberculosis": "肺结核",
    "pulmonary fibrosis": "肺纤维化",
    "pulmonary arterial hypertension": "肺动脉高压",
    "community-acquired pneumonia": "社区获得性肺炎",

    # 消化
    "peptic ulcer disease": "消化性溃疡",
    "gastric ulcer": "胃溃疡",
    "stomach ulcer": "胃溃疡",
    "duodenal ulcer": "十二指肠溃疡",
    "gastroesophageal reflux disease": "胃食管反流病",
    "gerd": "胃食管反流病",
    "gastritis": "胃炎",
    "ulcerative colitis": "溃疡性结肠炎",
    "crohn's disease": "克罗恩病",
    "crohn disease": "克罗恩病",
    "irritable bowel syndrome": "肠易激综合征",
    "ibs": "肠易激综合征",
    "diarrhea": "腹泻",
    "constipation": "便秘",
    "hepatitis": "肝炎",
    "fatty liver disease": "脂肪肝",
    "liver cirrhosis": "肝硬化",
    "cholecystitis": "胆囊炎",
    "cholelithiasis": "胆结石",
    "gallstones": "胆结石",
    "acid reflux": "反酸",
    "heartburn": "烧心",
    "nausea": "恶心",
    "vomiting": "呕吐",
    "helicobacter pylori eradication": "幽门螺杆菌根除",
    "abdominal pain": "腹痛",

    # 神经/精神
    "major depressive disorder": "重度抑郁症",
    "depression": "抑郁症",
    "generalized anxiety disorder": "广泛性焦虑症",
    "anxiety disorder": "焦虑症",
    "panic disorder": "惊恐障碍",
    "social anxiety disorder": "社交焦虑症",
    "insomnia": "失眠",
    "sleep disorder": "睡眠障碍",
    "migraine": "偏头痛",
    "headache": "头痛",
    "epilepsy": "癫痫",
    "seizure disorder": "癫痫",
    "parkinson disease": "帕金森病",
    "parkinson's disease": "帕金森病",
    "alzheimer disease": "阿尔茨海默病",
    "alzheimer's disease": "阿尔茨海默病",
    "schizophrenia": "精神分裂症",
    "obsessive compulsive disorder": "强迫症",
    "ocd": "强迫症",
    "adhd": "多动症",
    "attention deficit hyperactivity disorder": "注意力缺陷多动障碍",
    "bipolar disorder": "双相情感障碍",
    "bipolar i disorder": "双相I型障碍",
    "bipolar mania": "双相躁狂",
    "neuropathic pain": "神经病理性疼痛",
    "neuralgia": "神经痛",
    "postherpetic neuralgia": "带状疱疹后神经痛",
    "fibromyalgia": "纤维肌痛",

    # 肾/泌尿
    "chronic kidney disease": "慢性肾病",
    "ckd": "慢性肾病",
    "urinary tract infection": "尿路感染",
    "uti": "尿路感染",
    "kidney stones": "肾结石",
    "nephrolithiasis": "肾结石",
    "benign prostatic hyperplasia": "前列腺增生",
    "bph": "前列腺增生",
    "prostatitis": "前列腺炎",
    "urinary incontinence": "尿失禁",
    "overactive bladder": "膀胱过度活动症",

    # 风湿/骨骼
    "rheumatoid arthritis": "类风湿关节炎",
    "osteoarthritis": "骨关节炎",
    "gout": "痛风",
    "gouty arthritis": "痛风性关节炎",
    "osteoporosis": "骨质疏松症",
    "ankylosing spondylitis": "强直性脊柱炎",
    "systemic lupus erythematosus": "系统性红斑狼疮",
    "sle": "系统性红斑狼疮",
    "back pain": "腰背痛",
    "low back pain": "下腰痛",
    "joint pain": "关节痛",
    "muscle pain": "肌肉痛",
    "myalgia": "肌痛",

    # 感染/传染
    "fever": "发热",
    "pyrexia": "发热",
    "bacterial infection": "细菌感染",
    "viral infection": "病毒感染",
    "fungal infection": "真菌感染",
    "herpes simplex virus infection": "单纯疱疹病毒感染",
    "herpes zoster": "带状疱疹",
    "shingles": "带状疱疹",
    "influenza": "流感",
    "flu": "流感",
    "covid-19": "新冠",
    "hiv infection": "HIV感染",
    "syphilis": "梅毒",
    "pneumocystis jirovecii pneumonia": "肺孢子菌肺炎",
    "sepsis": "败血症",
    "septicemia": "败血症",
    "cellulitis": "蜂窝织炎",
    "impetigo": "脓疱病",
    "lyme disease": "莱姆病",
    "malaria": "疟疾",
    "malaria prophylaxis": "疟疾预防",
    "traveler's diarrhea": "旅行者腹泻",
    "shigellosis": "志贺菌病",
    "cholera": "霍乱",
    "parasitic infection": "寄生虫感染",

    # 皮肤
    "eczema": "湿疹",
    "atopic dermatitis": "特应性皮炎",
    "urticaria": "荨麻疹",
    "hives": "荨麻疹",
    "psoriasis": "银屑病",
    "plaque psoriasis": "斑块状银屑病",
    "acne vulgaris": "痤疮",
    "acne": "痤疮",
    "acne rosacea": "玫瑰痤疮",
    "rosacea": "玫瑰痤疮",
    "rash": "皮疹",
    "dermatitis": "皮炎",
    "contact dermatitis": "接触性皮炎",
    "allergic dermatitis": "过敏性皮炎",
    "seborrheic dermatitis": "脂溢性皮炎",
    "vitiligo": "白癜风",
    "alopecia": "脱发",
    "alopecia areata": "斑秃",
    "hair loss": "脱发",
    "pruritus": "瘙痒",
    "itching": "瘙痒",
    "warts": "疣",
    "fungal skin infection": "皮肤真菌感染",
    "candidiasis": "念珠菌病",

    # 血液/肿瘤
    "anemia": "贫血",
    "iron deficiency anemia": "缺铁性贫血",
    "leukemia": "白血病",
    "acute lymphoblastic leukemia": "急性淋巴细胞白血病",
    "chronic lymphocytic leukemia": "慢性淋巴细胞白血病",
    "lymphoma": "淋巴瘤",
    "non-hodgkin lymphoma": "非霍奇金淋巴瘤",
    "multiple myeloma": "多发性骨髓瘤",
    "breast cancer": "乳腺癌",
    "lung cancer": "肺癌",
    "colon cancer": "结肠癌",
    "colorectal cancer": "结直肠癌",
    "prostate cancer": "前列腺癌",
    "ovarian cancer": "卵巢癌",
    "pancreatic cancer": "胰腺癌",
    "liver cancer": "肝癌",
    "thyroid cancer": "甲状腺癌",
    "skin cancer": "皮肤癌",
    "melanoma": "黑色素瘤",
    "basal cell carcinoma": "基底细胞癌",
    "renal cell carcinoma": "肾细胞癌",
    "cervical cancer": "宫颈癌",
    "brain tumor": "脑肿瘤",
    "neuroblastoma": "神经母细胞瘤",

    # 眼科
    "glaucoma": "青光眼",
    "cataract": "白内障",
    "dry eye syndrome": "干眼症",
    "conjunctivitis": "结膜炎",
    "allergic conjunctivitis": "过敏性结膜炎",
    "macular degeneration": "黄斑变性",
    "eye inflammation": "眼部炎症",

    # 其他
    "allergic rhinitis": "过敏性鼻炎",
    "allergy": "过敏",
    "allergic reaction": "过敏反应",
    "pain": "疼痛",
    "chronic pain": "慢性疼痛",
    "acute pain": "急性疼痛",
    "postoperative pain": "术后疼痛",
    "inflammation": "炎症",
    "inflammatory conditions": "炎症性疾病",
    "inflammatory condition": "炎症性疾病",
    "edema": "水肿",
    "dizziness": "头晕",
    "vertigo": "眩晕",
    "cough": "咳嗽",
    "wheezing": "喘息",
    "shortness of breath": "气短",
    "dyspnea": "呼吸困难",
    "chest pain": "胸痛",
    "palpitation": "心悸",
    "tremor": "震颤",
    "essential tremor": "特发性震颤",
    "seizures": "癫痫发作",
    "weight loss": "体重下降",
    "weight gain": "体重增加",
    "fatigue": "疲劳",
    "weakness": "无力",
    "numbness": "麻木",
    "paresthesia": "感觉异常",
    "tinnitus": "耳鸣",
    "dry mouth": "口干",
    "appetite loss": "食欲不振",
    "anorexia": "厌食",
    "swelling": "肿胀",

    # 妇产/生殖
    "contraception": "避孕",
    "menopause": "更年期",
    "dysmenorrhea": "痛经",
    "menstrual pain": "痛经",
    "endometriosis": "子宫内膜异位症",
    "polycystic ovary syndrome": "多囊卵巢综合征",
    "infertility": "不孕",
    "erectile dysfunction": "勃起功能障碍",
    "premenstrual dysphoric disorder": "经前烦躁障碍",
    "vaginitis": "阴道炎",
    "bacterial vaginosis": "细菌性阴道病",
    "vulvovaginal candidiasis": "外阴阴道念珠菌病",
    "pelvic inflammatory disease": "盆腔炎",

    # 戒断/依赖
    "smoking cessation": "戒烟",
    "nicotine dependence": "尼古丁依赖",
    "alcohol dependence": "酒精依赖",
    "alcoholism": "酒精依赖",
    "opioid dependence": "阿片依赖",
    "opioid withdrawal": "阿片戒断",

    # 疫苗/预防
    "covid-19 prevention": "新冠预防",
    "covid-19 treatment": "新冠治疗",
    "immunization": "免疫接种",
    "vaccination": "疫苗接种",

    # 非常见但重要的条件
    "acute otitis media": "急性中耳炎",
    "otitis media": "中耳炎",
    "tonsillitis": "扁桃体炎",
    "pharyngitis": "咽炎",
    "sinusitis": "鼻窦炎",
    "appendicitis": "阑尾炎",
    "pancreatitis": "胰腺炎",
    "cholecystitis": "胆囊炎",
    "diverticulitis": "憩室炎",
    "stroke": "中风",
    "cerebrovascular accident": "脑血管意外",
    "cerebral infarction": "脑梗死",
    "cerebral hemorrhage": "脑出血",
    "hemorrhagic stroke": "出血性中风",
    "transient ischemic attack": "短暂性脑缺血发作",
    "organ transplant rejection prophylaxis": "器官移植排斥预防",
    "prophylaxis of organ transplant rejection": "器官移植排斥预防",
    "organ transplant rejection": "器官移植排斥",
    "rickettsial infection": "立克次体感染",
    "nocardiosis": "诺卡菌病",
    "toxoplasmosis": "弓形虫病",
    "periodontitis": "牙周炎",
    "chronic periodontitis": "慢性牙周炎",
    "diphtheria": "白喉",
    "pertussis": "百日咳",
    "legionnaires' disease": "军团菌病",
    "plague": "鼠疫",
    "inhalational anthrax": "吸入性炭疽",
    "chlamydia infection": "衣原体感染",
    "sexually transmitted infection": "性传播感染",
    "human immunodeficiency virus": "人类免疫缺陷病毒",
    "acromegaly": "肢端肥大症",
    "carcinoid tumors": "类癌肿瘤",
    "neuroendocrine tumors": "神经内分泌肿瘤",
    "interleukin-1 receptor antagonist deficiency": "白介素-1受体拮抗剂缺乏症",
    "eosinophilic esophagitis": "嗜酸性食管炎",
    "prurigo nodularis": "结节性痒疹",
    "hidradenitis suppurativa": "化脓性汗腺炎",
    "lichen planus": "扁平苔藓",
    "photoaging": "光老化",
    "melasma": "黄褐斑",
    "keratosis pilaris": "毛周角化症",
    "diaper rash": "尿布疹",
    "diaper rash with suspected infection": "疑似感染的尿布疹",
    "corns and calluses": "鸡眼和茧",
    "dandruff": "头皮屑",
    "scabies": "疥疮",
    "pediculosis": "虱病",
    "pediculosis capitis": "头虱病",
    "icthyosis": "鱼鳞病",
    "acne scarring": "痤疮疤痕",
    "acne vulgaris refractory to other therapy": "难治性痤疮",
    "severe nodular acne": "重度结节性痤疮",
    "seborrheic keratosis": "脂溢性角化病",

    # 疼痛细分
    "neuropathic pain": "神经病理性疼痛",
    "cancer pain": "癌痛",
    "breakthrough pain": "爆发痛",
    "bone pain": "骨痛",
    "abdominal pain": "腹痛",
    "stomach pain": "胃痛",
    "joint pain": "关节痛",
    "muscle pain": "肌肉痛",
    "chest pain": "胸痛",
    "back pain": "背痛",

    # 精神细分
    "major depressive disorder (adjunct)": "重度抑郁症(辅助)",
    "treatment-resistant depression": "难治性抑郁症",
    "seasonal affective disorder": "季节性情感障碍",
    "post-traumatic stress disorder": "创伤后应激障碍",
    "mixed depressive and anxiety disorder": "混合性抑郁焦虑障碍",
    "acute agitation": "急性躁动",
    "schizoaffective disorder": "分裂情感性障碍",
    "tardive dyskinesia": "迟发性运动障碍",

    # 眼/耳细分
    "ocular hypertension": "眼高压",
    "open-angle glaucoma": "开角型青光眼",
    "angle-closure glaucoma": "闭角型青光眼",
    "age-related macular degeneration": "年龄相关性黄斑变性",
    "diabetic retinopathy": "糖尿病视网膜病变",
    "mydriasis": "瞳孔散大",
    "intraocular inflammation": "眼内炎症",

    # 更多
    "adrenal insufficiency": "肾上腺功能不全",
    "addison disease": "艾迪生病",
    "cushing syndrome": "库欣综合征",
    "adrenocortical carcinoma": "肾上腺皮质癌",
    "hypercalcemia": "高钙血症",
    "hypocalcemia": "低钙血症",
    "hypokalemia": "低钾血症",
    "hyperkalemia": "高钾血症",
    "hyponatremia": "低钠血症",
    "diabetic ketoacidosis": "糖尿病酮症酸中毒",
    "metabolic acidosis": "代谢性酸中毒",
    "respiratory acidosis": "呼吸性酸中毒",
    "bowel preparation before colonoscopy": "结肠镜检查前肠道准备",
    "folate deficiency": "叶酸缺乏",
    "vitamin e deficiency": "维生素E缺乏",
    "vitamin d deficiency": "维生素D缺乏",
    "vitamin b12 deficiency": "维生素B12缺乏",

    # ── 常见副作用关键词 ──
    "dry skin": "皮肤干燥",
    "skin dryness": "皮肤干燥",
    "drowsiness": "嗜睡",
    "sedation": "镇静作用",
    "lightheadedness": "头轻",
    "cramps": "痉挛",
    "bloating": "腹胀",
    "gas": "胀气",
    "flatulence": "胀气",
    "appetite loss": "食欲不振",
    "loss of appetite": "食欲不振",
    "tiredness": "疲倦",
    "sleep disturbance": "睡眠障碍",
    "skin rash": "皮疹",
    "flushing": "潮红",
    "redness": "红肿",
    "irritation": "刺激",
    "stinging": "刺痛",
    "burning": "烧灼感",
    "tingling": "刺麻感",
    "shaking": "抖动",
    "tachycardia": "心动过速",
    "bradycardia": "心动过缓",
    "dry cough": "干咳",
    "sore throat": "喉咙痛",
    "throat irritation": "喉咙刺激",
    "nasal congestion": "鼻塞",
    "runny nose": "流鼻涕",
    "rhinorrhea": "流鼻涕",
    "sneezing": "打喷嚏",
    "muscle cramp": "肌肉痉挛",
    "arthralgia": "关节痛",
    "chills": "寒战",
    "night sweats": "盗汗",
    "sweating": "出汗",
    "hot flashes": "潮热",
    "thinning hair": "头发稀疏",
    "skin discoloration": "皮肤变色",
    "hyperpigmentation": "色素沉着",
    "photosensitivity": "光敏感",
    "sun sensitivity": "日光敏感",
    "blurred vision": "视力模糊",
    "visual disturbance": "视觉障碍",
    "eye irritation": "眼部刺激",
    "dry eyes": "干眼症",
    "tearing": "流泪",
    "hearing loss": "听力下降",
    "ringing in ears": "耳鸣",
    "mood changes": "情绪变化",
    "confusion": "混乱",
    "memory impairment": "记忆障碍",
    "cognitive impairment": "认知障碍",
    "hallucinations": "幻觉",
    "withdrawal": "戒断",
    "dependency": "依赖",
    "tolerance": "耐受性",
    "addiction": "成瘾",
    "bleeding": "出血",
    "bruising": "瘀伤",
    "easy bruising": "易瘀伤",
    "thrombocytopenia": "血小板减少",
    "leukopenia": "白细胞减少",
    "neutropenia": "中性粒细胞减少",
    "secondary infection": "继发感染",
    "oral candidiasis": "口腔念珠菌病",
    "thrush": "鹅口疮",
    "kidney damage": "肾损伤",
    "renal impairment": "肾功能损害",
    "liver damage": "肝损伤",
    "hepatotoxicity": "肝毒性",
    "hepatic impairment": "肝功能损害",
    "jaundice": "黄疸",
    "hyperglycemia": "高血糖",
    "hypoglycemia": "低血糖",
    "rebound effect": "反弹效应",
    "steroid withdrawal": "类固醇戒断",
    "adrenal suppression": "肾上腺抑制",
    "growth suppression": "生长抑制",
    "teratogenicity": "致畸性",
    "sexual dysfunction": "性功能障碍",
    "decreased libido": "性欲减退",
    "impotence": "阳痿",
    "gynecomastia": "男性乳房发育",
    "galactorrhea": "溢乳",
    "amenorrhea": "闭经",
    "oligomenorrhea": "月经稀少",
    "vaginal dryness": "阴道干燥",
    "vaginal bleeding": "阴道出血",
    "priapism": "异常勃起",
    "anaphylaxis": "过敏性休克",
    "angioedema": "血管性水肿",
    "drug eruption": "药物性皮疹",
    "erythema multiforme": "多形性红斑",
    "erosive esophagitis": "糜烂性食管炎",
    "varicella zoster virus": "水痘带状疱疹病毒",
    "c. difficile": "艰难梭菌",
}


class TranslationMapper:
    """英→中翻译映射器

    加载顺序:
    1. 核心手动映射 (DRUG_CLASS_ZH_CORE / CONDITION_ZH_CORE)
    2. googletrans 缓存文件 (data/translations/*.json)
    3. 找不到 → 保留英文原名
    """

    def __init__(self):
        self._class_map: Dict[str, str] = {}
        self._condition_map: Dict[str, str] = {}
        self._enum_map: Dict[str, str] = dict(SAFETY_TYPE_ZH)
        self._enum_map.update(QUALITY_WARNING_ZH)
        self._drug_name_map: Dict[str, str] = {}
        self._se_map: Dict[str, str] = {}

        # 加载顺序: 先缓存, 再手动映射覆盖 → 手动映射优先级最高
        self._load_caches()
        self._class_map.update(DRUG_CLASS_ZH_CORE)  # 手动覆盖缓存
        self._condition_map.update(CONDITION_ZH_CORE)  # 手动覆盖缓存

    def _load_caches(self):
        """加载翻译缓存文件"""
        translations_dir = Path(settings.data_dir) / "translations"

        # 药物类别缓存 — 先加载缓存再被手动映射覆盖
        cache_path = translations_dir / "drug_class_translations.json"
        if cache_path.exists():
            try:
                cache = json.loads(cache_path.read_text(encoding='utf-8'))
                self._class_map.update(cache)
                logger.info(f"Loaded drug_class cache: {len(cache)} entries")
            except Exception as e:
                logger.warning(f"Failed to load drug_class cache: {e}")

        # 条件名缓存 — 先加载缓存再被手动映射覆盖
        cache_path = translations_dir / "condition_translations.json"
        if cache_path.exists():
            try:
                cache = json.loads(cache_path.read_text(encoding='utf-8'))
                self._condition_map.update(cache)
                logger.info(f"Loaded condition cache: {len(cache)} entries")
            except Exception as e:
                logger.warning(f"Failed to load condition cache: {e}")

        # 副作用关键词缓存
        cache_path = translations_dir / "side_effects_keyword_translations.json"
        if cache_path.exists():
            try:
                cache = json.loads(cache_path.read_text(encoding='utf-8'))
                self._se_map.update(cache)
                logger.info(f"Loaded side_effects keyword cache: {len(cache)} entries")
            except Exception as e:
                logger.warning(f"Failed to load side_effects cache: {e}")

        # 药物名翻译缓存（复用已有的 drug_name_translations.json）
        cache_path = Path(settings.data_dir) / "drug_name_translations.json"
        if cache_path.exists():
            try:
                cache = json.loads(cache_path.read_text(encoding='utf-8'))
                self._drug_name_map.update(cache)
                logger.info(f"Loaded drug_name cache: {len(cache)} entries")
            except Exception as e:
                logger.warning(f"Failed to load drug_name cache: {e}")

    def translate_class(self, english_class: str) -> str:
        """翻译药物类别 (支持逗号分隔的多类别)"""
        if not english_class:
            return english_class

        # 多类别逗号分隔
        parts = []
        for c in english_class.split(','):
            c = c.strip()
            translated = self._class_map.get(c, c)
            parts.append(translated)

        return ', '.join(parts)

    def translate_condition(self, english_condition: str) -> str:
        """翻译疾病/适应症名"""
        if not english_condition:
            return english_condition
        return self._condition_map.get(english_condition, english_condition)

    def translate_enum(self, english_enum: str) -> str:
        """翻译枚举值 (safetyType / qualityWarning)"""
        if not english_enum:
            return english_enum
        return self._enum_map.get(english_enum, english_enum)

    def translate_side_effects_raw(self, raw: str) -> list[str]:
        """翻译副作用raw为中文列表

        策略:
        - 简短关键词 (≤30字符) → 翻译后展示
        - 长句描述 (>30字符) → 跳过, 不适合前端展示
        - 只有成功翻译为中文的才展示, 英文原文不展示
        """
        if not raw:
            return []

        # 分割副作用 (支持逗号、分号、括号内内容跳过)
        # 先去除括号内的补充说明，如 "(VZV)", "(including C. difficile)"
        import re
        clean_raw = re.sub(r'\([^)]*\)', '', raw)  # 去除括号内容
        parts = [p.strip() for p in clean_raw.replace(';', ',').split(',')]

        # 翻译每个关键词
        translated = []
        for p in parts:
            p_lower = p.strip().lower()
            if not p_lower:
                continue

            # 过滤太长的整句（副作用关键词应≤30字符）
            if len(p_lower) > 30:
                continue

            # 过滤太短的碎片
            if len(p_lower) < 3:
                continue

            # 去掉常见前缀词
            clean = p_lower
            for prefix in ['may cause ', 'call your doctor at once if you have: ',
                           'stop using ', 'severe ', 'some ']:
                clean = clean.replace(prefix, '')
            clean = clean.strip()

            if len(clean) < 3:
                continue

            # 查副作用关键词缓存
            zh = self._se_map.get(clean, None)
            if zh and zh != clean:
                translated.append(zh)
                continue

            # 查条件映射（副作用名和疾病名有重叠）
            zh = self._condition_map.get(clean, None)
            if zh and zh != clean:
                translated.append(zh)
                continue

            # 也查原始 (含前缀) 的版本
            zh = self._se_map.get(p_lower, None)
            if zh and zh != p_lower:
                translated.append(zh)
                continue

            zh = self._condition_map.get(p_lower, None)
            if zh and zh != p_lower:
                translated.append(zh)
                continue

            # 无法翻译为中文 → 不展示英文原文（用户看不到中文副作用比看到英文更好）

        # 去重
        return list(set(translated))

    def class_coverage_stats(self) -> dict:
        """翻译覆盖率统计"""
        return {
            "drug_class_manual": len(DRUG_CLASS_ZH_CORE),
            "drug_class_cached": len(self._class_map) - len(DRUG_CLASS_ZH_CORE),
            "condition_manual": len(CONDITION_ZH_CORE),
            "condition_cached": len(self._condition_map) - len(CONDITION_ZH_CORE),
            "enum_total": len(self._enum_map),
        }


# 全局单例
_mapper: TranslationMapper | None = None


def get_mapper() -> TranslationMapper:
    """获取全局翻译映射器"""
    global _mapper
    if _mapper is None:
        _mapper = TranslationMapper()
    return _mapper
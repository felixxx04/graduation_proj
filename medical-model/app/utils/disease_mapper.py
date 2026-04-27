"""中文→英文疾病/症状名映射 + 症状→疾病映射

解决推荐系统核心匹配问题:
1. 前端传入中文疾病名(如"发烧")，但药物适应症是英文(如"fever")
2. 症状(如"头疼")需关联到可能的疾病(如"headache"/"migraine")才能匹配适应症
3. 中英文逗号分隔符统一处理

策略:
- 中文疾病名 → 英文标准化名 (用于适应症匹配)
- 中文症状名 → 关联英文疾病名 (用于扩展匹配范围)
- 英文疾病名也做标准化 (缩写→全称)
"""

import logging
from typing import Dict, List, Set

logger = logging.getLogger(__name__)

# ── 中文疾病名 → 英文标准化名 ──
# 涵盖常见输入: 俗名、缩写、口语描述

CHINESE_TO_ENGLISH_DISEASE: Dict[str, List[str]] = {
    # 心血管
    "高血压": ["hypertension", "high blood pressure"],
    "低血压": ["hypotension", "low blood pressure"],
    "冠心病": ["coronary artery disease", "coronary heart disease"],
    "心绞痛": ["angina", "angina pectoris"],
    "心肌梗死": ["myocardial infarction", "heart attack"],
    "心梗": ["myocardial infarction"],
    "心力衰竭": ["heart failure", "congestive heart failure"],
    "心衰": ["heart failure", "congestive heart failure"],
    "心房颤动": ["atrial fibrillation"],
    "房颤": ["atrial fibrillation"],
    "心律失常": ["arrhythmia"],
    "动脉粥样硬化": ["atherosclerosis", "arteriosclerosis"],
    "深静脉血栓": ["deep vein thrombosis"],
    "肺栓塞": ["pulmonary embolism"],
    "外周动脉疾病": ["peripheral arterial disease"],
    "高血脂": ["hyperlipidemia", "high cholesterol"],
    "高脂血症": ["hyperlipidemia", "high cholesterol"],
    "高胆固醇": ["hypercholesterolemia", "high cholesterol"],
    "胆固醇高": ["hypercholesterolemia"],
    # 内分泌
    "糖尿病": ["diabetes mellitus", "diabetes"],
    "2型糖尿病": ["type 2 diabetes mellitus", "type 2 diabetes", "diabetes mellitus"],
    "1型糖尿病": ["type 1 diabetes mellitus", "type 1 diabetes"],
    "甲状腺功能减退": ["hypothyroidism"],
    "甲减": ["hypothyroidism"],
    "甲状腺功能亢进": ["hyperthyroidism"],
    "甲亢": ["hyperthyroidism"],
    "甲状腺肿": ["goiter", "thyroid enlargement"],
    "肥胖": ["obesity"],
    "代谢综合征": ["metabolic syndrome"],
    # 呼吸系统
    "哮喘": ["asthma"],
    "慢阻肺": ["chronic obstructive pulmonary disease", "copd"],
    "慢性阻塞性肺疾病": ["chronic obstructive pulmonary disease", "copd"],
    "支气管炎": ["bronchitis"],
    "肺炎": ["pneumonia"],
    "上呼吸道感染": ["upper respiratory infection", "upper respiratory tract infection"],
    "感冒": ["upper respiratory infection", "common cold"],
    "肺结核": ["tuberculosis"],
    "肺纤维化": ["pulmonary fibrosis"],
    "肺动脉高压": ["pulmonary arterial hypertension"],
    # 消化系统
    "胃溃疡": ["peptic ulcer disease", "gastric ulcer", "stomach ulcer"],
    "十二指肠溃疡": ["duodenal ulcer", "peptic ulcer disease"],
    "胃食管反流": ["gastroesophageal reflux disease", "gerd"],
    "反流性食管炎": ["gastroesophageal reflux disease", "gerd"],
    "胃炎": ["gastritis"],
    "肠炎": ["enteritis", "colitis"],
    "溃疡性结肠炎": ["ulcerative colitis"],
    "克罗恩病": ["crohn disease", "crohn's disease"],
    "肠易激综合征": ["irritable bowel syndrome", "ibs"],
    "腹泻": ["diarrhea"],
    "便秘": ["constipation"],
    "肝炎": ["hepatitis"],
    "脂肪肝": ["nonalcoholic steatohepatitis", "fatty liver disease"],
    "肝硬化": ["liver cirrhosis"],
    "胆囊炎": ["cholecystitis"],
    "胆结石": ["cholelithiasis", "gallstones"],
    # 神经/精神
    "抑郁症": ["major depressive disorder", "depression"],
    "抑郁": ["depression"],
    "焦虑症": ["anxiety disorder", "generalized anxiety disorder"],
    "焦虑": ["anxiety disorder"],
    "失眠": ["insomnia", "sleep disorder"],
    "偏头痛": ["migraine"],
    "头痛": ["headache"],
    "癫痫": ["epilepsy", "seizure disorder"],
    "帕金森病": ["parkinson disease", "parkinson's disease"],
    "阿尔茨海默病": ["alzheimer disease", "alzheimer's disease"],
    "老年痴呆": ["alzheimer disease"],
    "多动症": ["attention deficit hyperactivity disorder", "adhd"],
    "精神分裂症": ["schizophrenia"],
    "强迫症": ["obsessive compulsive disorder", "ocd"],
    "惊恐障碍": ["panic disorder"],
    "社交焦虑": ["social anxiety disorder"],
    # 肾/泌尿
    "慢性肾病": ["chronic kidney disease", "ckd"],
    "尿路感染": ["urinary tract infection", "uti"],
    "尿路结石": ["urinary calculi", "kidney stones"],
    "肾结石": ["nephrolithiasis", "kidney stones"],
    "前列腺增生": ["benign prostatic hyperplasia", "bph"],
    "尿失禁": ["urinary incontinence"],
    # 风湿/骨骼
    "类风湿关节炎": ["rheumatoid arthritis"],
    "骨关节炎": ["osteoarthritis"],
    "痛风": ["gout"],
    "骨质疏松": ["osteoporosis"],
    "骨质疏松症": ["osteoporosis"],
    "强直性脊柱炎": ["ankylosing spondylitis"],
    "系统性红斑狼疮": ["systemic lupus erythematosus", "sle"],
    "腰背痛": ["back pain", "low back pain"],
    "颈椎病": ["cervical spondylosis"],
    # 感染/传染
    "发烧": ["fever", "pyrexia", "febrile illness"],
    "发热": ["fever", "pyrexia"],
    "细菌感染": ["bacterial infection"],
    "病毒感染": ["viral infection"],
    "真菌感染": ["fungal infection"],
    "疱疹": ["herpes simplex virus infection"],
    "带状疱疹": ["herpes zoster", "shingles"],
    "流感": ["influenza", "flu"],
    "新冠": ["covid-19", "coronavirus infection"],
    "艾滋病": ["human immunodeficiency virus", "hiv infection"],
    "梅毒": ["syphilis"],
    "寄生虫感染": ["parasitic infection", "parasitic worm infection"],
    "蛔虫": ["ascariasis", "parasitic worm infection"],
    # 皮肤
    "湿疹": ["eczema", "atopic dermatitis"],
    "荨麻疹": ["urticaria", "hives"],
    "银屑病": ["psoriasis"],
    "牛皮癣": ["psoriasis"],
    "痤疮": ["acne vulgaris", "acne"],
    "痘痘": ["acne vulgaris", "acne"],
    "皮疹": ["rash", "dermatitis"],
    "过敏性皮炎": ["allergic dermatitis", "contact dermatitis"],
    "带状疱疹后神经痛": ["postherpetic neuralgia"],
    # 血液/肿瘤
    "贫血": ["anemia"],
    "缺铁性贫血": ["iron deficiency anemia"],
    "白血病": ["leukemia"],
    "淋巴瘤": ["lymphoma"],
    "乳腺癌": ["breast cancer"],
    "肺癌": ["lung cancer"],
    "结肠癌": ["colon cancer", "colorectal cancer"],
    "前列腺癌": ["prostate cancer"],
    # 眼科
    "青光眼": ["glaucoma"],
    "白内障": ["cataract"],
    "干眼症": ["dry eye syndrome"],
    "结膜炎": ["conjunctivitis"],
    # 其他
    "过敏": ["allergic rhinitis", "allergy"],
    "过敏性鼻炎": ["allergic rhinitis"],
    "疼痛": ["pain"],
    "慢性疼痛": ["chronic pain"],
    "术后疼痛": ["postoperative pain"],
    "恶心": ["nausea"],
    "呕吐": ["vomiting", "emesis"],
    "眩晕": ["vertigo", "dizziness"],
    "晕眩": ["vertigo", "dizziness"],
    "水肿": ["edema", "swelling"],
    "炎症": ["inflammation", "inflammatory condition"],
    "脱发": ["alopecia", "hair loss"],
    "多囊卵巢综合征": ["polycystic ovary syndrome"],
    "不孕": ["infertility"],
    "勃起功能障碍": ["erectile dysfunction"],
    "阳痿": ["erectile dysfunction"],
    "痛经": ["dysmenorrhea", "menstrual pain"],
    "月经不调": ["menstrual irregularity"],
    "更年期综合征": ["menopause"],
    "戒烟": ["smoking cessation", "nicotine dependence"],
    "酗酒": ["alcohol dependence", "alcoholism"],
    "中毒": ["poisoning", "toxicity"],
    # 新增常见疾病（修复缺失的关键疾病名）
    "中风": ["stroke", "cerebrovascular accident"],
    "脑卒中": ["stroke", "cerebrovascular accident"],
    "脑梗": ["cerebral infarction", "stroke"],
    "脑梗死": ["cerebral infarction", "stroke"],
    "脑出血": ["cerebral hemorrhage", "stroke", "hemorrhagic stroke"],
    "脑溢血": ["cerebral hemorrhage", "stroke"],
    "阑尾炎": ["appendicitis"],
    "扁桃体炎": ["tonsillitis"],
    "中耳炎": ["otitis media"],
    "咽炎": ["pharyngitis"],
    "心肌病": ["cardiomyopathy"],
    "肩周炎": ["adhesive capsulitis", "frozen shoulder"],
    "坐骨神经痛": ["sciatica"],
    "接触性皮炎": ["contact dermatitis"],
    "甲状腺癌": ["thyroid cancer"],
    "胰腺炎": ["pancreatitis"],
    "腮腺炎": ["mumps", "parotitis"],
    "附件炎": ["adnexitis", "pelvic inflammatory disease"],
    "盆腔炎": ["pelvic inflammatory disease"],
    "宫颈炎": ["cervicitis"],
    "阴道炎": ["vaginitis"],
    "前列腺炎": ["prostatitis"],
}

# ── 中文症状名 → 关联英文疾病名 ──
# 症状不是疾病本身，但可以关联到可能的疾病

SYMPTOM_TO_DISEASE: Dict[str, List[str]] = {
    # 常见症状 → 直接英文症状名 + 1-2个高概率关联疾病
    # 不映射到过于宽泛的类别（如"bacterial infection"、"viral infection"）
    "发烧": ["fever", "influenza"],
    "发热": ["fever", "influenza"],
    "头疼": ["headache", "migraine"],
    "头痛": ["headache", "migraine"],
    "想吐": ["nausea"],
    "恶心": ["nausea"],
    "呕吐": ["vomiting"],
    "拉肚子": ["diarrhea"],
    "腹泻": ["diarrhea"],
    "咳嗽": ["cough", "upper respiratory infection"],
    "干咳": ["cough"],
    "咳痰": ["cough", "bronchitis"],
    "喘": ["asthma", "wheezing"],
    "喘息": ["asthma", "wheezing"],
    "胸闷": ["chest tightness", "angina"],
    "胸痛": ["chest pain", "angina"],
    "心慌": ["palpitation", "arrhythmia"],
    "心悸": ["palpitation", "arrhythmia"],
    "气短": ["shortness of breath", "dyspnea"],
    "呼吸困难": ["dyspnea", "shortness of breath"],
    "头晕": ["dizziness", "vertigo"],
    "眩晕": ["vertigo", "dizziness"],
    "乏力": ["fatigue"],
    "疲倦": ["fatigue"],
    "无力": ["weakness"],
    "水肿": ["edema"],
    "脚肿": ["edema", "peripheral edema"],
    "腿肿": ["edema", "peripheral edema"],
    "肚子疼": ["abdominal pain", "stomach pain"],
    "腹痛": ["abdominal pain"],
    "胃痛": ["stomach pain", "gastritis"],
    "胃疼": ["stomach pain", "gastritis"],
    "反酸": ["acid reflux", "gastroesophageal reflux disease"],
    "烧心": ["heartburn", "gastroesophageal reflux disease"],
    "关节疼": ["joint pain", "arthralgia"],
    "关节痛": ["joint pain", "arthralgia"],
    "腰疼": ["back pain", "low back pain"],
    "腰痛": ["back pain", "low back pain"],
    "肌肉酸痛": ["myalgia", "muscle pain"],
    "肌肉痛": ["myalgia", "muscle pain"],
    "抽筋": ["cramp", "muscle cramp"],
    "皮疹": ["rash", "dermatitis"],
    "痒": ["pruritus", "itching"],
    "皮肤瘙痒": ["pruritus", "itching"],
    "起痘": ["acne vulgaris", "acne"],
    "过敏": ["allergic rhinitis", "allergy"],
    "眼睛痒": ["ocular itching", "allergic conjunctivitis"],
    "流泪": ["tearing", "lacrimation"],
    "鼻塞": ["nasal congestion", "allergic rhinitis"],
    "流鼻涕": ["rhinorrhea", "runny nose", "allergic rhinitis"],
    "打喷嚏": ["sneezing", "allergic rhinitis"],
    "尿频": ["urinary frequency", "urinary tract infection"],
    "尿急": ["urinary urgency", "urinary tract infection"],
    "尿痛": ["dysuria", "urinary tract infection"],
    "血尿": ["hematuria", "urinary tract infection"],
    "失眠": ["insomnia", "sleep disorder"],
    "睡不着": ["insomnia", "sleep disorder"],
    "多梦": ["sleep disorder"],
    "焦虑不安": ["anxiety disorder", "generalized anxiety disorder"],
    "情绪低落": ["depression", "major depressive disorder"],
    "烦躁": ["irritability", "anxiety disorder"],
    "手抖": ["tremor", "essential tremor"],
    "震颤": ["tremor"],
    "麻木": ["numbness", "paresthesia"],
    "刺痛": ["tingling", "paresthesia"],
    "耳鸣": ["tinnitus"],
    "听力下降": ["hearing loss"],
    "视力模糊": ["blurred vision"],
    "口干": ["dry mouth", "xerostomia"],
    "口渴": ["polydipsia", "thirst"],
    "食欲不振": ["anorexia", "loss of appetite"],
    "吃不下": ["anorexia", "loss of appetite"],
    "体重下降": ["weight loss"],
    "消瘦": ["weight loss"],
    "体重增加": ["weight gain"],
    "发胖": ["weight gain"],
}

# ── 英文疾病名标准化映射 (扩充版) ──
# 补充 clinical_matcher.py 之外的常见输入

ENGLISH_DISEASE_EXPAND: Dict[str, List[str]] = {
    "fever": ["fever", "pyrexia", "febrile illness", "hyperthermia"],
    "headache": ["headache", "cephalalgia", "head pain"],
    "pain": ["pain", "ache", "aching", "painful condition"],
    "inflammation": ["inflammation", "inflammatory condition"],
    "diabetes": ["diabetes mellitus", "diabetes"],
    "hypertension": ["hypertension", "high blood pressure", "htn"],
    "infection": ["infection", "bacterial infection", "viral infection"],
    "cold": ["upper respiratory infection", "common cold", "upper respiratory tract infection"],
    "flu": ["influenza", "flu"],
    "cough": ["cough", "productive cough", "dry cough"],
    "nausea": ["nausea", "vomiting", "emesis"],
    "rash": ["rash", "dermatitis", "skin eruption"],
    "allergy": ["allergic rhinitis", "allergy", "allergic reaction"],
    "insomnia": ["insomnia", "sleep disorder"],
    "anxiety": ["anxiety disorder", "generalized anxiety disorder"],
    "depression": ["major depressive disorder", "depression", "depressive disorder"],
    "asthma": ["asthma", "bronchial asthma"],
    "copd": ["chronic obstructive pulmonary disease", "copd"],
    "obesity": ["obesity", "overweight"],
    "gout": ["gout", "gouty arthritis", "hyperuricemia"],
    "acne": ["acne vulgaris", "acne"],
}


def translate_chinese_disease(chinese_name: str) -> List[str]:
    """中文疾病名 → 英文标准化名列表

    Args:
        chinese_name: 中文疾病名（如"发烧"、"高血压"）

    Returns:
        英文标准化名列表（如["fever", "pyrexia"]）
    """
    name = chinese_name.strip()
    if not name:
        return []

    # 直接匹配
    if name in CHINESE_TO_ENGLISH_DISEASE:
        return CHINESE_TO_ENGLISH_DISEASE[name]

    # 子串匹配（仅cn_key在name中的方向，且cn_key>=2字符）
    # 不使用name-in-cn_key方向（防止短输入如"风"匹配"痛风"）
    results = []
    for cn_key, en_values in CHINESE_TO_ENGLISH_DISEASE.items():
        if len(cn_key) >= 2 and cn_key in name:
            results.extend(en_values)

    return results


def expand_symptoms_to_diseases(symptom_str: str) -> List[str]:
    """症状 → 关联疾病名列表

    Args:
        symptom_str: 中文症状描述（如"头疼，发烧，想吐"）

    Returns:
        关联的英文疾病名列表
    """
    if not symptom_str:
        return []

    results = []
    # 分割症状（支持中文逗号、英文逗号、空格）
    symptoms = _split_input(symptom_str)

    for symptom in symptoms:
        symptom = symptom.strip()
        if not symptom:
            continue

        # 直接匹配
        if symptom in SYMPTOM_TO_DISEASE:
            results.extend(SYMPTOM_TO_DISEASE[symptom])
        else:
            # 子串匹配（仅s_key在symptom方向，且s_key>=2字符）
            # 不使用symptom-in-s_key方向（防止短输入如"痛"匹配大量疾病）
            for s_key, diseases in SYMPTOM_TO_DISEASE.items():
                if len(s_key) >= 2 and s_key in symptom:
                    results.extend(diseases)

    # 去重
    return list(set(results))


def expand_english_disease(english_name: str) -> List[str]:
    """英文疾病名扩充 → 更多相关英文名

    Args:
        english_name: 英文疾病名（如"fever"、"diabetes"）

    Returns:
        扩充后的英文名列表
    """
    name = english_name.strip().lower()
    if not name:
        return []

    # 直接匹配
    if name in ENGLISH_DISEASE_EXPAND:
        return ENGLISH_DISEASE_EXPAND[name]

    # 子串匹配
    results = []
    for en_key, en_values in ENGLISH_DISEASE_EXPAND.items():
        if en_key in name or name in en_key:
            results.extend(en_values)

    if results:
        return list(set(results))

    # 没有匹配时返回原始名
    return [name]


def _split_input(text: str) -> List[str]:
    """分割输入字符串（支持中英文逗号、顿号、空格、分号、斜杠）

    Args:
        text: 原始输入文本

    Returns:
        分割后的列表
    """
    import re
    # 支持: 中文逗号，英文逗号, 顿号、, 分号;, 空格, 斜杠/, 全角空格
    parts = re.split(r'[，,;；\s、/／\u3000]+', text)
    return [p.strip() for p in parts if p.strip()]


def process_patient_input(
    diseases_str: str,
    symptoms_str: str,
) -> Set[str]:
    """处理患者输入 → 综合英文疾病名集合

    综合考虑:
    1. 中文疾病名 → 英文
    2. 英文疾病名 → 扩充
    3. 中文症状 → 关联疾病

    Args:
        diseases_str: 疾病描述字符串（中英文混合）
        symptoms_str: 症状描述字符串（中文）

    Returns:
        英文标准化疾病名集合（用于适应症匹配）
    """
    result: Set[str] = set()

    # 1. 处理疾病
    if diseases_str:
        disease_parts = _split_input(diseases_str)
        for part in disease_parts:
            # 尝试中文→英文映射
            en_names = translate_chinese_disease(part)
            if en_names:
                result.update(en_names)
            else:
                # 可能是英文输入，做扩充
                expanded = expand_english_disease(part)
                result.update(expanded)

    # 2. 处理症状 → 关联疾病
    if symptoms_str:
        symptom_diseases = expand_symptoms_to_diseases(symptoms_str)
        result.update(symptom_diseases)

    return result
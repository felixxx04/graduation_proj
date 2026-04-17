# 数据充分性改进计划书（档位B）

> 项目：差分隐私保护的AI驱动个性化医疗用药推荐系统
> 日期：2026-04-17
> 目标档位：B（毕设推荐级）

---

## 一、目标指标

| 指标 | 当前值 | 目标值 | 差距 |
|------|--------|--------|------|
| 患者数 | 200 | 3,000 | 15× |
| 药物数（有分类） | 30（DB） + 0（OpenFDA） | 150 | 5× |
| 训练样本（有效） | 0 | 30,000-50,000 | ∞ |
| 疾病词汇 | 20（6个不匹配） | 60 | 3× |
| 过敏词汇 | 10（3个不匹配） | 25 | 2.5× |
| 药物类别 | 8 | 14 | 1.75× |
| 推荐记录 | 0 | 1,000 | ∞ |
| 特征有效率 | 27% | 100% | P0修复 |
| 标签信号质量 | 极差 | 良好 | P0修复 |
| FEATURE_DIM | 200 | 54→97（随词汇扩充调整） | 见P0-3 |

---

## 二、分阶段执行计划

### P0：止血（修复致命数据缺陷）

> 目标：让现有数据真正可用，消除全零特征和语言不匹配

---

#### P0-1 药物分类归一化

**问题**：142条OpenFDA药物 category 全为"其他"，8维one-hot中7维恒零

**涉及文件**：
- `medical-model/app/data/preprocessor.py` — 新增分类映射字典和分类函数
- `medical-model/app/main.py` — 启动时调用分类修正
- `medical-model/data/drugs_openfda.json` — 修正后回写

**实施步骤**：

1. 在 `preprocessor.py` 新增 `DRUG_NAME_TO_CATEGORY` 映射字典：

```python
DRUG_NAME_TO_CATEGORY = {
    # 降糖药
    '二甲双胍': '降糖药', '格列美脲': '降糖药', '胰岛素': '降糖药',
    '格列本脲': '降糖药', '阿卡波糖': '降糖药', '吡格列酮': '降糖药',
    '瑞格列奈': '降糖药', '利拉鲁肽': '降糖药', '西格列汀': '降糖药',
    # 降压药
    '氨氯地平': '降压药', '缬沙坦': '降压药', '硝苯地平': '降压药',
    '氯沙坦': '降压药', '依那普利': '降压药', '美托洛尔': '降压药',
    '卡托普利': '降压药', '培哚普利': '降压药', '厄贝沙坦': '降压药',
    '替米沙坦': '降压药', '非洛地平': '降压药', '比索洛尔': '降压药',
    # 降脂药
    '阿托伐他汀': '降脂药', '瑞舒伐他汀': '降脂药', '辛伐他汀': '降脂药',
    '普伐他汀': '降脂药', '氟伐他汀': '降脂药', '非诺贝特': '降脂药',
    # 抗血小板药
    '氯吡格雷': '抗血小板药', '阿司匹林': '抗血小板药', '替格瑞洛': '抗血小板药',
    # 抗凝药
    '华法林': '抗凝药', '利伐沙班': '抗凝药', '达比加群': '抗凝药',
    # 消化系统用药
    '奥美拉唑': '消化系统用药', '雷贝拉唑': '消化系统用药', '兰索拉唑': '消化系统用药',
    '泮托拉唑': '消化系统用药', '法莫替丁': '消化系统用药',
    # 心血管用药
    '地高辛': '心血管用药', '硝酸甘油': '心血管用药', '曲美他嗪': '心血管用药',
    # 抗感染药
    '阿莫西林': '抗感染药', '头孢': '抗感染药', '左氧氟沙星': '抗感染药',
    '莫西沙星': '抗感染药', '阿奇霉素': '抗感染药', '克拉霉素': '抗感染药',
    '甲硝唑': '抗感染药', '氟康唑': '抗感染药',
    # 呼吸系统用药
    '沙美特罗': '呼吸系统用药', '布地奈德': '呼吸系统用药', '沙丁胺醇': '呼吸系统用药',
    '孟鲁司特': '呼吸系统用药', '异丙托溴铵': '呼吸系统用药',
    # 抗抑郁药
    '舍曲林': '抗抑郁药', '帕罗西汀': '抗抑郁药', '西酞普兰': '抗抑郁药',
    '文拉法辛': '抗抑郁药', '氟西汀': '抗抑郁药',
    # 镇静催眠药
    '唑吡坦': '镇静催眠药', '艾司唑仑': '镇静催眠药', '地西泮': '镇静催眠药',
    # 甲状腺用药
    '左甲状腺素': '甲状腺用药', '甲巯咪唑': '甲状腺用药', '丙硫氧嘧啶': '甲状腺用药',
    # 抗骨质疏松药
    '阿仑膦酸钠': '抗骨质疏松药', '唑来膦酸': '抗骨质疏松药', '利塞膦酸钠': '抗骨质疏松药',
}
```

2. 新增 `classify_drug(drug: dict) -> str` 函数：

```python
def classify_drug(drug: dict) -> str:
    """根据药物名称和适应症推断分类"""
    name = drug.get('name', '')
    generic = drug.get('generic_name', '')
    category = drug.get('category', '')

    # 如果已有有效分类，直接返回
    if category and category in DRUG_CATEGORY_MAP and category != '其他':
        return category

    # 按名称匹配
    for key, cat in DRUG_NAME_TO_CATEGORY.items():
        if key in name or key in generic:
            return cat

    # 按适应症关键词匹配
    indications = drug.get('indications', '[]')
    if isinstance(indications, str):
        try:
            indications = json.loads(indications)
        except:
            indications = []
    ind_text = ' '.join(str(i) for i in indications)

    INDICATION_KEYWORDS = {
        '降糖药': ['糖尿病', '血糖', '胰岛素', 'diabetes', 'glucose', 'insulin'],
        '降压药': ['高血压', '血压', 'hypertension', 'blood pressure'],
        '降脂药': ['高脂', '胆固醇', '血脂', 'cholesterol', 'lipid', 'statin'],
        '抗血小板药': ['血小板', '血栓', 'platelet', 'thromb', 'antiplatelet'],
        '抗凝药': ['凝血', '抗凝', 'anticoagul', 'warfarin'],
        '消化系统用药': ['溃疡', '胃酸', '反流', 'ulcer', 'gastric', 'reflux'],
        '心血管用药': ['心衰', '心律', '心绞痛', 'heart failure', 'arrhythm'],
        '抗感染药': ['感染', '细菌', 'infect', 'bacteri', 'antibiot'],
        '呼吸系统用药': ['哮喘', '慢阻肺', '呼吸', 'asthma', 'COPD', 'bronch'],
        '抗抑郁药': ['抑郁', '焦虑', 'depress', 'anxiety'],
        '镇静催眠药': ['失眠', '镇静', 'insomnia', 'sedative'],
        '甲状腺用药': ['甲状腺', '甲亢', '甲减', 'thyroid'],
        '抗骨质疏松药': ['骨质疏松', 'osteoporos', 'bone density'],
    }

    for cat, keywords in INDICATION_KEYWORDS.items():
        for kw in keywords:
            if kw in ind_text:
                return cat

    return '其他'
```

3. 在 `main.py` 启动加载药物后，遍历修正分类：

```python
# 在 startup() 函数中，drug_data 加载后添加：
for drug in drugs_data:
    drug['category'] = classify_drug(drug)
```

4. 编写一次性脚本 `scripts/fix_drug_categories.py`，运行后回写 `drugs_openfda.json`

**验证标准**：
- 142条药物中"其他"占比 < 30%（即 > 100条有有效分类）
- 每个8类别至少有5条药物

**预计工作量**：1天

---

#### P0-2 禁忌症/副作用中文化

**问题**：禁忌症全为英文FDA原文，中文疾病名匹配命中率为0%

**涉及文件**：
- `medical-model/app/data/preprocessor.py` — 新增映射字典和翻译函数
- `medical-model/scripts/generate_training_data.py` — 标签计算使用翻译后的中文
- `medical-model/app/services/predictor.py` — 预测特征构造使用翻译后的中文

**实施步骤**：

1. 在 `preprocessor.py` 新增 `CONTRAINDICATION_CN_MAP`：

```python
CONTRAINDICATION_CN_MAP = {
    # 心血管
    'hypertension': '高血压', 'high blood pressure': '高血压',
    'heart failure': '心衰', 'cardiac failure': '心衰',
    'arrhythmia': '心律失常', 'atrial fibrillation': '房颤',
    'coronary artery': '冠心病', 'myocardial infarction': '冠心病',
    # 内分泌
    'diabetes': '糖尿病', 'diabetic': '糖尿病',
    'hypoglycemia': '低血糖', 'hyperthyroidism': '甲亢',
    'hypothyroidism': '甲减', 'thyroid': '甲状腺疾病',
    # 肾脏
    'renal': '慢性肾病', 'kidney': '慢性肾病', 'nephro': '慢性肾病',
    'dialysis': '慢性肾病',
    # 肝脏
    'hepatic': '肝炎', 'liver': '肝炎', 'hepat': '肝炎',
    # 消化
    'ulcer': '胃溃疡', 'gastric': '胃溃疡', 'peptic': '胃溃疡',
    'gastrointestinal bleeding': '胃溃疡',
    # 呼吸
    'asthma': '哮喘', 'bronchospasm': '哮喘', 'COPD': '慢阻肺',
    # 神经
    'seizure': '癫痫', 'epilepsy': '癫痫', 'convulsion': '癫痫',
    'parkinson': '帕金森', 'stroke': '脑梗塞',
    # 血液
    'bleeding': '贫血', 'coagulation': '贫血', 'thrombocytopenia': '贫血',
    # 骨骼
    'osteoporosis': '骨质疏松',
    # 其他
    'pregnancy': None,  # 不映射到疾病词汇
    'lactation': None,
    'pediatric': None,
    'hypersensitivity': '其他',
    'anemia': '贫血', 'gout': '痛风',
    'depression': '抑郁症', 'suicidal': '抑郁症',
}
```

2. 新增 `translate_contraindications(contra_list: List[str]) -> List[str]` 函数：

```python
def translate_contraindications(contra_list: List[str]) -> List[str]:
    """将英文禁忌症文本翻译为中文疾病名列表"""
    result = []
    for text in contra_list:
        text_lower = text.lower()
        for en_key, cn_val in CONTRAINDICATION_CN_MAP.items():
            if cn_val is None:  # 跳过不映射的项
                continue
            if en_key in text_lower:
                if cn_val not in result:
                    result.append(cn_val)
    return result
```

3. 修改 `generate_training_data.py` 的 `create_label()` 函数（约第284行）：

```python
# 修改前：
for disease in diseases:
    for contra in contraindications:
        if disease in contra or contra in disease:
            label -= 0.5

# 修改后：
cn_contraindications = translate_contraindications(contraindications)
for disease in diseases:
    for contra in cn_contraindications:
        if disease in contra or contra in disease:
            label -= 0.5
```

4. 同步修改 `predictor.py` 的 `_create_drug_patient_features()` 中的冲突计算逻辑

**验证标准**：
- 142条药物中禁忌症可翻译为中文的比例 > 70%
- 标签分布：推荐(label>0.6)、中性(0.3-0.6)、不推荐(<0.3) 三段均有样本
- 禁忌冲突检出率从 ≈0% 提升到 > 50%

**预计工作量**：1.5天

---

#### P0-3 消除特征噪声维度

**问题**：200维中146维为随机噪声（训练）或零（预测），73%特征无效

**涉及文件**：
- `medical-model/app/data/preprocessor.py` — `FEATURE_DIM = 54`（暂定，P2词汇扩充后调整）
- `medical-model/app/config.py` — `feature_dim = 54`
- `medical-model/app/services/trainer.py` — 3处 `feature_dim=200`
- `medical-model/app/services/predictor.py` — 2处 `FEATURE_DIM` 引用
- `medical-model/app/main.py` — `field_dims=[200]`
- `medical-model/scripts/generate_training_data.py` — 去掉噪声填充

**实施步骤**：

1. 修改 `preprocessor.py` 第33行：`FEATURE_DIM = 54`

2. 修改 `generate_training_data.py` 的 `create_feature_vector()`：
   - 删除 idx >= 54 后的随机噪声填充代码
   - 向量在 idx=54 处截断

3. 修改 `predictor.py`：
   - `_create_patient_features()` 返回长度42的向量（到current_medications为止）
   - `_create_drug_patient_features()` 返回长度54的向量
   - 确保无零填充尾部

4. 修改 `main.py` 模型加载：
   - `field_dims=[200]` → `field_dims=[8, 2, 1, 20, 10, 10, 8, 1, 1, 1]`
   - 或保持 `field_dims=[54]`（单字段模式，FM退化为全连接交互）

5. 删除旧模型文件 `saved_models/deepfm_trained.pt`（维度不兼容）

6. 更新 `get_field_dims()` 返回值与实际字段对应

**验证标准**：
- 生成的特征向量 shape == (54,)
- 向量中无非零填充段（idx 0-53 全部有意义）
- 训练和预测对同一输入产生完全一致的特征向量

**预计工作量**：1天

---

### P1：对齐（消除训练/预测不一致）

---

#### P1-1 修复BMI计算

**问题**：训练时BMI从数据库计算，预测时硬编码0.55

**涉及文件**：
- `medical-model/app/services/predictor.py` — 第124行附近

**实施步骤**：

1. 修改 `_create_patient_features()` 第124行：

```python
# 修改前：
features[2] = 0.55  # BMI placeholder

# 修改后：
height = patient.get('height', 170)  # cm
weight = patient.get('weight', 65)   # kg
height_m = float(height) / 100.0
if height_m > 0:
    bmi = float(weight) / (height_m * height_m)
    features[2] = min(bmi / 40.0, 1.5)
else:
    features[2] = 0.55  # fallback
```

2. 确保前端传递患者信息时包含 height 和 weight 字段

**验证标准**：训练和预测中同一患者的BMI特征值偏差 < 0.05

**预计工作量**：0.5天

---

#### P1-2 统一特征构造逻辑

**问题**：`generate_training_data.py` 和 `predictor.py` 各自实现特征构造，存在漂移

**涉及文件**：
- `medical-model/app/data/preprocessor.py` — 扩展 PatientFeatureProcessor
- `medical-model/scripts/generate_training_data.py` — 委托调用
- `medical-model/app/services/predictor.py` — 委托调用

**实施步骤**：

1. 在 `PatientFeatureProcessor` 中新增方法：

```python
def create_patient_drug_features(self, patient: dict, drug: dict) -> np.ndarray:
    """构建完整的患者-药物特征向量（54维）"""
    features = np.zeros(FEATURE_DIM)

    # 患者特征
    # age
    age = float(patient.get('age', 50))
    features[0] = min(age / 100.0, 1.5)

    # gender
    features[1] = 1.0 if patient.get('gender') in ('男', 'MALE', 'male') else 0.0

    # BMI
    height = float(patient.get('height', 170))
    weight = float(patient.get('weight', 65))
    height_m = height / 100.0
    if height_m > 0:
        bmi = weight / (height_m * height_m)
        features[2] = min(bmi / 40.0, 1.5)
    else:
        features[2] = 0.55

    # diseases one-hot
    diseases = _safe_parse_json_list(patient.get('chronic_diseases'))
    idx = 3
    for disease in diseases:
        if disease in self.disease_vocab_dict:
            features[idx + self.disease_vocab_dict[disease]] = 1.0
        else:
            features[idx + self.disease_vocab_dict.get('其他', len(self.disease_vocab_dict) - 1)] = 1.0

    # allergies one-hot
    idx = 3 + len(DISEASE_VOCAB)
    allergies = _safe_parse_json_list(patient.get('allergies'))
    for allergy in allergies:
        if allergy in self.allergy_vocab_dict:
            features[idx + self.allergy_vocab_dict[allergy]] = 1.0
        else:
            features[idx + self.allergy_vocab_dict.get('其他', len(self.allergy_vocab_dict) - 1)] = 1.0

    # current medications (placeholder)
    idx = 3 + len(DISEASE_VOCAB) + len(ALLERGY_VOCAB)
    # 保留10维零占位

    # 药物特征
    idx = 3 + len(DISEASE_VOCAB) + len(ALLERGY_VOCAB) + 10

    # drug category one-hot
    category = classify_drug(drug)
    if category in DRUG_CATEGORY_MAP:
        features[idx + DRUG_CATEGORY_MAP[category]] = 1.0
    else:
        features[idx + DRUG_CATEGORY_MAP['其他']] = 1.0

    idx += len(DRUG_CATEGORY_MAP)

    # match/conflict scores
    cn_contraindications = translate_contraindications(
        _safe_parse_json_list(drug.get('contraindications'))
    )
    features[idx] = self._compute_match_score(diseases, drug)
    features[idx + 1] = self._compute_contra_score(diseases, cn_contraindications)
    features[idx + 2] = self._compute_allergy_score(allergies, drug)

    return features
```

2. `generate_training_data.py` 的 `create_feature_vector()` 改为调用此方法
3. `predictor.py` 的 `_create_drug_patient_features()` 改为调用此方法
4. 删除两处重复代码

**验证标准**：对10个随机 (patient, drug) 对，新旧实现输出完全一致

**预计工作量**：1天

---

#### P1-3 修正 field_dims 传入方式

**问题**：`field_dims=[200]`，FM层无法区分字段边界

**涉及文件**：
- `medical-model/app/main.py`
- `medical-model/app/data/preprocessor.py`

**实施步骤**：

1. 修改 `get_field_dims()` 返回实际字段维度列表：

```python
def get_field_dims() -> List[int]:
    """返回每个字段的维度列表，用于DeepFM初始化"""
    return [
        1,          # age (连续值)
        1,          # gender (连续值)
        1,          # BMI (连续值)
        len(DISEASE_VOCAB),    # diseases one-hot
        len(ALLERGY_VOCAB),    # allergies one-hot
        10,         # current_medications placeholder
        len(DRUG_CATEGORY_MAP),  # drug category one-hot
        1,          # match_score
        1,          # contra_score
        1,          # allergy_score
    ]
```

2. 修改 `main.py` 所有 `field_dims=[200]` 为 `field_dims=get_field_dims()`
3. 确认 `DeepFM.__init__` 的 `input_dim = sum(field_dims)` 仍等于 `FEATURE_DIM`

**验证标准**：模型初始化成功，FM层嵌入维度正确

**预计工作量**：0.5天

---

### P2：扩充（增加数据量和词汇覆盖）

---

#### P2-1 修正并扩充疾病词汇表

**当前问题**：
- 词汇表有20个疾病，但数据中6种疾病名与词汇表不一致
  - 数据中"2型糖尿病" vs 词汇表"糖尿病"
  - 数据中"高脂血症" vs 词汇表"高血脂"
  - 数据中"COPD" vs 词汇表"哮喘"
  - 数据中"脑卒中后遗症" vs 词汇表"脑梗塞"
  - 数据中"心力衰竭" vs 词汇表"心衰"
  - 数据中"甲状腺功能减退" vs 词汇表"甲状腺疾病"

**实施步骤**：

1. 先在 `preprocessor.py` 中添加疾病别名映射：

```python
DISEASE_ALIAS_MAP = {
    '2型糖尿病': '糖尿病',
    '1型糖尿病': '糖尿病',
    '高脂血症': '高血脂',
    '血脂异常': '高血脂',
    'COPD': '哮喘',           # 慢阻肺归入呼吸系统
    '慢阻肺': '哮喘',
    '脑卒中后遗症': '脑梗塞',
    '脑卒中': '脑梗塞',
    '中风': '脑梗塞',
    '心力衰竭': '心衰',
    '甲状腺功能减退': '甲状腺疾病',
    '甲减': '甲状腺疾病',
    '甲亢': '甲状腺疾病',
    '甲状腺结节': '甲状腺疾病',
    '脂肪肝': '肝炎',
    '慢性胃炎': '胃溃疡',
}
```

2. 扩充 `DISEASE_VOCAB` 从20到60：

```python
DISEASE_VOCAB = [
    # 原有（20个）
    '高血压', '糖尿病', '冠心病', '高血脂', '哮喘',
    '慢性肾病', '肝炎', '胃溃疡', '关节炎', '抑郁症',
    '甲状腺疾病', '贫血', '痛风', '骨质疏松', '心衰',
    '脑梗塞', '帕金森', '癫痫', '肿瘤', '其他',
    # 新增（40个）
    # 呼吸系统
    '慢阻肺', '肺心病', '肺炎', '支气管扩张',
    # 消化系统
    '肝硬化', '胆囊炎', '胰腺炎', '肠易激综合征',
    # 心血管
    '房颤', '心律失常', '主动脉瓣狭窄', '外周动脉疾病',
    # 内分泌
    '代谢综合征',
    # 神经
    '偏头痛', '重症肌无力', '多发性硬化',
    # 肾脏
    '肾结石', '肾衰竭', '肾病综合征',
    # 血液
    '深静脉血栓', '血小板减少症',
    # 精神
    '焦虑症', '双相障碍', '失眠症',
    # 肿瘤
    '肺癌', '乳腺癌', '结直肠癌', '前列腺癌', '胃癌',
    # 风湿
    '类风湿关节炎', '系统性红斑狼疮', '强直性脊柱炎',
    # 眼科
    '青光眼', '白内障',
    # 耳鼻喉
    '过敏性鼻炎',
    # 其他
    '尿路感染', '前列腺增生', '腰椎间盘突出', '银屑病',
]
```

3. 同步更新 `FEATURE_DIM` 和 `get_field_dims()`

**验证标准**：患者数据中所有疾病均能映射到词汇表

**预计工作量**：1天

---

#### P2-2 扩充过敏词汇表

**当前问题**：词汇表10个，数据中3种不匹配
- 数据中"头孢菌素" vs 词汇表"头孢类"
- 数据中"海鲜"不在词汇表
- 数据中"花粉"不在词汇表

**实施步骤**：

1. 先添加过敏别名映射：

```python
ALLERGY_ALIAS_MAP = {
    '头孢菌素': '头孢类',
    '头孢': '头孢类',
    '磺胺': '磺胺类',
}
```

2. 扩充 `ALLERGY_VOCAB` 从10到25：

```python
ALLERGY_VOCAB = [
    # 原有（10个）
    '青霉素', '磺胺类', '阿司匹林', '碘造影剂', '头孢类',
    '链霉素', '万古霉素', '喹诺酮类', '四环素类', '其他',
    # 新增（15个）
    '大环内酯类', '氨基糖苷类', '硝基咪唑类', '抗真菌药',
    '非甾体抗炎药', '麻醉药', '碘', '乳胶',
    '海鲜', '花粉', '尘螨', '坚果',
    '磺脲类', '华法林',
]
```

3. 同步更新 `FEATURE_DIM` 和 `get_field_dims()`

**验证标准**：患者数据中所有过敏均能映射到词汇表

**预计工作量**：0.5天

---

#### P2-3 扩充药物类别映射

**当前**：8个 → **目标**：14个

**实施步骤**：

1. 扩充 `DRUG_CATEGORY_MAP`：

```python
DRUG_CATEGORY_MAP = {
    '降糖药': 0, '降压药': 1, '降脂药': 2, '抗血小板药': 3,
    '消化系统用药': 4, '心血管用药': 5, '抗感染药': 6,
    '呼吸系统用药': 7, '抗抑郁药': 8, '镇静催眠药': 9,
    '甲状腺用药': 10, '抗骨质疏松药': 11, '抗凝药': 12,
    '其他': 13,
}
```

2. 同步更新 `FEATURE_DIM` 和 `get_field_dims()`

**验证标准**：数据库17个药物类别中14个可直接映射，3个归入"其他"

**预计工作量**：0.5天

---

#### P2-4 合并数据库药物到模型服务

**问题**：数据库30条高质量中文药物未被模型服务加载

**涉及文件**：
- `medical-model/app/data_sources/db_adapter.py` — 新增
- `medical-model/app/main.py` — 启动时合并

**实施步骤**：

1. 新增 `db_adapter.py`：

```python
"""从MySQL数据库加载药物数据"""
import pymysql
from app.config import settings

def fetch_drugs_from_db() -> list:
    """从medical_recommendation.drug表读取药物"""
    conn = pymysql.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
        charset='utf8mb4'
    )
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SELECT * FROM drug")
            return cursor.fetchall()
    finally:
        conn.close()
```

2. 修改 `main.py` 启动逻辑：

```python
# 先加载OpenFDA数据
with open(DRUGS_DATA_FILE, 'r', encoding='utf-8') as f:
    drugs_data = json.load(f)

# 修正分类
for drug in drugs_data:
    drug['category'] = classify_drug(drug)

# 从数据库加载并合并
try:
    db_drugs = fetch_drugs_from_db()
    db_names = {d.get('generic_name', '') or d.get('name', '') for d in db_drugs}

    for db_drug in db_drugs:
        # 如果数据库药物不在OpenFDA列表中，添加
        generic = db_drug.get('generic_name', '') or db_drug.get('name', '')
        if not any(generic in (d.get('generic_name', '') or d.get('name', ''))
                   for d in drugs_data):
            drugs_data.append({
                'drug_code': db_drug.get('drug_code', ''),
                'name': db_drug.get('name', ''),
                'generic_name': db_drug.get('generic_name', ''),
                'category': db_drug.get('category', '其他'),
                'indications': db_drug.get('indications', '[]'),
                'contraindications': db_drug.get('contraindications', '[]'),
                'side_effects': db_drug.get('side_effects', '[]'),
                'interactions': db_drug.get('interactions', '[]'),
                'typical_dosage': db_drug.get('typical_dosage', ''),
                'typical_frequency': db_drug.get('typical_frequency', ''),
                'description': db_drug.get('description', ''),
            })

    logger.info(f"合并后药物总数: {len(drugs_data)} (OpenFDA + DB)")
except Exception as e:
    logger.warning(f"数据库药物加载失败: {e}，仅使用OpenFDA数据")
```

**验证标准**：合并后药物总数 > 150条，每个类别至少5条

**预计工作量**：1天

---

#### P2-5 扩充患者数据至3,000条

**当前**：200条 → **目标**：3,000条

**涉及文件**：
- `medical-backend/sql/patient_data_extended.sql` — 新增

**生成策略**：

```python
# 合成患者数据生成规则
AGE_DISTRIBUTION = {
    '30-40': 0.15,  # 450人
    '40-50': 0.25,  # 750人
    '50-60': 0.30,  # 900人
    '60-70': 0.20,  # 600人
    '70-85': 0.10,  # 300人
}
GENDER_RATIO = {'MALE': 0.55, 'FEMALE': 0.45}

# 疾病组合规则（按年龄权重）
DISEASE_BY_AGE = {
    '30-40': 1-2种，以高血压、胃炎为主
    '40-50': 1-3种，高血压+糖尿病开始出现
    '50-60': 2-4种，心血管代谢疾病高发
    '60-70': 2-5种，多病共存常见
    '70-85': 3-6种，多重慢性病
}

# 疾病关联规则（共病组合）
COMORBIDITY_PAIRS = [
    ('高血压', '糖尿病', 0.3),      # 30%高血压患者同时有糖尿病
    ('高血压', '高血脂', 0.4),      # 40%高血压患者同时有高血脂
    ('糖尿病', '高血脂', 0.35),
    ('冠心病', '高血压', 0.6),
    ('心衰', '冠心病', 0.5),
    ('脑梗塞', '高血压', 0.7),
    ('骨质疏松', '关节炎', 0.3),
]

# 过敏分布
ALLERGY_RATE = 0.25  # 25%患者有过敏
```

**编写SQL生成脚本** `scripts/generate_patients.py`：
- 输出 INSERT 语句到 `patient_data_extended.sql`
- 患者数据标注 `is_synthetic = TRUE`（新增字段）
- 健康档案按规则关联疾病、过敏、当前用药

**验证标准**：
- 总患者数 = 3,000
- 每个年龄组数量与分布一致
- 疾病/过敏/用药分布符合医学共病规律
- 所有疾病和过敏值均在词汇表中

**预计工作量**：1.5天

---

#### P2-6 缩减模型匹配数据量

**问题**：DeepFM参数~50,000+ vs 训练样本不足

**方案**：P2-5扩充后训练样本 ≈ 3000×150 = 450,000对，过滤后约100,000-150,000有效样本

**模型调整**：

```python
# 当前
embed_dim = 16
hidden_dims = [128, 64, 32]
dropout = 0.2

# 调整后
embed_dim = 8       # 减半，防过拟合
hidden_dims = [64, 32]  # 减少一层和宽度
dropout = 0.3       # 增加正则化
```

**参数量对比**：
- 调整前：~50,000参数，样本/参数比 ≈ 0.12
- 调整后：~12,000参数，样本/参数比 ≈ 8-12

**涉及文件**：
- `medical-model/app/models/deepfm.py` — 默认超参数
- `medical-model/app/services/trainer.py` — TrainingConfig 默认值

**验证标准**：训练集loss稳定下降，验证集loss不过拟合

**预计工作量**：0.5天

---

#### P2-7 重新计算 FEATURE_DIM

P2-1~P2-3 词汇扩充后，特征维度需重新计算：

```
特征布局：
  age:              1  (连续值)
  gender:           1  (连续值)
  BMI:              1  (连续值)
  diseases_onehot: 60  (DISEASE_VOCAB长度)
  allergies_onehot:25  (ALLERGY_VOCAB长度)
  current_meds:    10  (占位)
  drug_category:   14  (DRUG_CATEGORY_MAP长度)
  match_score:      1
  contra_score:     1
  allergy_score:    1
─────────────────────
  FEATURE_DIM = 115
```

`get_field_dims()` 返回：`[1, 1, 1, 60, 25, 10, 14, 1, 1, 1]`

**涉及文件**：所有引用 `FEATURE_DIM` 的文件同步修改

**预计工作量**：包含在P2-1~P2-3中

---

### P3：验证（构建评估闭环）

---

#### P3-1 生成推荐历史基线

**问题**：recommendation表0条记录

**实施步骤**：

1. 编写脚本 `scripts/generate_recommendation_baseline.py`
2. 对3000个患者，按疾病-适应症匹配选出Top-5推荐
3. 应用差分隐私噪声后插入 recommendation 表
4. 同时更新 privacy_ledger 表记录隐私预算消耗

**验证标准**：recommendation表 ≥ 1,000条记录

**预计工作量**：1天

---

#### P3-2 构建评估数据集

**实施步骤**：

1. 从患者×药物对中随机抽取500对
2. 基于规则自动标注（适应症/禁忌症/过敏）
3. 人工审核其中100对，校验规则标签合理性
4. 划分：训练80% / 验证10% / 测试10%
5. 保存为 `data/eval_dataset.json`

**评估数据格式**：
```json
{
    "patient_id": "P001",
    "drug_code": "D001",
    "features": [...],
    "rule_label": 0.8,
    "human_label": null,  // 填入后为人工标注
    "split": "train"
}
```

**验证标准**：测试集 ≥ 50对，含推荐/中性/不推荐三类

**预计工作量**：1.5天

---

#### P3-3 添加模型评估指标

**涉及文件**：
- `medical-model/app/services/trainer.py` — 训练过程记录指标

**新增指标**：
- AUC-ROC（主要指标）
- Log Loss
- Precision@5 / Recall@5
- DDI Rate（药物相互作用率，安全指标）

**输出格式**：
```python
training_report = {
    'epochs': 50,
    'final_train_loss': 0.234,
    'final_val_loss': 0.289,
    'auc_roc': 0.82,
    'precision_at_5': 0.71,
    'recall_at_5': 0.65,
    'ddi_rate': 0.03,
    'dp_epsilon_spent': 2.34,
}
```

**验证标准**：训练完成后自动输出评估报告

**预计工作量**：1天

---

## 三、执行时间线

```
Week 1: P0（止血）
  Day 1-2: P0-1 药物分类归一化
  Day 2-3: P0-2 禁忌症中文化
  Day 3-4: P0-3 消除特征噪声维度
  Day 4-5: 集成测试，验证特征一致性

Week 2: P1（对齐）+ P2 词汇扩充
  Day 1:   P1-1 修复BMI + P1-3 修正field_dims
  Day 1-2: P1-2 统一特征构造逻辑
  Day 2-3: P2-1 疾病词汇扩充
  Day 3:   P2-2 过敏词汇扩充 + P2-3 药物类别扩充
  Day 3-4: P2-7 FEATURE_DIM 重新计算 + 全量测试
  Day 4-5: P2-4 合并数据库药物

Week 3: P2 数据扩充 + 模型调整
  Day 1-2: P2-5 生成3000条合成患者数据
  Day 2-3: 导入数据库 + 生成训练数据
  Day 3:   P2-6 模型缩配 + 训练
  Day 3-5: 训练调优 + 差分隐私参数验证

Week 4: P3（验证）
  Day 1-2: P3-1 推荐历史基线
  Day 2-3: P3-2 评估数据集构建
  Day 3-5: P3-3 评估指标 + 全流程回归测试 + 文档更新
```

---

## 四、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| P0-3 改维度后旧模型不可用 | 必须重新训练 | 删除旧模型，确保训练流程畅通 |
| P0-2 英中翻译不完整 | 部分禁忌症仍无法匹配 | 允许部分保留空，优于错误映射 |
| P2-5 合成患者数据不代表真实分布 | 模型泛化能力受限 | 标注is_synthetic，后续可替换真实数据 |
| P2-6 模型缩配可能欠拟合 | AUC偏低 | 保留原超参数为配置选项 |
| P1-2 统一特征构造引入回归 | 训练/预测结果变化 | 先写测试对比新旧输出 |
| 数据库连接配置缺失 | P2-4合并失败 | 添加config.py中的DB连接配置 |

---

## 五、验收标准

### 档位B达标的量化指标

| 指标 | 达标值 | 验证方式 |
|------|--------|---------|
| 患者数 | ≥ 3,000 | `SELECT COUNT(*) FROM patient` |
| 药物数（有分类） | ≥ 150 | 统计 drugs_data 中非"其他"分类数 |
| 训练样本 | ≥ 30,000 | `len(training_data.json)` |
| 疾病词汇覆盖 | 60 | `len(DISEASE_VOCAB)` |
| 过敏词汇覆盖 | 25 | `len(ALLERGY_VOCAB)` |
| 特征有效率 | 100% | 特征向量无非零填充段 |
| 标签分布 | 三段均有>10% | 推荐/中性/不推荐各>10% |
| 推荐/评估记录 | ≥ 1,000 | `SELECT COUNT(*) FROM recommendation` |
| 模型AUC | > 0.7 | 测试集评估 |
| 样本/参数比 | > 5 | 训练样本数/模型参数数 |

---

## 六、文件修改清单

### 修改文件

| 文件 | 修改内容 | 阶段 |
|------|---------|------|
| `medical-model/app/data/preprocessor.py` | 词汇表扩充、分类映射、翻译函数、特征统一 | P0+P1+P2 |
| `medical-model/app/main.py` | 启动逻辑、field_dims、药物合并 | P0+P1+P2 |
| `medical-model/app/config.py` | feature_dim 更新 | P0+P2 |
| `medical-model/app/models/deepfm.py` | 默认超参数调整 | P2 |
| `medical-model/app/services/trainer.py` | feature_dim、评估指标 | P0+P3 |
| `medical-model/app/services/predictor.py` | BMI修复、特征统一 | P1 |
| `medical-model/scripts/generate_training_data.py` | 噪声去除、特征统一 | P0+P1 |

### 新增文件

| 文件 | 内容 | 阶段 |
|------|------|------|
| `medical-model/app/data_sources/db_adapter.py` | 数据库药物加载 | P2 |
| `medical-model/scripts/fix_drug_categories.py` | 一次性分类修正脚本 | P0 |
| `medical-model/scripts/generate_patients.py` | 合成患者数据生成 | P2 |
| `medical-model/scripts/generate_recommendation_baseline.py` | 推荐基线生成 | P3 |
| `medical-backend/sql/patient_data_extended.sql` | 扩充患者数据 | P2 |
| `medical-model/data/eval_dataset.json` | 评估数据集 | P3 |

### 删除文件

| 文件 | 原因 | 阶段 |
|------|------|------|
| `medical-model/saved_models/deepfm_trained.pt` | 维度不兼容 | P0 |

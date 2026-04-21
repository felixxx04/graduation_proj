# 数据训练与功能扩展方案

> 记录日期：2026-04-22
> 状态：方案已确定，待执行

---

## 一、老师要求的毕设功能扩展

### 1.1 核心需求

系统需要记住患者的慢性病（长期病），推荐药物时自动避开禁忌药物。

**具体要求**：
1. 从患者历史处方推断慢性病
2. 推荐时基于患者慢性病过滤禁忌药物
3. 前后端都需要支持
4. **必须通过数据训练实现，不能使用硬编码方式**
5. 系统功能是用药推荐，必须覆盖所有用药场景，不能只覆盖慢性病

### 1.2 当前系统问题

| 问题 | 现状 |
|------|------|
| 禁忌处理 | 仅用 substring matching 生成 `conflict_score`（单一标量），无硬过滤 |
| 特征向量 | 200维单字段 `[200]`，FM无法学习有效的交叉特征 |
| 训练数据 | 使用合成随机数据，无真实禁忌信号 |
| 疾病词汇表 | Python DISEASE_VOCAB (20项) 与数据库疾病字符串不一致 |
| 过敏处理 | 同样是 substring matching，无硬过滤 |

---

## 二、数据训练方案

### 2.1 数据集选择

**选定数据集**：Kaggle Medical Knowledge Graph Data
- URL: https://www.kaggle.com/datasets/hwwang98/medical-knowledge-graph-data
- 内容：8,807 种疾病、3,828 种药物、中文知识图谱

| 关系类型 | 数量 | 说明 |
|----------|------|------|
| recommand_drug | 59,467 | 疾病→推荐用药 |
| common_drug | 14,649 | 疾病→常用药物 |
| acompany_with | 12,029 | 疾病→伴随疾病（共病） |
| has_symptom | 5,998 | 疾病→症状 |

**关键限制**：数据集没有直接的"禁忌"关系字段，需通过反向排除推导。

### 2.2 禁忌推导策略——反向排除法

1. **构建药物-适应症映射**：从 `recommand_drug` + `common_drug` 合并，得到每个药物对应的适应症集合
2. **正样本**：知识图谱中的 recommand_drug 和 common_drug 关系即为正样本（药物适合该疾病）
3. **负样本**：对每个疾病D，排除其推荐/常用药物后，从剩余药物中随机采样，标记为负样本（药物不适合该疾病）
4. **禁忌推导规则**：
   - 规则1：药物A不属于疾病D的推荐/常用药物，且药物A的适应症与D的伴随疾病有交集 → 潜在禁忌
   - 规则2：从训练后的 DeepFM 模型预测中，对每个疾病计算所有药物的适配分数，分数低于阈值(0.3)的药物标记为禁忌

### 2.3 训练数据构建

#### 正样本

```
正样本来源 = recommand_drug(59,467) + common_drug(14,649) = 74,116 条
每条记录：(疾病ID, 药物ID, label=1)
```

#### 负样本

```
对每个疾病，从 3,828 种药物中排除其推荐/常用药物后，随机采样
负样本数量 ≈ 正样本 × 2 ≈ 148,000 条
每条记录：(疾病ID, 药物ID, label=0)
```

#### 特征编码

| 特征组 | 维度 | 说明 |
|--------|------|------|
| 疾病嵌入 | 128 | 疾病ID Embedding |
| 药物嵌入 | 128 | 药物ID Embedding |
| 疾病类别 | 16 | 疾病所属科室/系统 one-hot |
| 药物类别 | 16 | 药物分类 one-hot |
| 共病特征 | 32 | 伴随疾病嵌入平均 |
| 症状特征 | 32 | 疾病症状嵌入平均 |
| **总维度** | **352** | |

#### 训练数据 JSON 格式

```json
{
  "disease_id": 12345,
  "disease_name": "高血压",
  "drug_id": 678,
  "drug_name": "硝苯地平",
  "label": 1,
  "disease_category": [0,0,1,0,...,0],
  "drug_category": [0,1,0,0,...,0],
  "comorbidity_emb_avg": [0.12, -0.34, ...],
  "symptom_emb_avg": [0.56, 0.78, ...]
}
```

### 2.4 DeepFM 模型重构

#### 多字段 FM 结构

```python
# 当前: field_dims = [200]  (单字段，FM无法学习交叉特征)
# 重构后:
field_dims = [8807, 3828, 16, 16, 32, 32]  # 6个字段
# 疾病ID, 药物ID, 疾病类别, 药物类别, 共病嵌入桶, 症状嵌入桶
embedding_dim = 16
```

#### 禁忌感知损失函数

```python
def contraindication_aware_loss(y_pred, y_true, is_contraindicated):
    bce = F.binary_cross_entropy(y_pred, y_true, reduction='none')
    # 禁忌惩罚：对禁忌药物的高预测分数施加额外惩罚
    contra_penalty = is_contraindicated * y_pred * LAMBDA_CONTRA
    return (bce + contra_penalty).mean()

LAMBDA_CONTRA = 2.0  # 禁忌惩罚强度
```

#### 训练流程

```
1. 加载知识图谱 CSV → 解析 nodes 和 edges
2. 构建 药物→疾病 正向映射 + 疾病→药物 反向映射
3. 生成正样本 (label=1) + 负样本 (label=0)
4. 预计算共病嵌入和症状嵌入
5. 训练 DeepFM：80% 训练 + 20% 验证
6. 导出禁忌规则表：对每个疾病预测所有药物分数，<0.3 标记禁忌
7. 保存模型 + ID映射表 + 禁忌规则表
```

---

## 三、推理服务改造

### 3.1 禁忌规则表

训练完成后导出，用于硬过滤兜底：

```python
contraindication_map = {
    "高血压": ["肾上腺素", "麻黄碱", ...],
    "糖尿病": ["葡萄糖注射液", ...],
    ...
}
# 来源：模型预测(分数<0.3) + 规则推导(适应症冲突)
```

### 3.2 慢性病推断

```python
def infer_chronic_diseases(medication_history: list[str]) -> list[str]:
    # 利用知识图谱 recommand_drug 反向映射
    # 药物→疾病 反向索引
    drug_to_diseases = {}  # 从 knowledge graph 构建
    for rel in recommand_drug + common_drug:
        drug_to_diseases[rel.drug].append(rel.disease)

    # 统计患者历史处方中各疾病出现频率
    disease_counter = Counter()
    for drug in medication_history:
        if drug in drug_to_diseases:
            disease_counter.update(drug_to_diseases[drug])

    # 出现 >= 2 次的疾病视为慢性病
    chronic = [d for d, count in disease_counter.items() if count >= 2]
    return chronic
```

### 3.3 推理流程

```
输入：患者信息 + 当前疾病 + 过敏史 + 当前用药
  ↓
1. 从患者健康记录获取 chronic_diseases
2. 从历史处方推断慢性病 (infer_chronic_diseases)
3. 合并疾病列表 = 当前疾病 + 记录慢性病 + 推断慢性病
4. 获取候选药物列表 (全部药物)
5. 硬过滤：移除禁忌药物 (禁忌规则表)
6. 硬过滤：移除过敏药物
7. DeepFM 预测剩余药物得分 + 差分隐私噪声
8. 排序返回 Top-N + 被排除药物列表 (含排除原因)
```

---

## 四、数据库改造

### 4.1 新增表

```sql
-- 知识图谱实体
CREATE TABLE kg_disease (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    category VARCHAR(50)
);

CREATE TABLE kg_drug (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    category VARCHAR(50)
);

-- 知识图谱关系
CREATE TABLE kg_relation (
    id INT PRIMARY KEY AUTO_INCREMENT,
    source_type VARCHAR(20),   -- 'disease'
    source_id INT,
    target_type VARCHAR(20),   -- 'drug'/'disease'/'symptom'
    target_id INT,
    relation_type VARCHAR(30), -- 'recommand_drug'/'common_drug'/'acompany_with'/'has_symptom'
    INDEX idx_source (source_type, source_id, relation_type)
);

-- 推导的禁忌关系
CREATE TABLE kg_contraindication (
    id INT PRIMARY KEY AUTO_INCREMENT,
    disease_id INT NOT NULL,
    drug_id INT NOT NULL,
    confidence FLOAT DEFAULT 1.0,
    source VARCHAR(50),  -- 'model'/'rule'/'manual'
    UNIQUE KEY uk_disease_drug (disease_id, drug_id)
);
```

---

## 五、后端改造

### 5.1 新增接口

```
GET  /api/patient/{id}/chronic-diseases     → 获取患者慢性病(记录+推断)
GET  /api/kg/contraindications?disease=xxx   → 查询疾病禁忌药物
POST /api/kg/rebuild                         → 重新训练模型并更新禁忌表
```

### 5.2 RecommendationService 改造

代理到 Python 模型前，先查询患者慢性病，传递完整疾病列表：

```java
// 获取患者记录中的慢性病
List<String> recordedChronic = patientHealthRecord.getChronicDiseases();
// 获取从历史处方推断的慢性病
List<String> inferredChronic = inferChronicDiseases(patientId);
// 合并
List<String> allDiseases = merge(currentDiseases, recordedChronic, inferredChronic);
// 传递给模型服务
```

---

## 六、前端改造

### 6.1 推荐结果增强

```
推荐结果区域
├── 推荐药物卡片 (Top-N)
│   ├── 药物名称、类别、推荐分数
│   ├── 适应症匹配说明
│   └── 隐私保护可视化
│
└── ⚠ 已排除药物（折叠区域，默认收起）
    └── 展开后：药物名称 | 排除原因 | 对应疾病 | 置信度
```

### 6.2 慢性病推断提示

```
📋 检测到的慢性病
├── 来自健康记录：高血压、糖尿病
├── 来自处方推断：高血脂（基于历史用药：阿托伐他汀）
└── [确认] [修改] 按钮
```

---

## 七、数据导入流程

```
1. 下载 Kaggle 数据集 CSV 文件到 medical-model/data/
2. 运行导入脚本 parse_kg_data.py:
   a. 解析 nodes.csv → kg_disease + kg_drug
   b. 解析 edges.csv → kg_relation
3. 运行训练脚本 train_with_kg.py:
   a. 构建正/负训练样本
   b. 训练 DeepFM 模型
   c. 导出禁忌规则表 → kg_contraindication
4. 同步知识图谱药物名与系统 drug 表的名称映射
5. 将数据导入 MySQL（通过 SQL 脚本）
```

---

## 八、执行进度

### 阶段规划

| 阶段 | 内容 | 涉及模块 | 状态 |
|------|------|----------|------|
| **P0** | 下载 Kaggle 数据集 | medical-model/data/ | ⏳ 待下载 |
| **P1** | 导入知识图谱数据到 MySQL | 后端 SQL + 导入脚本 | ❌ 未开始 |
| **P2** | 训练数据构建 + DeepFM 重训练 | Python 模型服务 | ❌ 未开始 |
| **P3** | 禁忌规则表生成 + 硬过滤逻辑 | Python 推理服务 | ❌ 未开始 |
| **P4** | 慢性病推断服务 | Python + Java 后端 | ❌ 未开始 |
| **P5** | 后端接口改造 | Java Spring Boot | ❌ 未开始 |
| **P6** | 前端 UI 改造 | React 前端 | ❌ 未开始 |
| **P7** | 端到端测试 | 全栈 | ❌ 未开始 |

### 下一步行动

1. 在另一台设备上下载 Kaggle 数据集
2. 将 CSV 文件放到 `medical-model/data/` 目录下
3. 从 P1 开始执行

---

## 九、关键文件清单

| 文件 | 改动类型 | 说明 |
|------|----------|------|
| `medical-model/app/models/deepfm.py` | 重构 | 多字段FM + 禁忌损失函数 |
| `medical-model/app/services/predictor.py` | 重构 | 禁忌硬过滤 + 慢性病推断 |
| `medical-model/app/services/trainer.py` | 重构 | 知识图谱数据训练流程 |
| `medical-model/app/data/preprocessor.py` | 重构 | 知识图谱特征编码 |
| `medical-model/app/main.py` | 修改 | 新增推断/禁忌接口 |
| `medical-model/data/parse_kg_data.py` | 新增 | 知识图谱数据解析脚本 |
| `medical-model/data/train_with_kg.py` | 新增 | 知识图谱训练脚本 |
| `medical-backend/sql/schema.sql` | 修改 | 新增 kg_* 表 |
| `medical-backend/sql/kg_data.sql` | 新增 | 知识图谱数据导入 SQL |
| `medical-backend/src/.../RecommendationService.java` | 修改 | 慢性病查询+传递 |
| `medical-backend/src/.../KnowledgeGraphService.java` | 新增 | 知识图谱服务 |
| `medical-backend/src/.../KnowledgeGraphController.java` | 新增 | 知识图谱接口 |
| `src/pages/DrugRecommendation.tsx` | 修改 | 排除药物区域 + 慢性病提示 |
| `src/pages/PatientRecords.tsx` | 修改 | 慢性病推断展示 |
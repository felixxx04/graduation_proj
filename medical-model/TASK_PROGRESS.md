# 任务执行情况与剩余工作

## 已完成工作

### Phase 2: 安全数据收集 (100% COMPLETE)

- **禁忌症(Contraindication)**: 22批全部完成，覆盖全部1091种零安全数据药物
- **交互(Interaction)**: 22批全部完成，覆盖全部1091种零安全数据药物
  - Batch 1-20: 早期会话完成
  - Batch 21: 46药物, 44 major, 92 moderate, 2 empty
  - Batch 22: 31药物, 51 major, 75 moderate, 0 empty
- 所有数据保存在 `data/deepseek_prompts/safety_batches/` 对应子目录

### 代码修改（当前未提交）

1. **CLAUDE.md**: 更新项目文档，反映架构变更
2. **config.py**: embed_dim 从16改为8（匹配14-field schema）
3. **predictor.py**: RuleMarker/data_unverified安全等级/翻译改进
4. **safety_filter.py**: 添加data_unverified安全等级支持
5. **explanation_generator.py**: 翻译feature字段名
6. **translation_mapper.py**: 扩展翻译映射（SAFETY_TYPE_ZH, FIELD_NAME_ZH等）
7. **DrugRecommendation.tsx**: 前端安全数据未验证徽章
8. **saved_models/**: 模型文件更新（metadata.json, encoder.json, 模型权重）

### 脚本创建

- `scripts/generate_safety_prompts.py`: 生成安全数据提示词批次
- `scripts/merge_safety_data.py`: 合并安全数据
- `scripts/run_phase3_experiments.py`: Phase 3 DP对比实验脚本

---

## 剩余工作

### Phase 1: 模型重训练 + 部署

1. **Task 1.1**: ✅ embed_dim配置已修复（config.py: embed_dim=8）
2. **Task 1.2**: ⬜ 重新训练模型 — POST /model/train 或直接调用trainer
   - 配置: embed_dim=8, hidden_dims=[64,32], epochs=20, focalLossAlpha=0.4
   - 预期: AUC-PR >0.85
3. **Task 1.3**: ⬜ 运行DP对比实验（论文数据）— 3组: No-DP / DP ε=1.0 / DP ε=0.5

### Phase 2: 安全数据合并与部署（数据已收集，待合并）

1. **Task 2.1**: ✅ SafetyFilter添加"data_unverified"安全等级
2. **Task 2.2**: ✅ 生成安全数据提示词
3. **Task 2.3**: ⬜ 合并安全数据 — 使用merge_safety_data.py合并22批交互+22批禁忌症
   - 验证/去重/更新metadata
   - 目标: contraindication_map和interaction_map覆盖1700+药物
4. **Task 2.4**: ✅ 前端显示"安全数据未验证"徽章

### Phase 3: 翻译完善

1. **Task 3.1**: ⬜ 翻译剩余76个英文病况名 — translation_mapper.py CONDITION_ZH_CORE
2. **Task 3.2**: ⬜ 翻译RuleMarker警告文本 — predictor.py _translate_warnings()
3. **Task 3.3**: ⬜ 翻译解释特征名（BarChart Y轴）— 部分完成(FIELD_NAME_ZH)
4. **Task 3.4**: ⬜ 前端显示matchedDisease + 翻译链完善

### Phase 4: 双加载冲突 + DP可视化

1. **Task 4.1**: ⬜ 解决双加载冲突 — predictor.py set_drugs_data()保留英文数据字段
2. **Task 4.2**: ⬜ DP置信区间可视化增强 — DrugRecommendation.tsx

---

## 优先级排序

```
合并安全数据(2.3) → 模型重训练(1.2) → DP实验(1.3) → 翻译完善(3.1-3.4) → 双加载+可视化(4.1-4.2)
```

合并安全数据是最高优先级，因为它直接影响医疗安全性（1091种药物零安全数据 → SafetyFilter默认视为safe）。
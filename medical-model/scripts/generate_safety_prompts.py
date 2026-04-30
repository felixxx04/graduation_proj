"""生成 DeepSeek 安全数据提示词 — 为1091种缺失药物生成禁忌症+交互数据

为所有不在 contraindication_map 和 interaction_map 中的药物生成两类提示词:
1. 禁忌症数据 (contraindications)
2. 药物交互数据 (interactions)

每批25种药物，约44批禁忌 + 44批交互 = 88个提示词文件。
"""

import json
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
PIPELINE_PATH = os.path.join(DATA_DIR, "pipeline_data.json")
OUTPUT_DIR = os.path.join(DATA_DIR, "deepseek_prompts", "safety_batches")
CONTRA_DIR = os.path.join(OUTPUT_DIR, "contraindication_prompts")
INTER_DIR = os.path.join(OUTPUT_DIR, "interaction_prompts")

os.makedirs(CONTRA_DIR, exist_ok=True)
os.makedirs(INTER_DIR, exist_ok=True)

BATCH_SIZE = 50  # 每批50种药物

# 加载 pipeline_data
with open(PIPELINE_PATH, 'r', encoding='utf-8') as f:
    pipeline_data = json.load(f)

contra_map = pipeline_data.get('contraindication_map', {})
inter_map = pipeline_data.get('interaction_map', {})
merged_drugs = pipeline_data.get('merged_drugs', {})

# 识别缺失药物
safe_verified = set(contra_map.keys()) | set(inter_map.keys())
missing_drugs = []
for drug_name, drug_data in merged_drugs.items():
    if drug_name not in safe_verified:
        missing_drugs.append({
            'name': drug_name,
            'class': drug_data.get('drug_class_en', ''),
            'indications_raw': drug_data.get('indications_raw', ''),
            'side_effects_raw': drug_data.get('side_effects_raw', ''),
            'pregnancy_category': drug_data.get('pregnancy_category', ''),
            'dosage_form': drug_data.get('dosage_form', ''),
            'route': drug_data.get('route_of_administration', ''),
        })

print(f'Drugs with verified safety data: {len(safe_verified)}')
print(f'Drugs needing safety data: {len(missing_drugs)}')

# 分批
batches = []
for i in range(0, len(missing_drugs), BATCH_SIZE):
    batches.append(missing_drugs[i:i + BATCH_SIZE])

print(f'Total batches: {len(batches)} ({BATCH_SIZE} drugs per batch)')

# ── 禁忌症提示词 ──

CONTRA_HEADER = """你是一个临床药学专家。请为以下每种药物生成完整的禁忌症(contraindications)列表。

要求:
1. 每种药物列出其所有禁忌症,包括绝对禁忌症和相对禁忌症
2. 禁忌症类型分为以下类别:
   - disease: 疾病禁忌 (如 "severe renal impairment")
   - allergy_type: 过敏禁忌 (如 "penicillin allergy")
   - physiological_condition: 生理状态禁忌 (如 "pregnancy", "lactation", "pediatric")
   - drug_class: 药物类禁忌 (如 "MAO inhibitors")
3. 严重程度分为:
   - absolute: 绝对禁忌,不应使用
   - relative: 相对禁忌,需谨慎评估获益风险比
4. 禁忌症应具体且临床相关,避免过于笼统
5. 如果药物有 indications_raw,可以帮助推断禁忌症(例如高血压药禁忌低血压)
6. 对于组合药物,列出每个成分的禁忌症

输入药物列表:
"""

CONTRA_EXAMPLE = """

请输出 JSON 格式如下:
[
  {
    "generic_name": "Isotretinoin",
    "contraindications": [
      {"contraindication_name": "pregnancy", "contraindication_type": "physiological_condition", "severity": "absolute", "reason": "Known teratogen, causes severe birth defects"},
      {"contraindication_name": "severe hepatic impairment", "contraindication_type": "disease", "severity": "absolute", "reason": "Hepatotoxicity risk"},
      {"contraindication_name": "vitamin A overdose", "contraindication_type": "drug_class", "severity": "relative", "reason": "Additive toxicity with vitamin A supplements"}
    ]
  },
  ...
]

注意: 只输出JSON,不要输出其他解释文本。"""

# ── 交互数据提示词 ──

INTER_HEADER = """你是一个临床药学专家。请为以下每种药物生成重要的药物交互(interactions)列表。

要求:
1. 只列出 major(严重)和 moderate(中度)交互,不列出 minor(轻微)交互
2. 交互应具有临床意义,影响用药安全或疗效
3. 每个交互包含:
   - drug_a: 药物名称(当前药物)
   - drug_b: 交互药物名称(使用通用药物类别名,如 "warfarin", "MAO inhibitors", "CYP3A4 inhibitors")
   - interaction_type: major 或 moderate
   - clinical_effect: 临床效果描述(如 "增加出血风险", "降低降压效果")
   - mechanism: 机制描述(如 "CYP3A4竞争性抑制", "药效学拮抗")
4. 优先列出与常见药物类的交互(抗凝药、抗抑郁药、抗真菌药、抗酸药等)
5. 对于组合药物,列出每个成分的交互

输入药物列表:
"""

INTER_EXAMPLE = """

请输出 JSON 格式如下:
[
  {
    "generic_name": "Isotretinoin",
    "interactions": [
      {"drug_a": "isotretinoin", "drug_b": "vitamin A supplements", "interaction_type": "major", "clinical_effect": "增加维生素A毒性风险(肝毒性、高钙血症)", "mechanism": "Additive vitamin A toxicity"},
      {"drug_a": "isotretinoin", "drug_b": "tetracycline antibiotics", "interaction_type": "major", "clinical_effect": "增加假性脑瘤风险", "mechanism": "Both increase intracranial pressure"}
    ]
  },
  ...
]

注意: 只输出JSON,不要输出其他解释文本。"""

# ── 生成提示词 ──

contra_count = 0
inter_count = 0

for batch_idx, batch in enumerate(batches):
    batch_num = batch_idx + 1

    # 构建药物列表
    drug_lines = []
    for d in batch:
        ind_raw = d['indications_raw'] if d['indications_raw'] else '(无数据)'
        se_raw = d['side_effects_raw'][:100] + '...' if d.get('side_effects_raw') and len(d.get('side_effects_raw', '')) > 100 else (d.get('side_effects_raw', '') or '(无数据)')
        preg = d['pregnancy_category'] or '未知'
        line = f"{d['name']} | 类别: {d['class']} | 适应症: {ind_raw} | 妊娠分级: {preg}"
        drug_lines.append(line)

    drug_list = "\n".join(drug_lines)

    # 禁忌症提示词
    contra_prompt = CONTRA_HEADER + drug_list + CONTRA_EXAMPLE
    contra_path = os.path.join(CONTRA_DIR, f"contra_prompt_{batch_num}.txt")
    with open(contra_path, 'w', encoding='utf-8') as f:
        f.write(contra_prompt)
    contra_count += 1

    # 交互提示词
    inter_prompt = INTER_HEADER + drug_list + INTER_EXAMPLE
    inter_path = os.path.join(INTER_DIR, f"inter_prompt_{batch_num}.txt")
    with open(inter_path, 'w', encoding='utf-8') as f:
        f.write(inter_prompt)
    inter_count += 1

print(f'\nDone! Generated {contra_count} contraindication prompts + {inter_count} interaction prompts')
print(f'Output dirs:')
print(f'  Contraindication: {CONTRA_DIR}')
print(f'  Interaction: {INTER_DIR}')
print(f'每批{BATCH_SIZE}种药物, 共{len(batches)}批, 覆盖全部{len(missing_drugs)}种药物')
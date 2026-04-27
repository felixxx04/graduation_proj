"""生成 DeepSeek 适应症补充/验证提示词 — 两阶段批量脚本

阶段1 (priority): 36个无适应症药物 → 生成完整适应症
阶段2 (verification): 1061个有适应症但需验证的药物 → 验证准确性并补充遗漏
"""

import json
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

PIPELINE_DATA = "data/pipeline_data.json"
OUTPUT_BASE = "data/deepseek_prompts/indication_verify"
BATCH_SIZE = 50

os.makedirs(OUTPUT_BASE, exist_ok=True)
os.makedirs(os.path.join(OUTPUT_BASE, "priority_batches"), exist_ok=True)
os.makedirs(os.path.join(OUTPUT_BASE, "verify_batches"), exist_ok=True)
os.makedirs(os.path.join(OUTPUT_BASE, "prompts"), exist_ok=True)

# 加载药物数据
with open(PIPELINE_DATA, 'r', encoding='utf-8') as f:
    data = json.load(f)

drugs = data['merged_drugs']

# === 阶段1: 36个无适应症药物 (priority) ===
priority_drugs = []
for name, d in drugs.items():
    if d.get('source_primary') == 'drugs_com' and not d.get('source_supplementary') and not d.get('indications'):
        priority_drugs.append({
            'name': name,
            'class': d.get('drug_class_en', '') or d.get('drug_classes_com', '') or 'Unknown',
        })

# === 阶段2: 1061个需验证药物 ===
verify_drugs = []
for name, d in drugs.items():
    if d.get('source_primary') == 'drugs_com' and not d.get('source_supplementary') and d.get('indications'):
        existing_conditions = [i['condition'] for i in d.get('indications', [])]
        verify_drugs.append({
            'name': name,
            'class': d.get('drug_class_en', '') or d.get('drug_classes_com', '') or 'Unknown',
            'existing_indications': existing_conditions,
        })

# === 生成批量JSON文件 ===
def make_batches(drug_list: list, prefix: str, subdir: str) -> list:
    """分批写入JSON，返回批次数"""
    num_batches = (len(drug_list) + BATCH_SIZE - 1) // BATCH_SIZE
    batch_dir = os.path.join(OUTPUT_BASE, subdir)

    for i in range(num_batches):
        start = i * BATCH_SIZE
        end = min(start + BATCH_SIZE, len(drug_list))
        batch = drug_list[start:end]

        batch_path = os.path.join(batch_dir, f"batch_{i + 1}.json")
        with open(batch_path, 'w', encoding='utf-8') as f:
            json.dump(batch, f, ensure_ascii=False, indent=2)

        print(f"{prefix} batch {i + 1}: {len(batch)} drugs → {batch_path}")

    return num_batches

priority_count = make_batches(priority_drugs, "Priority", "priority_batches")
verify_count = make_batches(verify_drugs, "Verify", "verify_batches")

# === 生成Prompt文件 ===

# 阶段1 Prompt: 生成完整适应症
PRIORITY_HEADER = """你是一个药学知识专家。请为以下每种药物生成完整的适应症(indications)列表。

要求:
1. 每种药物列出其所有常见适应症,包括 On Label(官方批准)和 Off Label(临床常用但未正式批准)
2. 适应症使用英文小写描述,如 "pain", "fever", "hypertension", "type 2 diabetes mellitus"
3. 适应症应具体且可匹配,避免过于笼统(如 "various infections" 应拆分为 "bacterial infection", "urinary tract infection" 等具体适应症)
4. 必须基于真实医学知识,FDA批准的适应症优先,临床常用的Off Label适应症其次
5. 对于组合药物,列出每个成分的适应症
6. 不要虚构适应症,不确定的标注为 "Off Label" 并注明常见程度

输入药物列表:
"""

PRIORITY_EXAMPLE = """

请输出 JSON 格式如下:
[
  {
    "generic_name": "Dexamethasone",
    "indications": [
      {"condition": "inflammatory conditions", "type": "On Label"},
      {"condition": "allergic reactions", "type": "On Label"},
      {"condition": "asthma", "type": "On Label"},
      {"condition": "adrenal insufficiency", "type": "On Label"},
      {"condition": "nausea and vomiting from chemotherapy", "type": "Off Label"}
    ]
  },
  ...
]

注意: 只输出JSON,不要输出其他解释文本。"""

# 阶段2 Prompt: 验证并补充现有适应症
VERIFY_HEADER = """你是一个药学知识专家。请验证以下每种药物的现有适应症列表,并补充遗漏的适应症。

要求:
1. 验证每个现有适应症是否医学正确(是否为该药物的真实适应症)
2. 补充遗漏的重要适应症,包括 On Label 和 Off Label
3. 删除错误的适应症(如不属于该药物的适应症)
4. 适应症使用英文小写描述,如 "pain", "fever", "hypertension"
5. 适应症应具体可匹配,避免过于笼统
6. 必须基于真实医学知识,FDA批准的适应症优先
7. 不要虚构适应症,不确定的标注为 "Off Label"

输入药物列表:
"""

VERIFY_EXAMPLE = """

请输出 JSON 格式如下:
[
  {
    "generic_name": "Salbutamol",
    "verified": true,
    "removed": [],
    "added": [
      {"condition": "exercise-induced asthma", "type": "On Label"},
      {"condition": "bronchospasm", "type": "On Label"}
    ],
    "final_indications": [
      {"condition": "asthma", "type": "On Label"},
      {"condition": "exercise-induced asthma", "type": "On Label"},
      {"condition": "bronchospasm", "type": "On Label"},
      {"condition": "chronic obstructive pulmonary disease", "type": "Off Label"}
    ]
  },
  ...
]

注意: 只输出JSON,不要输出其他解释文本。verified字段表示现有适应症是否基本正确,
removed字段列出被删除的错误适应症,added字段列出新增的适应症,
final_indications是最终的完整适应症列表。"""

# 生成阶段1 prompt文件
priority_batch_dir = os.path.join(OUTPUT_BASE, "priority_batches")
priority_batch_files = sorted([f for f in os.listdir(priority_batch_dir) if f.startswith("batch_") and f.endswith(".json")])

for bf in priority_batch_files:
    batch_path = os.path.join(priority_batch_dir, bf)
    batch_num = bf.replace("batch_", "").replace(".json", "")

    with open(batch_path, 'r', encoding='utf-8') as f:
        batch = json.load(f)

    drug_lines = [f"{d['name']} | {d['class']}" for d in batch]
    drug_list = "\n".join(drug_lines)

    prompt = PRIORITY_HEADER + drug_list + PRIORITY_EXAMPLE
    prompt_path = os.path.join(OUTPUT_BASE, "prompts", f"priority_prompt_{batch_num}.txt")

    with open(prompt_path, 'w', encoding='utf-8') as f:
        f.write(prompt)

    print(f"Priority prompt {batch_num}: {len(batch)} drugs → {prompt_path}")

# 生成阶段2 prompt文件
verify_batch_dir = os.path.join(OUTPUT_BASE, "verify_batches")
verify_batch_files = sorted([f for f in os.listdir(verify_batch_dir) if f.startswith("batch_") and f.endswith(".json")])

for bf in verify_batch_files:
    batch_path = os.path.join(verify_batch_dir, bf)
    batch_num = bf.replace("batch_", "").replace(".json", "")

    with open(batch_path, 'r', encoding='utf-8') as f:
        batch = json.load(f)

    drug_lines = []
    for d in batch:
        existing = ", ".join(d['existing_indications'])
        drug_lines.append(f"{d['name']} | {d['class']} | existing: [{existing}]")

    drug_list = "\n".join(drug_lines)

    prompt = VERIFY_HEADER + drug_list + VERIFY_EXAMPLE
    prompt_path = os.path.join(OUTPUT_BASE, "prompts", f"verify_prompt_{batch_num}.txt")

    with open(prompt_path, 'w', encoding='utf-8') as f:
        f.write(prompt)

    print(f"Verify prompt {batch_num}: {len(batch)} drugs → {prompt_path}")

# === 输出汇总 ===
print(f"\n=== 生成完成 ===")
print(f"阶段1 (Priority): {len(priority_drugs)} 药物, {priority_count} 批次")
print(f"阶段2 (Verify): {len(verify_drugs)} 药物, {verify_count} 批次")
print(f"总计: {len(priority_drugs) + len(verify_drugs)} 药物, {priority_count + verify_count} 批次")
print(f"\n建议先用DeepSeek处理阶段1({priority_count}批), 再处理阶段2({verify_count}批)")
print(f"输出目录: {OUTPUT_BASE}")
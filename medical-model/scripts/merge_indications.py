"""将 DeepSeek 生成的适应症数据合并到 pipeline_data.json

读取 responses/ 目录下的所有 JSON 文件，
将每种药物的 indications 字段更新为结构化适应症列表。
"""

import json
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

PIPELINE_PATH = "data/pipeline_data.json"
RESPONSES_DIR = "data/deepseek_prompts/indication_batches/responses"

# 加载 pipeline_data.json
print("Loading pipeline_data.json...")
with open(PIPELINE_PATH, 'r', encoding='utf-8') as f:
    pipeline_data = json.load(f)

merged_drugs = pipeline_data.get('merged_drugs', {})
original_count = len(merged_drugs)
print(f"Original drugs count: {original_count}")

# 加载所有响应文件
print("Loading DeepSeek responses...")
all_indications = {}  # generic_name → indications list

for filename in sorted(os.listdir(RESPONSES_DIR)):
    filepath = os.path.join(RESPONSES_DIR, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 解析 JSON
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        # 尝试从 markdown 中提取 JSON
        start = content.index('[')
        end = content.rindex(']') + 1
        data = json.loads(content[start:end])

    for drug in data:
        name = drug.get('generic_name', '').strip()
        indications = drug.get('indications', [])
        if name and indications:
            all_indications[name] = indications

    print(f"  {filename}: {len(data)} drugs")

print(f"Total indications loaded: {len(all_indications)}")

# 合并到 pipeline_data
updated_count = 0
missing_names = []

for drug_key, drug_data in merged_drugs.items():
    generic_name = drug_data.get('generic_name', '')

    # 尝试精确匹配
    if generic_name in all_indications:
        drug_data['indications'] = all_indications[generic_name]
        updated_count += 1
    else:
        # 尝试大小写不敏感匹配
        found = False
        for ind_name in all_indications:
            if ind_name.lower() == generic_name.lower():
                drug_data['indications'] = all_indications[ind_name]
                updated_count += 1
                found = True
                break
        if not found:
            missing_names.append(generic_name)

print(f"\nUpdated: {updated_count}/{original_count}")
print(f"Missing (no DeepSeek data): {len(missing_names)}")

if missing_names and len(missing_names) <= 20:
    for name in missing_names:
        print(f"  Missing: {name}")

# 统计适应症质量
indication_stats = {}
for drug_key, drug_data in merged_drugs.items():
    indications = drug_data.get('indications', []) or []
    count = len(indications)
    bucket = f"{count}" if count < 5 else "5+"
    indication_stats[bucket] = indication_stats.get(bucket, 0) + 1

print(f"\nIndication count distribution:")
for bucket in sorted(indication_stats.keys()):
    print(f"  {bucket} indications: {indication_stats[bucket]} drugs")

# 保存更新后的 pipeline_data.json
print(f"\nSaving updated pipeline_data.json...")
with open(PIPELINE_PATH, 'w', encoding='utf-8') as f:
    json.dump(pipeline_data, f, ensure_ascii=False, indent=2)

print("Done!")

# 验证关键药物
print("\n=== Key drug verification ===")
key_drugs = ['Ibuprofen', 'Aspirin', 'acetaminophen', 'Amlodipine', 'Metformin',
             'Acyclovir', 'Omeprazole', 'Clopidogrel', 'Warfarin']
for name in key_drugs:
    if name in merged_drugs:
        indications = merged_drugs[name].get('indications', [])
        conditions = [ind.get('condition', '') if isinstance(ind, dict) else str(ind)
                      for ind in indications]
        print(f"  {name}: {len(indications)} indications = {conditions[:5]}...")
    else:
        # 大小写搜索
        for key, data in merged_drugs.items():
            if data.get('generic_name', '').lower() == name.lower():
                indications = data.get('indications', [])
                conditions = [ind.get('condition', '') if isinstance(ind, dict) else str(ind)
                              for ind in indications]
                print(f"  {name} (as {data.get('generic_name')}): {len(indications)} indications = {conditions[:5]}...")
                break
"""将 DeepSeek 生成的安全数据合并到 pipeline_data.json

读取 contraindication 和 interaction 响应文件，
合并到 pipeline_data.json 的 contraindication_map 和 interaction_map。
不覆盖已有的 Drug Finder 安全数据（825种药物）。

用法: python scripts/merge_safety_data.py
"""

import json
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIPELINE_PATH = os.path.join(PROJECT_ROOT, "data", "pipeline_data.json")
CONTRA_RESPONSES_DIR = os.path.join(PROJECT_ROOT, "data", "deepseek_prompts", "safety_batches", "contraindication_responses")
INTER_RESPONSES_DIR = os.path.join(PROJECT_ROOT, "data", "deepseek_prompts", "safety_batches", "interaction_responses")

# 加载 pipeline_data.json
print("Loading pipeline_data.json...")
with open(PIPELINE_PATH, 'r', encoding='utf-8') as f:
    pipeline_data = json.load(f)

contra_map = pipeline_data.get('contraindication_map', {})
inter_map = pipeline_data.get('interaction_map', {})
merged_drugs = pipeline_data.get('merged_drugs', {})

original_contra_count = len(contra_map)
original_inter_count = len(inter_map)
print(f"Original contraindication_map: {original_contra_count} drugs")
print(f"Original interaction_map: {original_inter_count} drugs")

# 已有安全数据的药物名集合（不覆盖）
existing_safe_drugs = set(contra_map.keys()) | set(inter_map.keys())

# ── 合并禁忌症数据 ──

SEVERITY_NORMALIZE = {
    'absolute': 'absolute',
    'relative': 'relative',
    'major': 'absolute',
    'minor': 'relative',
    'moderate': 'relative',
}

TYPE_NORMALIZE = {
    'disease': 'disease',
    'allergy_type': 'allergy_type',
    'allergy': 'allergy_type',
    'physiological_condition': 'physiological_condition',
    'physiological': 'physiological_condition',
    'pregnancy': 'physiological_condition',
    'drug_class': 'drug_class',
    'drug_interaction': 'drug_class',
}

contra_added = 0
contra_entries_added = 0

if os.path.exists(CONTRA_RESPONSES_DIR):
    for filename in sorted(os.listdir(CONTRA_RESPONSES_DIR)):
        filepath = os.path.join(CONTRA_RESPONSES_DIR, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # 解析 JSON
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            try:
                start = content.index('[')
                end = content.rindex(']') + 1
                data = json.loads(content[start:end])
            except (ValueError, json.JSONDecodeError):
                print(f"  WARNING: Could not parse {filename}, skipping")
                continue

        for drug in data:
            name = drug.get('generic_name', '').strip()
            contraindications = drug.get('contraindications', [])

            if name and contraindications:
                # 查找 pipeline_data 中的药物名
                matched_name = _find_drug_name(name, merged_drugs)

                if matched_name and matched_name not in existing_safe_drugs:
                    # 标准化字段值
                    normalized = []
                    for c in contraindications:
                        if isinstance(c, dict):
                            severity = SEVERITY_NORMALIZE.get(
                                str(c.get('severity', 'relative')).lower(), 'relative'
                            )
                            contra_type = TYPE_NORMALIZE.get(
                                str(c.get('contraindication_type', 'disease')).lower(), 'disease'
                            )
                            normalized.append({
                                'contraindication_name': c.get('contraindication_name', ''),
                                'contraindication_type': contra_type,
                                'severity': severity,
                                'reason': c.get('reason', ''),
                            })

                    contra_map[matched_name] = normalized
                    contra_added += 1
                    contra_entries_added += len(normalized)

        print(f"  {filename}: processed")

    print(f"\nContraindication merge: {contra_added} drugs added, {contra_entries_added} entries total")
else:
    print(f"No contraindication responses found at {CONTRA_RESPONSES_DIR}")

# ── 合并交互数据 ──

INTER_TYPE_NORMALIZE = {
    'major': 'major',
    'moderate': 'moderate',
    'severe': 'major',
    'minor': 'moderate',
}

inter_added = 0
inter_entries_added = 0

if os.path.exists(INTER_RESPONSES_DIR):
    for filename in sorted(os.listdir(INTER_RESPONSES_DIR)):
        filepath = os.path.join(INTER_RESPONSES_DIR, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            try:
                start = content.index('[')
                end = content.rindex(']') + 1
                data = json.loads(content[start:end])
            except (ValueError, json.JSONDecodeError):
                print(f"  WARNING: Could not parse {filename}, skipping")
                continue

        for drug in data:
            name = drug.get('generic_name', '').strip()
            interactions = drug.get('interactions', [])

            if name and interactions:
                matched_name = _find_drug_name(name, merged_drugs)

                if matched_name and matched_name not in existing_safe_drugs:
                    normalized = []
                    for i in interactions:
                        if isinstance(i, dict):
                            inter_type = INTER_TYPE_NORMALIZE.get(
                                str(i.get('interaction_type', 'moderate')).lower(), 'moderate'
                            )
                            normalized.append({
                                'drug_a': i.get('drug_a', matched_name),
                                'drug_b': i.get('drug_b', ''),
                                'interaction_type': inter_type,
                                'clinical_effect': i.get('clinical_effect', ''),
                                'mechanism': i.get('mechanism', ''),
                            })

                    inter_map[matched_name] = normalized
                    inter_added += 1
                    inter_entries_added += len(normalized)

        print(f"  {filename}: processed")

    print(f"\nInteraction merge: {inter_added} drugs added, {inter_entries_added} entries total")
else:
    print(f"No interaction responses found at {INTER_RESPONSES_DIR}")

# ── 更新 pipeline_data ──

pipeline_data['contraindication_map'] = contra_map
pipeline_data['interaction_map'] = inter_map

# 更新 metadata
if 'metadata' not in pipeline_data:
    pipeline_data['metadata'] = {}
pipeline_data['metadata']['safety_data_merge'] = {
    'original_contra_drugs': original_contra_count,
    'original_inter_drugs': original_inter_count,
    'deepseek_contra_drugs_added': contra_added,
    'deepseek_inter_drugs_added': inter_added,
    'total_contra_drugs': len(contra_map),
    'total_inter_drugs': len(inter_map),
    'drugs_still_missing_safety_data': len(merged_drugs) - len(set(contra_map.keys()) | set(inter_map.keys())),
}

print(f"\nFinal stats:")
print(f"  contraindication_map: {len(contra_map)} drugs")
print(f"  interaction_map: {len(inter_map)} drugs")
print(f"  drugs with any safety data: {len(set(contra_map.keys()) | set(inter_map.keys()))}")
print(f"  drugs still missing: {len(merged_drugs) - len(set(contra_map.keys()) | set(inter_map.keys()))}")

# 保存
print(f"\nSaving updated pipeline_data.json...")
with open(PIPELINE_PATH, 'w', encoding='utf-8') as f:
    json.dump(pipeline_data, f, ensure_ascii=False, indent=2)

print("Done!")


def _find_drug_name(name: str, merged_drugs: dict) -> str:
    """在 merged_drugs 中查找药物名（支持大小写不敏感匹配）"""
    # 精确匹配
    if name in merged_drugs:
        return name
    # 大小写不敏感匹配
    for key in merged_drugs:
        if key.lower() == name.lower():
            return key
    # 部分匹配
    name_lower = name.lower()
    for key in merged_drugs:
        if name_lower in key.lower() or key.lower() in name_lower:
            return key
    return None
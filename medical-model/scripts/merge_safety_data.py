"""将 DeepSeek 生成的安全数据合并到 pipeline_data.json

读取 contraindication 和 interaction 响应文件，
合并到 pipeline_data.json 的 contraindication_map 和 interaction_map。
不覆盖已有的 Drug Finder 安全数据（825种药物）。

对于 partial/supplement 文件，智能合并为完整数据：
- inter_batch_1.json 是完整版本，partial/supplement 跳过
- 对于没有完整版本的批次，使用 partial + supplement 合并

用法: python scripts/merge_safety_data.py
"""

import json
import sys
import os
import re
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIPELINE_PATH = os.path.join(PROJECT_ROOT, "data", "pipeline_data.json")
CONTRA_DIR = os.path.join(PROJECT_ROOT, "data", "deepseek_prompts", "safety_batches", "contraindication_responses")
INTER_DIR = os.path.join(PROJECT_ROOT, "data", "deepseek_prompts", "safety_batches", "interaction_responses")


def find_drug_name(name: str, merged_drugs: dict) -> str | None:
    """在 merged_drugs 中查找药物名（支持大小写不敏感匹配）"""
    if not name:
        return None
    # 精确匹配
    if name in merged_drugs:
        return name
    # 大小写不敏感匹配
    for key in merged_drugs:
        if key.lower() == name.lower():
            return key
    # 部分匹配（短名匹配长名）
    name_lower = name.lower()
    for key in merged_drugs:
        key_lower = key.lower()
        if name_lower in key_lower or key_lower in name_lower:
            return key
    return None


def load_json_file(filepath: str) -> list | None:
    """加载 JSON 文件，容错处理"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        try:
            start = content.index('[')
            end = content.rindex(']') + 1
            return json.loads(content[start:end])
        except (ValueError, json.JSONDecodeError):
            print(f"  WARNING: Could not parse {os.path.basename(filepath)}, skipping")
            return None


def classify_batch_files(directory: str) -> dict[int, dict]:
    """将目录中的文件按批次号分类，区分完整版/partial/supplement"""
    pattern = re.compile(r'_(\d+)(?:_(partial|sup\d+))?\.json$', re.IGNORECASE)
    batches: dict[int, dict] = defaultdict(lambda: {"complete": [], "partial": [], "supplements": []})

    for filename in sorted(os.listdir(directory)):
        if not filename.endswith('.json'):
            continue
        match = pattern.search(filename)
        if not match:
            continue

        batch_num = int(match.group(1))
        suffix = match.group(2) or ""

        filepath = os.path.join(directory, filename)
        if suffix == "":
            batches[batch_num]["complete"].append(filepath)
        elif suffix == "partial":
            batches[batch_num]["partial"].append(filepath)
        elif suffix.startswith("sup"):
            batches[batch_num]["supplements"].append(filepath)

    return dict(batches)


def merge_batch_data(batch_info: dict) -> list:
    """智能合并一个批次的所有数据文件

    优先级：
    1. 完整版本文件（如 inter_batch_1.json）
    2. partial + supplements 合并（如果没有完整版）
    """
    # 优先使用完整版本
    if batch_info["complete"]:
        all_drugs = []
        for filepath in batch_info["complete"]:
            data = load_json_file(filepath)
            if data:
                all_drugs.extend(data)
        return all_drugs

    # 没有 complete 版本：partial + supplements
    all_drugs = []
    for filepath in batch_info["partial"]:
        data = load_json_file(filepath)
        if data:
            all_drugs.extend(data)

    for filepath in batch_info["supplements"]:
        data = load_json_file(filepath)
        if data:
            # supplement 可能包含完整数据（DeepSeek 会重新生成）
            # 或者只包含补充部分
            supplement_drugs = {}
            for drug in all_drugs:
                supplement_drugs[drug.get('generic_name', '').strip()] = True
            for drug in data:
                name = drug.get('generic_name', '').strip()
                if name not in supplement_drugs:
                    all_drugs.append(drug)

    return all_drugs


# ── 加载 pipeline_data.json ──

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

# ── 标准化映射 ──

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

INTER_TYPE_NORMALIZE = {
    'major': 'major',
    'moderate': 'moderate',
    'severe': 'major',
    'minor': 'moderate',
}

# ── 合并禁忌症数据 ──

contra_added = 0
contra_entries_added = 0
contra_unmatched = []

if os.path.exists(CONTRA_DIR):
    batches = classify_batch_files(CONTRA_DIR)
    print(f"\nContraindication: {len(batches)} batch groups found")

    for batch_num in sorted(batches.keys()):
        batch_info = batches[batch_num]
        drugs = merge_batch_data(batch_info)

        matched_count = 0
        for drug in drugs:
            name = drug.get('generic_name', '').strip()
            contraindications = drug.get('contraindications', [])

            if not name:
                continue

            matched_name = find_drug_name(name, merged_drugs)

            if matched_name is None:
                contra_unmatched.append(name)
                continue

            if matched_name in existing_safe_drugs:
                continue

            if contraindications:
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
                matched_count += 1

        print(f"  Batch {batch_num}: {len(drugs)} drugs loaded, {matched_count} matched & added")

    print(f"\nContraindication merge: {contra_added} drugs added, {contra_entries_added} entries")
    if contra_unmatched:
        print(f"  Unmatched drug names ({len(contra_unmatched)}): {contra_unmatched[:10]}...")
else:
    print(f"No contraindication responses found at {CONTRA_DIR}")

# ── 合并交互数据 ──

inter_added = 0
inter_entries_added = 0
inter_unmatched = []

if os.path.exists(INTER_DIR):
    batches = classify_batch_files(INTER_DIR)
    print(f"\nInteraction: {len(batches)} batch groups found")

    for batch_num in sorted(batches.keys()):
        batch_info = batches[batch_num]
        drugs = merge_batch_data(batch_info)

        matched_count = 0
        for drug in drugs:
            name = drug.get('generic_name', '').strip()
            interactions = drug.get('interactions', [])

            if not name:
                continue

            matched_name = find_drug_name(name, merged_drugs)

            if matched_name is None:
                inter_unmatched.append(name)
                continue

            if matched_name in existing_safe_drugs:
                continue

            if interactions:
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
                matched_count += 1

        print(f"  Batch {batch_num}: {len(drugs)} drugs loaded, {matched_count} matched & added")

    print(f"\nInteraction merge: {inter_added} drugs added, {inter_entries_added} entries")
    if inter_unmatched:
        print(f"  Unmatched drug names ({len(inter_unmatched)}): {inter_unmatched[:10]}...")
else:
    print(f"No interaction responses found at {INTER_DIR}")

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
    'drugs_with_any_safety_data': len(set(contra_map.keys()) | set(inter_map.keys())),
    'drugs_still_missing_safety_data': len(merged_drugs) - len(set(contra_map.keys()) | set(inter_map.keys())),
}

print(f"\nFinal stats:")
print(f"  contraindication_map: {len(contra_map)} drugs")
print(f"  interaction_map: {len(inter_map)} drugs")
print(f"  drugs with any safety data: {len(set(contra_map.keys()) | set(inter_map.keys()))}")
print(f"  drugs still missing safety data: {len(merged_drugs) - len(set(contra_map.keys()) | set(inter_map.keys()))}")

# 保存
print(f"\nSaving updated pipeline_data.json...")
with open(PIPELINE_PATH, 'w', encoding='utf-8') as f:
    json.dump(pipeline_data, f, ensure_ascii=False, indent=2)

print("Done!")
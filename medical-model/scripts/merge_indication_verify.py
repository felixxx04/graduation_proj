"""合并 DeepSeek 验证结果到 pipeline_data.json

读取 DeepSeek 返回的验证JSON, 将验证后的适应症合并回 pipeline_data.json:
- 阶段1 (priority): 36个无适应症药物 → 直接添加 indications 和 indications_raw
- 阶段2 (verify): 1061个有适应症药物 → 用 final_indications 替换现有 indications, 更新 indications_raw
"""

import json
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

PIPELINE_DATA = "data/pipeline_data.json"
RESPONSE_DIR = "data/deepseek_prompts/indication_verify/responses"

def load_responses(response_dir: str) -> list:
    """加载所有DeepSeek返回的JSON响应"""
    all_results = []

    # 阶段1: priority responses
    priority_dir = os.path.join(response_dir, "priority")
    if os.path.exists(priority_dir):
        for f in sorted(os.listdir(priority_dir)):
            if f.endswith(".json"):
                path = os.path.join(priority_dir, f)
                with open(path, 'r', encoding='utf-8') as fh:
                    results = json.load(fh)
                all_results.extend(results)
                print(f"Loaded priority response: {f} ({len(results)} drugs)")

    # 阶段2: verify responses
    verify_dir = os.path.join(response_dir, "verify")
    if os.path.exists(verify_dir):
        for f in sorted(os.listdir(verify_dir)):
            if f.endswith(".json"):
                path = os.path.join(verify_dir, f)
                with open(path, 'r', encoding='utf-8') as fh:
                    results = json.load(fh)
                all_results.extend(results)
                print(f"Loaded verify response: {f} ({len(results)} drugs)")

    return all_results


def match_drug_name(result_name: str, pipeline_drugs: dict) -> str | None:
    """匹配DeepSeek返回的药物名到pipeline_data中的药物名

    DeepSeek返回的名字可能与pipeline_data不完全一致(大小写、括号等),
    需要做模糊匹配。
    """
    # 直接匹配
    if result_name in pipeline_drugs:
        return result_name

    # 小写匹配
    lower_map = {k.lower(): k for k in pipeline_drugs}
    if result_name.lower() in lower_map:
        return lower_map[result_name.lower()]

    # 去除品牌名后匹配 (只取第一个括号前的部分)
    clean = result_name.split('(')[0].split('Brand')[0].strip()
    if clean.lower() in lower_map:
        return lower_map[clean.lower()]

    # 包含匹配 (result_name 是 pipeline key 的子串)
    for key in pipeline_drugs:
        if result_name.lower() in key.lower() or key.lower() in result_name.lower():
            # 避免过度匹配: 必须有足够重叠
            if len(result_name) > 3 and len(key) > 3:
                # 检查核心药名是否一致
                core_result = result_name.lower().split()[0]
                core_key = key.lower().split()[0]
                if core_result == core_key and len(core_result) > 3:
                    return key

    return None


def merge_results(pipeline_data: dict, all_results: list) -> tuple[int, int, int]:
    """合并DeepSeek结果到pipeline_data

    Returns: (updated_count, skipped_count, error_count)
    """
    drugs = pipeline_data['merged_drugs']
    updated = 0
    skipped = 0
    errors = 0

    for result in all_results:
        drug_name = result.get('generic_name', '')
        matched_key = match_drug_name(drug_name, drugs)

        if matched_key is None:
            print(f"  SKIP: '{drug_name}' not found in pipeline_data")
            skipped += 1
            continue

        d = drugs[matched_key]

        # 阶段1 (priority): 没有 final_indications 字段, 直接用 indications
        if 'final_indications' in result:
            # 阶段2 (verify): 有 final_indications
            final_inds = result['final_indications']
            verified = result.get('verified', True)
            removed = result.get('removed', [])
            added = result.get('added', [])

            if removed:
                print(f"  {matched_key}: removed {removed}")
            if added:
                added_names = [a['condition'] for a in added]
                print(f"  {matched_key}: added {added_names}")

            # 更新 indications
            d['indications'] = final_inds
            # 更新 indications_raw (从 final_indications 拼接)
            d['indications_raw'] = '|'.join([i['condition'] for i in final_inds])

        elif 'indications' in result:
            # 阶段1 (priority): 直接生成
            inds = result['indications']
            d['indications'] = inds
            d['indications_raw'] = '|'.join([i['condition'] for i in inds])

        else:
            print(f"  ERROR: '{drug_name}' has no indications data in response")
            errors += 1
            continue

        updated += 1

    return updated, skipped, errors


def main():
    # 加载 pipeline_data
    with open(PIPELINE_DATA, 'r', encoding='utf-8') as f:
        pipeline_data = json.load(f)

    # 加载 DeepSeek responses
    if not os.path.exists(RESPONSE_DIR):
        print(f"Response directory not found: {RESPONSE_DIR}")
        print("请先将DeepSeek的返回结果放入以下目录结构:")
        print(f"  {RESPONSE_DIR}/priority/  — 阶段1(36药物)的返回JSON")
        print(f"  {RESPONSE_DIR}/verify/    — 阶段2(1061药物)的返回JSON")
        return

    all_results = load_responses(RESPONSE_DIR)
    print(f"\nTotal results loaded: {len(all_results)}")

    if not all_results:
        print("No results found. 请确认responses目录中有JSON文件。")
        return

    # 合并
    print("\n=== 合并开始 ===")
    updated, skipped, errors = merge_results(pipeline_data, all_results)

    # 保存
    with open(PIPELINE_DATA, 'w', encoding='utf-8') as f:
        json.dump(pipeline_data, f, ensure_ascii=False, indent=2)

    print(f"\n=== 合并完成 ===")
    print(f"更新: {updated} 药物")
    print(f"跳过(未匹配): {skipped} 药物")
    print(f"错误(无数据): {errors} 药物")

    # 统计合并后状态
    drugs = pipeline_data['merged_drugs']
    has_ind = sum(1 for d in drugs.values() if d.get('indications'))
    has_ind_raw = sum(1 for d in drugs.values() if d.get('indications_raw', '').strip())
    total = len(drugs)

    print(f"\n合并后统计:")
    print(f"  总药物数: {total}")
    print(f"  有结构化indications: {has_ind}/{total}")
    print(f"  有indications_raw: {has_ind_raw}/{total}")


if __name__ == "__main__":
    main()
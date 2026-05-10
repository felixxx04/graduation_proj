"""Batch translate drug indications via DeepSeek API — v2 with better error handling.
Continues from existing progress file."""
import json
import time
import os
import sys
import io
import requests
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

API_URL = "https://api.deepseek.com/anthropic/v1/messages"
AUTH_TOKEN = os.environ.get('ANTHROPIC_AUTH_TOKEN', '')
MODEL = "deepseek-v4-pro"
BATCH_SIZE = 35

PROGRESS_PATH = "data/indication_translations_progress.json"
FINAL_PATH = "data/indication_translations.json"


def load_all_indications():
    with open('data/pipeline_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    drugs = data['merged_drugs']
    ind_count = Counter()
    for name, drug in drugs.items():
        indications = drug.get('indications', [])
        if isinstance(indications, str):
            for ind in indications.split('|'):
                c = ind.strip().lower()
                if c and len(c) > 2:
                    ind_count[c] += 1
        elif isinstance(indications, list):
            for ind in indications:
                c = (ind.get('condition', '') if isinstance(ind, dict) else str(ind)).strip().lower()
                if c and len(c) > 2:
                    ind_count[c] += 1
    return [ind for ind, _ in ind_count.most_common()], ind_count


def call_api(prompt):
    payload = {'model': MODEL, 'max_tokens': 5000, 'messages': [{'role': 'user', 'content': prompt}]}
    headers = {'Content-Type': 'application/json', 'x-api-key': AUTH_TOKEN, 'anthropic-version': '2023-06-01'}
    r = requests.post(API_URL, json=payload, headers=headers, timeout=180)
    if r.status_code == 200:
        data = r.json()
        for block in data.get('content', []):
            if block.get('type') == 'text':
                text = block.get('text', '').strip()
                if text:
                    return text
        # Check thinking for content
        for block in data.get('content', []):
            if block.get('type') == 'thinking':
                thinking = block.get('thinking', '')
                lines = thinking.strip().split('\n')
                text_lines = [l for l in lines if '|' in l]
                if text_lines:
                    return '\n'.join(text_lines)
        return ''
    else:
        raise Exception(f"API {r.status_code}: {r.text[:200]}")


def parse_response(text, batch_indications):
    """Parse pipe-delimited response: en | cn | body_system | etiology"""
    results = {}
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line or '|' not in line:
            continue
        parts = [p.strip() for p in line.split('|')]
        if len(parts) < 2:
            continue
        en_key = parts[0].lower()
        cn_val = parts[1]
        bs_val = parts[2] if len(parts) > 2 else ''
        et_val = parts[3] if len(parts) > 3 else ''

        # Direct match
        if en_key in batch_indications:
            results[en_key] = {'chinese': cn_val, 'body_system': bs_val, 'etiology': et_val}
            continue

        # Fuzzy match
        for ind in batch_indications:
            if ind == en_key or ind in en_key or en_key in ind:
                results[ind] = {'chinese': cn_val, 'body_system': bs_val, 'etiology': et_val}
                break

    return results


def main():
    if not AUTH_TOKEN:
        print("ERROR: No ANTHROPIC_AUTH_TOKEN")
        return

    all_indications, ind_count = load_all_indications()
    print(f"Total: {len(all_indications)} indications")

    # Load progress
    results = {}
    if os.path.exists(PROGRESS_PATH):
        with open(PROGRESS_PATH, 'r', encoding='utf-8') as f:
            results = json.load(f)
    print(f"Done: {len(results)}")

    remaining = [ind for ind in all_indications if ind not in results]
    print(f"Remaining: {len(remaining)}")

    if not remaining:
        print("All done!")
        return

    total_batches = (len(remaining) + BATCH_SIZE - 1) // BATCH_SIZE
    consecutive_errors = 0

    for batch_start in range(0, len(remaining), BATCH_SIZE):
        batch = remaining[batch_start:batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1

        batch_set = set(batch)
        prompt = f"""翻译以下英文药品适应症为中文，并分类身体系统和病因。

格式：英文名 | 中文翻译 | 身体系统 | 病因
身体系统从：cardiovascular respiratory gastrointestinal hepatic biliary renal reproductive endocrine neurologic musculoskeletal dermatologic ophthalmic hematologic systemic 中选择
病因从：chronic acute infectious bacterial viral fungal parasitic inflammatory autoimmune neoplastic metabolic degenerative functional allergic genetic psychiatric symptomatic 中选择

{chr(10).join(f'{i+1}. {ind}' for i, ind in enumerate(batch))}"""

        try:
            response = call_api(prompt)
            batch_results = parse_response(response, batch_set)

            for ind in batch:
                if ind not in batch_results:
                    batch_results[ind] = {'chinese': ind, 'body_system': '', 'etiology': ''}

            results.update(batch_results)
            consecutive_errors = 0

        except Exception as e:
            print(f"  Batch {batch_num}: ERROR {e}")
            consecutive_errors += 1
            if consecutive_errors >= 3:
                print("  Too many errors, stopping")
                break
            time.sleep(10)
            continue

        # Save every batch
        with open(PROGRESS_PATH, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        got = sum(1 for ind in batch if results.get(ind, {}).get('body_system'))
        print(f"  Batch {batch_num}/{total_batches}: {got}/{len(batch)} with body_system | Total: {len(results)}")

        time.sleep(3)

    with open(FINAL_PATH, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\nDONE: {len(results)} translated")
    print(f"Saved: {FINAL_PATH}")


if __name__ == "__main__":
    main()

"""Batch translate drug indications from English to Chinese via DeepSeek API.
Also adds L2 body_system+etiology classification for KnowledgeRouter."""
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
BATCH_SIZE = 40

OUTPUT_PATH = "data/indication_translations.json"
PROGRESS_PATH = "data/indication_translations_progress.json"

def load_indications():
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
    return ind_count


def call_api(prompt, retry=0):
    payload = {
        'model': MODEL,
        'max_tokens': 4000,
        'messages': [{'role': 'user', 'content': prompt}]
    }
    headers = {
        'Content-Type': 'application/json',
        'x-api-key': AUTH_TOKEN,
        'anthropic-version': '2023-06-01'
    }
    try:
        r = requests.post(API_URL, json=payload, headers=headers, timeout=120)
        if r.status_code == 200:
            data = r.json()
            for block in data.get('content', []):
                if block.get('type') == 'text':
                    return block.get('text', '').strip()
            return ''
        else:
            raise Exception(f"API {r.status_code}: {r.text[:200]}")
    except requests.exceptions.Timeout:
        if retry < 2:
            time.sleep(5)
            return call_api(prompt, retry + 1)
        raise


def parse_batch_response(text, indications):
    """Parse DeepSeek's batch translation response.
    Expected format per line: ENGLISH | CHINESE | BODY_SYSTEM | ETIOLOGY"""
    results = {}
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line or '|' not in line:
            continue
        parts = [p.strip() for p in line.split('|')]
        if len(parts) >= 2:
            en = parts[0].lower()
            cn = parts[1]
            body_system = parts[2] if len(parts) > 2 else ''
            etiology = parts[3] if len(parts) > 3 else ''
            # Match back to original indication
            for ind in indications:
                if ind.lower() == en or ind.lower() in en or en in ind.lower():
                    results[ind] = {
                        'chinese': cn,
                        'body_system': body_system,
                        'etiology': etiology,
                    }
                    break
            # Direct match
            if en in indications:
                results[en] = {
                    'chinese': cn,
                    'body_system': body_system,
                    'etiology': etiology,
                }
    return results


def main():
    if not AUTH_TOKEN:
        print("ERROR: ANTHROPIC_AUTH_TOKEN not set")
        return

    ind_count = load_indications()
    # Sort by frequency, prioritize common ones
    sorted_inds = [ind for ind, _ in ind_count.most_common()]
    print(f"Total unique indications: {len(sorted_inds)}")
    print(f"Batches of {BATCH_SIZE}: {(len(sorted_inds) + BATCH_SIZE - 1) // BATCH_SIZE}")

    # Load existing progress
    all_results = {}
    if os.path.exists(PROGRESS_PATH):
        with open(PROGRESS_PATH, 'r', encoding='utf-8') as f:
            all_results = json.load(f)
        print(f"Loaded {len(all_results)} existing translations")

    # Filter out already translated
    remaining = [ind for ind in sorted_inds if ind not in all_results]
    print(f"Remaining: {len(remaining)}")

    if not remaining:
        print("All done!")
        return

    # Process in batches
    for batch_start in range(0, len(remaining), BATCH_SIZE):
        batch = remaining[batch_start:batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1
        total_batches = (len(remaining) + BATCH_SIZE - 1) // BATCH_SIZE

        print(f"\n[Batch {batch_num}/{total_batches}] {len(batch)} indications...")

        # Build prompt
        ind_list = '\n'.join(f'{i+1}. {ind}' for i, ind in enumerate(batch))
        prompt = f"""请作为医学翻译和疾病分类专家，为以下英文药品适应症提供：
1. 准确的中文翻译
2. 身体系统分类（cardiovascular/respiratory/gastrointestinal/hepatic/biliary/renal/reproductive/endocrine/neurologic/musculoskeletal/dermatologic/ophthalmic/hematologic/systemic/other）
3. 病因分类（chronic/acute/infectious/viral/bacterial/fungal/parasitic/inflammatory/autoimmune/neoplastic/metabolic/degenerative/functional/allergic/genetic/psychiatric/symptomatic/other）

格式：英文名 | 中文翻译 | 身体系统 | 病因
每行一个适应症，请勿添加额外说明。

{ind_list}"""

        try:
            response = call_api(prompt)
            batch_results = parse_batch_response(response, batch)

            # Fill gaps with direct string match
            for ind in batch:
                if ind not in batch_results:
                    # Try fuzzy
                    for en, data in list(batch_results.items()):
                        if en in ind or ind in en:
                            batch_results[ind] = data
                            break

            all_results.update(batch_results)

            # Save progress
            with open(PROGRESS_PATH, 'w', encoding='utf-8') as f:
                json.dump(all_results, f, ensure_ascii=False, indent=2)

            found = len(batch_results)
            print(f"  Translated: {found}/{len(batch)} ({found/len(batch)*100:.0f}%)")
            if found < len(batch):
                missing = [ind for ind in batch if ind not in batch_results]
                print(f"  Missing ({len(missing)}): {missing[:3]}...")
                # Save missing as-is
                for ind in missing:
                    all_results[ind] = {'chinese': ind, 'body_system': '', 'etiology': ''}

        except Exception as e:
            print(f"  ERROR: {e}")
            time.sleep(10)
            continue

        time.sleep(2)  # Rate limit

    # Save final results
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"COMPLETE: {len(all_results)} indications translated")
    print(f"Output: {OUTPUT_PATH}")

    # Stats
    has_body = sum(1 for v in all_results.values() if v.get('body_system'))
    has_etiology = sum(1 for v in all_results.values() if v.get('etiology'))
    print(f"With body_system: {has_body}")
    print(f"With etiology: {has_etiology}")


if __name__ == "__main__":
    main()

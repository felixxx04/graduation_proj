"""Fix P0 gaps: re-translate bad indications, expand L1 colloquial, expand symptom combos.
All done via DeepSeek API in a single batch pass."""
import json
import time
import os
import sys
import io
import re
import requests
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

API_URL = "https://api.deepseek.com/anthropic/v1/messages"
AUTH_TOKEN = os.environ.get('ANTHROPIC_AUTH_TOKEN', '')
MODEL = "deepseek-v4-pro"

VALID_BS = {'cardiovascular','respiratory','gastrointestinal','hepatic','biliary',
            'renal','reproductive','endocrine','neurologic','musculoskeletal',
            'dermatologic','ophthalmic','hematologic','systemic','psychiatric'}
VALID_ET = {'chronic','acute','infectious','bacterial','viral','fungal','parasitic',
            'inflammatory','autoimmune','neoplastic','metabolic','degenerative',
            'functional','allergic','genetic','psychiatric','symptomatic',
            'vascular','ischemic','arrhythmic','atherosclerotic','thrombotic',
            'dysfunction','deficiency','erosive','reflux','calculous','hyperplastic',
            'mechanical','hemorrhagic','withdrawal','dependency','congenital','hormonal'}


def load_bad_translations():
    """Load indications whose translation needs fixing."""
    with open('data/indication_translations_progress.json', 'r', encoding='utf-8') as f:
        translations = json.load(f)

    with open('data/pipeline_data.json', 'r', encoding='utf-8') as f:
        drugs = json.load(f)['merged_drugs']

    ind_count = Counter()
    for name, drug in drugs.items():
        indications = drug.get('indications', [])
        if isinstance(indications, str):
            for ind in indications.split('|'):
                c = ind.strip().lower()
                if c and len(c) > 2: ind_count[c] += 1
        elif isinstance(indications, list):
            for ind in indications:
                c = (ind.get('condition','') if isinstance(ind, dict) else str(ind)).strip().lower()
                if c and len(c) > 2: ind_count[c] += 1

    bad = []
    for en, info in translations.items():
        bs = info.get('body_system', '').strip().lower()
        et = info.get('etiology', '').strip().lower()
        cn = info.get('chinese', '')
        if bs not in VALID_BS or (bs in VALID_BS and et and et not in VALID_ET):
            drug_cnt = ind_count.get(en, 0)
            bad.append((en, cn, bs, et, drug_cnt))

    bad.sort(key=lambda x: -x[4])  # Sort by drug count descending
    return bad


def call_api(prompt):
    payload = {'model': MODEL, 'max_tokens': 4000, 'messages': [{'role': 'user', 'content': prompt}]}
    headers = {'Content-Type': 'application/json', 'x-api-key': AUTH_TOKEN, 'anthropic-version': '2023-06-01'}
    for attempt in range(3):
        try:
            r = requests.post(API_URL, json=payload, headers=headers, timeout=120)
            if r.status_code == 200:
                data = r.json()
                for block in data.get('content', []):
                    if block.get('type') == 'text' and block.get('text', '').strip():
                        return block['text'].strip()
                return ''
            else:
                time.sleep(5)
        except:
            time.sleep(5)
    return ''


def fix_translations(bad_items):
    """Re-translate bad indications with strict format."""
    print(f"\n=== Fixing {len(bad_items)} bad translations ===")

    batch_size = 40
    all_fixes = {}
    progress_path = 'data/indication_translations_progress.json'

    # Process in batches
    for bi in range(0, len(bad_items), batch_size):
        batch = bad_items[bi:bi + batch_size]
        batch_num = bi // batch_size + 1
        total = (len(bad_items) + batch_size - 1) // batch_size
        print(f"  Batch {batch_num}/{total}: {len(batch)} items")

        # Build prompt
        items = '\n'.join(f'{i+1}. {en}' for i, (en, _, _, _, _) in enumerate(batch))
        prompt = f"""为以下英文药品适应症提供中文翻译和分类。严格使用给定选项。

格式每行：英文名 | 中文翻译 | 身体系统 | 病因
身体系统（只能选一个）：cardiovascular respiratory gastrointestinal hepatic biliary renal reproductive endocrine neurologic musculoskeletal dermatologic ophthalmic hematologic systemic psychiatric
病因（只能选一个）：chronic acute infectious bacterial viral fungal parasitic inflammatory autoimmune neoplastic metabolic degenerative functional allergic genetic psychiatric symptomatic vascular ischemic hemorrhagic deficiency hormonal

{items}"""

        response = call_api(prompt)
        if not response:
            print(f"    Empty response, skipping")
            continue

        # Parse
        fixed = 0
        for line in response.strip().split('\n'):
            parts = [p.strip() for p in line.split('|')]
            if len(parts) < 2: continue
            en_key = parts[0].lower()
            cn_val = parts[1]
            bs_val = parts[2].lower() if len(parts) > 2 else ''
            et_val = parts[3].lower() if len(parts) > 3 else ''

            # Validate bs and et
            if bs_val not in VALID_BS: bs_val = ''
            if et_val not in VALID_ET: et_val = ''

            # Fuzzy match to original en
            for orig_en, _, _, _, _ in batch:
                if orig_en.lower() == en_key or orig_en.lower() in en_key or en_key in orig_en.lower():
                    all_fixes[orig_en] = {'chinese': cn_val, 'body_system': bs_val, 'etiology': et_val}
                    fixed += 1
                    break

        print(f"    Fixed: {fixed}/{len(batch)}")

        # Save incrementally
        if os.path.exists(progress_path):
            with open(progress_path, 'r', encoding='utf-8') as f:
                progress = json.load(f)
            for en, info in all_fixes.items():
                progress[en] = info
            with open(progress_path, 'w', encoding='utf-8') as f:
                json.dump(progress, f, ensure_ascii=False, indent=2)

        time.sleep(2)

    return all_fixes


def expand_l1_colloquial():
    """Generate 200+ new colloquial → standard term mappings."""
    print(f"\n=== Expanding L1 colloquial table ===")

    prompt = """请作为中文医学专家，为以下常见患者口语表达提供标准医学术语（英文）。

每个口语词至少给1个标准英文术语，可以给2-3个。格式：中文口语 | 英文术语1, 英文术语2

腹泻相关：窜稀 闹肚子 水样便 拉水 便稀
疼痛相关：抽筋 痉挛 落枕 扭伤 崴脚 岔气 淤青
消化相关：打嗝 嗳气 屁多 胀气 口臭 烧胃 胃酸多
口腔相关：牙龈肿 牙疼 口腔溃疡 嘴角烂 口舌生疮
眼部相关：眼干 眼涩 眼屎多 流泪 怕光 眼痒
耳部相关：耳堵 耳闷 听力下降 耳朵流脓 耳鸣嗡嗡
呼吸相关：痰多 干咳 夜咳 喘不上气 吸气痛
泌尿相关：小便黄 小便泡沫多 夜尿多 尿不尽 尿等待 尿分叉 尿痛尿急
心血管相关：心口疼 心跳乱 心口堵 心口闷 腿肿 脚肿
皮肤相关：起皮 脱屑 红印 硬块 小疙瘩 水泡 脓包
神经相关：手脚麻 腿麻 手抖 记性差 坐不住 胡思乱想
全身相关：怕冷 盗汗 出虚汗 口干 口苦 没胃口 消瘦
妇科相关：痛经 月经少 月经多 月经不按时 白带多 白带黄 下体痒
男科相关：尿不出来 勃起不硬 早泄 阴囊湿 腰痛尿频"""

    response = call_api(prompt)
    if not response:
        print("  Empty response")
        return {}

    new_l1 = {}
    for line in response.strip().split('\n'):
        parts = [p.strip() for p in line.split('|')]
        if len(parts) < 2:
            # Try comma/other separator
            parts = [p.strip() for p in line.split('|', 1)]
            if len(parts) < 2: continue
        cn = parts[0]
        en_raw = parts[1] if len(parts) > 1 else ''
        # Parse comma-separated English terms
        en_terms = [e.strip().lower() for e in en_raw.replace(',', '|').replace('，', '|').split('|') if e.strip()]
        if cn and en_terms and len(cn) >= 2:
            new_l1[cn] = en_terms

    print(f"  Generated {len(new_l1)} new L1 entries")
    for cn, en in list(new_l1.items())[:5]:
        print(f"    {cn} -> {en}")
    return new_l1


def expand_symptom_combos():
    """Generate 50+ symptom combination → disease rules."""
    print(f"\n=== Expanding symptom combo rules ===")

    prompt = """请作为临床诊断专家，为以下症状组合推断最可能的疾病。

格式每行：最可能的疾病英文名 | 症状关键词(用逗号分隔) | 最少需匹配几个关键词 | 身体系统 | 病因

给50个常见症状组合，覆盖：
- 呼吸系统(咳嗽咳痰发烧→肺炎, 鼻塞流涕打喷嚏→过敏性鼻炎)
- 消化系统(反酸烧心胸痛→GERD, 腹痛腹泻发烧→急性胃肠炎)
- 心血管(胸闷气短心悸→心衰, 头晕眼花→低血压)
- 神经(头晕恶心耳鸣→梅尼埃病, 一侧头痛畏光→偏头痛)
- 泌尿(尿频尿急尿痛→尿路感染, 腰疼血尿→肾结石)
- 皮肤(红斑鳞屑→银屑病, 水疱灼痛→带状疱疹)
- 内分泌(多饮多尿消瘦→糖尿病, 怕冷乏力浮肿→甲减)
- 骨骼(腰腿痛麻→腰椎间盘突出, 关节红肿热痛→痛风急性发作)
- 精神(情绪低失眠厌食→抑郁症, 紧张心慌手抖→焦虑症)"""

    response = call_api(prompt)
    if not response:
        print("  Empty response")
        return []

    new_combos = []
    for line in response.strip().split('\n'):
        parts = [p.strip() for p in line.split('|')]
        if len(parts) < 4: continue
        disease = parts[0].lower()
        keywords_raw = parts[1]
        try:
            min_matches = int(re.search(r'\d+', parts[2]).group()) if re.search(r'\d+', parts[2]) else 2
        except:
            min_matches = 2
        body_system = parts[3].lower() if len(parts) > 3 else ''
        etiology = parts[4].lower() if len(parts) > 4 else ''

        keywords = [k.strip().lower() for k in keywords_raw.replace(',', '|').replace('，', '|').split('|') if k.strip()]
        if disease and keywords:
            new_combos.append({
                'keywords': keywords,
                'min_matches': min_matches,
                'disease': disease,
                'body_system': body_system if body_system in VALID_BS else '',
                'etiology': etiology if etiology in VALID_ET else '',
            })

    print(f"  Generated {len(new_combos)} new symptom combos")
    for c in new_combos[:5]:
        print(f"    {c['disease']}: {c['keywords'][:3]}... (min {c['min_matches']})")
    return new_combos


def apply_fixes():
    """Apply all fixes to the actual data files."""
    print("\n=== Applying fixes ===")

    # 1. Update disease_mapper with new Chinese entries from fixed translations
    progress_path = 'data/indication_translations_progress.json'
    if not os.path.exists(progress_path):
        print("No progress file found")
        return

    with open(progress_path, 'r', encoding='utf-8') as f:
        translations = json.load(f)

    # Build cn→en mappings
    cn_to_en = {}
    for en, info in translations.items():
        cn = info.get('chinese', '').strip()
        bs = info.get('body_system', '').strip().lower()
        if bs not in VALID_BS: continue
        cn = re.sub(r'[（(][^)）]*[)）]', '', cn).strip()
        if len(cn) < 2: continue
        if cn not in cn_to_en:
            cn_to_en[cn] = []
        if en not in cn_to_en[cn]:
            cn_to_en[cn].append(en)

    # Update disease_mapper.py
    mapper_path = 'app/utils/disease_mapper.py'
    with open(mapper_path, 'r', encoding='utf-8') as f:
        content = f.read()

    old_match = re.search(r'CHINESE_TO_ENGLISH_DISEASE.*?=\s*\{(.+?)\}', content, re.DOTALL)
    if old_match:
        lines = ['CHINESE_TO_ENGLISH_DISEASE: Dict[str, List[str]] = {']
        for cn in sorted(cn_to_en.keys()):
            en_list = ', '.join(f'"{e}"' for e in cn_to_en[cn])
            lines.append(f'    "{cn}": [{en_list}],')
        lines.append('}')
        new_dict = '\n'.join(lines)
        content = content[:old_match.start()] + new_dict + content[old_match.end():]

        with open(mapper_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  disease_mapper: {len(cn_to_en)} entries")

    # 2. Update routing_tables.json
    with open('app/data/routing_tables.json', 'r', encoding='utf-8') as f:
        rt = json.load(f)

    # Update L2 with fixed translations
    new_l2 = 0
    for en, info in translations.items():
        bs = info.get('body_system', '').strip().lower()
        et = info.get('etiology', '').strip().lower()
        cn = info.get('chinese', '').strip()
        if bs not in VALID_BS: continue
        cn = re.sub(r'[（(][^)）]*[)）]', '', cn).strip()
        if len(cn) < 2: continue
        if en not in rt['l2_disease_categories']:
            rt['l2_disease_categories'][en] = {'body_system': bs, 'etiology': et, 'category_name': cn}
            new_l2 += 1

    print(f"  L2: added {new_l2} entries, total {len(rt['l2_disease_categories'])}")

    # Ensure L3 has routes for all body_system+etiology combos
    existing_l3 = set(rt['l3_indication_to_atc'].keys())
    needed_l3 = set()
    for en, cat in rt['l2_disease_categories'].items():
        bs, et = cat.get('body_system',''), cat.get('etiology','')
        if bs and et:
            l3k = f'{bs}_{et}'
            if l3k not in existing_l3:
                needed_l3.add(l3k)

    if needed_l3:
        # Auto-generate L3 routes
        for l3k in sorted(needed_l3):
            bs, et = l3k.split('_', 1)
            if et in ('bacterial','infectious'):
                rt['l3_indication_to_atc'][l3k] = {'atc_codes': ['J01'], 'drug_classes': ['抗生素'], 'description': f'{bs}感染用药'}
            elif et == 'viral':
                rt['l3_indication_to_atc'][l3k] = {'atc_codes': ['J05'], 'drug_classes': ['抗病毒药'], 'description': f'{bs}病毒感染用药'}
            elif et == 'fungal':
                rt['l3_indication_to_atc'][l3k] = {'atc_codes': ['J02'], 'drug_classes': ['抗真菌药'], 'description': f'{bs}真菌感染用药'}
            elif et == 'allergic':
                rt['l3_indication_to_atc'][l3k] = {'atc_codes': ['R06'], 'drug_classes': ['抗组胺药'], 'description': f'{bs}过敏用药'}
            elif et in ('acute','symptomatic','functional'):
                rt['l3_indication_to_atc'][l3k] = {'atc_codes': ['N02'], 'drug_classes': ['对症治疗药'], 'description': f'{bs}症状治疗'}
            elif et in ('inflammatory','autoimmune'):
                rt['l3_indication_to_atc'][l3k] = {'atc_codes': ['M01','L04'], 'drug_classes': ['NSAIDs','免疫抑制剂'], 'description': f'{bs}炎症治疗'}
            else:
                rt['l3_indication_to_atc'][l3k] = {'atc_codes': ['N02'], 'drug_classes': ['对症治疗药'], 'description': f'{bs}{et}类用药'}
        print(f"  L3: added {len(needed_l3)} routes, total {len(rt['l3_indication_to_atc'])}")

    with open('app/data/routing_tables.json', 'w', encoding='utf-8') as f:
        json.dump(rt, f, ensure_ascii=False, indent=2)

    # 3. Update symptom_combos.json
    new_combos = expand_symptom_combos()
    if new_combos:
        with open('app/data/symptom_combos.json', 'r', encoding='utf-8') as f:
            combos = json.load(f)
        existing_diseases = {c['disease'] for c in combos['combos']}
        for c in new_combos:
            if c['disease'] not in existing_diseases:
                combos['combos'].append(c)
        with open('app/data/symptom_combos.json', 'w', encoding='utf-8') as f:
            json.dump(combos, f, ensure_ascii=False, indent=2)
        print(f"  symptom_combos: {len(combos['combos'])} total")

    # 4. Update L1 colloquial
    new_l1 = expand_l1_colloquial()
    if new_l1:
        with open('app/data/routing_tables.json', 'r', encoding='utf-8') as f:
            rt = json.load(f)
        for cn, en_list in new_l1.items():
            if cn not in rt['l1_colloquial_to_standard']:
                rt['l1_colloquial_to_standard'][cn] = en_list
        with open('app/data/routing_tables.json', 'w', encoding='utf-8') as f:
            json.dump(rt, f, ensure_ascii=False, indent=2)
        print(f"  L1: added {len(new_l1)} entries, total {len(rt['l1_colloquial_to_standard'])}")


def main():
    # Step 1: Fix bad translations
    bad = load_bad_translations()
    print(f"Bad translations to fix: {len(bad)}")
    fixes = fix_translations(bad)

    # Step 2: Apply all fixes
    apply_fixes()

    # Step 3: Stats
    with open('app/data/routing_tables.json', 'r', encoding='utf-8') as f:
        rt = json.load(f)
    print(f"\n=== FINAL STATS ===")
    print(f"L1 colloquial: {len(rt['l1_colloquial_to_standard'])}")
    print(f"L2 diseases: {len(rt['l2_disease_categories'])}")
    print(f"L3 routes: {len(rt['l3_indication_to_atc'])}")

    # Coverage
    with open('data/pipeline_data.json', 'r', encoding='utf-8') as f:
        drugs = json.load(f)['merged_drugs']
    ind_count = Counter()
    for name, drug in drugs.items():
        indications = drug.get('indications', [])
        if isinstance(indications, str):
            for ind in indications.split('|'):
                c = ind.strip().lower()
                if c and len(c) > 2: ind_count[c] += 1
        elif isinstance(indications, list):
            for ind in indications:
                c = (ind.get('condition','') if isinstance(ind, dict) else str(ind)).strip().lower()
                if c and len(c) > 2: ind_count[c] += 1

    covered = sum(1 for ind in ind_count if ind in rt['l2_disease_categories'])
    print(f"Coverage: {covered}/{len(ind_count)} = {covered/len(ind_count)*100:.1f}%")


if __name__ == "__main__":
    main()

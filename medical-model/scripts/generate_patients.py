"""患者数据生成器 — 基于pipeline_data.json真实药物/疾病分布生成模拟患者

生成策略:
1. 疾病分布: 基于indication_map中460种条件的药物覆盖数加权采样
   - 主病(primary_disease): 高频常见病(发烧/高血压/皮炎/痛风等)
   - 慢性病(chronic_diseases): 从高血压/糖尿病/心脏病/哮喘/癫痫等慢性病中采样
2. 过敏: 约15%患者有过敏记录, 从contraindication_map中allergy_type类采样
3. 当前用药: 约60%患者正在服药, 从merged_drugs中按疾病相关药物采样
4. 年龄/性别/BMI: 基于真实人口分布

生成数量: 300患者 → 智能配对预估 ~10K样本 → medium配置(embed=8, hidden=[64,32])
"""

import json
import random
import logging
import sys
from pathlib import Path
from collections import Counter
from typing import Dict, List, Any, Set

logger = logging.getLogger(__name__)

# 常见疾病权重 (基于indication_map药物覆盖数)
COMMON_DISEASES = [
    'fever', 'hypertension', 'atopic dermatitis', 'gout',
    'gastroesophageal reflux disease', 'back pain',
    'bacterial urinary tract infection', 'pharyngitis due to streptococcus pyogenes',
    'vertigo', 'flatulence', 'acute bacterial sinusitis',
    'hypercholesterolemia', 'depression', 'pneumonia',
    'anxiety', 'insomnia', 'headache', 'sore throat',
    'common cold', 'allergy', 'diarrhea', 'nausea',
    'urinary tract infection', 'bacterial skin infection',
    'asthma', 'diabetes', 'epilepsy', 'arrhythmia',
    'heart failure', 'edema', 'joint pain', 'nerve pain',
]

# 慢性病候选 (需要长期用药)
CHRONIC_DISEASES = [
    'hypertension', 'diabetes', 'type 2 diabetes',
    'heart failure', 'asthma', 'epilepsy',
    'depression', 'anxiety', 'gout',
    'hypercholesterolemia', 'arrhythmia',
    'rheumatoid arthritis', 'osteoporosis',
    'hypothyroidism', 'psoriasis',
    'chronic obstructive pulmonary disease',
    'chronic kidney disease', 'atrial fibrillation',
]

# 常见过敏原
COMMON_ALLERGENS = [
    'penicillin', 'sulfonamides', 'aspirin', 'nsaid',
    'cephalosporins', 'latex', 'iodine', 'codeine',
    'morphine', 'amoxicillin', 'tetracycline',
    'fluoroquinolones', 'macrolides', 'trimethoprim',
]

# 年龄分布 (模拟医院门诊年龄分布)
AGE_WEIGHTS = [
    (0, 9, 0.03),    # 儿科
    (10, 19, 0.04),  # 青少年
    (20, 29, 0.08),  # 青年
    (30, 39, 0.12),  # 青壮年
    (40, 49, 0.18),  # 中年
    (50, 59, 0.22),  # 中老年 (门诊主力)
    (60, 69, 0.18),  # 老年
    (70, 79, 0.10),  # 高龄
    (80, 95, 0.05),  # 老年
]

# 性别分布
GENDER_WEIGHTS = {'MALE': 0.48, 'FEMALE': 0.50, 'UNKNOWN': 0.02}

# BMI分布 (中国成年人)
BMI_WEIGHTS = [
    (15.0, 18.4, 0.08),   # 偏瘦
    (18.5, 23.9, 0.45),   # 正常
    (24.0, 27.9, 0.32),   # 超重
    (28.0, 35.0, 0.15),   # 肥胖
]


def _weighted_choice(weighted_items: List[tuple], rng: random.Random) -> Any:
    """加权随机选择"""
    items, weights = zip(*[(item, w) for item, w, *_ in weighted_items]
                          if len(weighted_items) > 0 and len(weighted_items[0]) == 2
                          else [(item, w) for *_, item, w in weighted_items])
    # Handle (value, weight) or (low, high, weight) format
    parsed = []
    for item in weighted_items:
        if len(item) == 2:
            parsed.append(item)
        elif len(item) == 3:
            parsed.append(item)

    total = sum(w for *_, w in parsed)
    r = rng.random() * total
    cumulative = 0
    for item in parsed:
        if len(item) == 2:
            val, w = item
        else:
            val, _, w = item
        cumulative += w
        if r <= cumulative:
            return val
    return parsed[-1][0] if len(parsed[-1]) == 2 else (parsed[-1][0], parsed[-1][1])


def _sample_age(rng: random.Random) -> int:
    """按年龄分布采样"""
    r = rng.random()
    cumulative = 0
    for low, high, weight in AGE_WEIGHTS:
        cumulative += weight
        if r <= cumulative:
            return rng.randint(low, high)
    return rng.randint(60, 75)


def _sample_gender(rng: random.Random) -> str:
    """按性别分布采样"""
    r = rng.random()
    cumulative = 0
    for gender, weight in GENDER_WEIGHTS.items():
        cumulative += weight
        if r <= cumulative:
            return gender
    return 'UNKNOWN'


def _sample_bmi(rng: random.Random) -> float:
    """按BMI分布采样"""
    r = rng.random()
    cumulative = 0
    for low, high, weight in BMI_WEIGHTS:
        cumulative += weight
        if r <= cumulative:
            return round(rng.uniform(low, high), 1)
    return round(rng.uniform(18.5, 24.0), 1)


def _sample_conditions(
    pool: List[str],
    count: int,
    condition_drug_count: Dict[str, int],
    rng: random.Random,
) -> List[str]:
    """从疾病池中按药物覆盖数加权采样

    高频疾病(覆盖药物多)被采样的概率更高, 符合真实门诊分布
    """
    if count <= 0:
        return []

    weights = []
    for cond in pool:
        # 用药物覆盖数作为权重, 最小1避免零权重
        w = condition_drug_count.get(cond.lower(), 1)
        weights.append(w)

    total = sum(weights)
    probs = [w / total for w in weights]

    # 加权无放回采样
    selected = []
    available = list(range(len(pool)))
    available_probs = list(probs)

    for _ in range(min(count, len(pool))):
        if not available:
            break
        # 重新归一化
        psum = sum(available_probs)
        if psum <= 0:
            idx = rng.choice(available)
        else:
            norm_probs = [p / psum for p in available_probs]
            idx = rng.choices(available, weights=norm_probs, k=1)[0]

        selected.append(pool[idx])
        # 移除已选
        remove_at = available.index(idx)
        available.pop(remove_at)
        available_probs.pop(remove_at)

    return selected


def _find_drugs_for_condition(
    condition: str,
    indication_map: Dict[str, List[Dict]],
    drug_names: List[str],
    rng: random.Random,
    count: int = 2,
) -> List[str]:
    """找到治疗某疾病的药物, 随机选择count个"""
    matching_drugs = []
    cond_lower = condition.lower()

    for drug_name in drug_names:
        indications = indication_map.get(drug_name, [])
        for ind in indications:
            if isinstance(ind, dict):
                ind_cond = str(ind.get('condition', '')).lower()
            else:
                ind_cond = str(ind).lower()
            if cond_lower in ind_cond or ind_cond in cond_lower:
                matching_drugs.append(drug_name)
                break

    if not matching_drugs:
        return []

    count = min(count, len(matching_drugs))
    return rng.sample(matching_drugs, count)


def generate_patients(
    pipeline_data: Dict[str, Any],
    num_patients: int = 500,
    seed: int = 42,
) -> List[Dict[str, Any]]:
    """生成模拟患者数据

    Args:
        pipeline_data: pipeline_data.json完整数据
        num_patients: 患者数量
        seed: 随机种子
    Returns:
        患者记录列表
    """
    rng = random.Random(seed)

    # 提取数据
    indication_map = pipeline_data.get('indication_map', {})
    contraindication_map = pipeline_data.get('contraindication_map', {})
    merged_drugs = pipeline_data.get('merged_drugs', {})

    # 药物名列表
    drug_names = []
    for drug_id, drug in merged_drugs.items():
        gn = drug.get('generic_name', drug.get('name', ''))
        if gn:
            drug_names.append(gn)

    # 条件→药物覆盖数映射
    condition_drug_count: Dict[str, int] = Counter()
    for drug_name, indications in indication_map.items():
        for ind in indications:
            if isinstance(ind, dict):
                cond = str(ind.get('condition', '')).lower()
            else:
                cond = str(ind).lower()
            if cond:
                condition_drug_count[cond] += 1

    # 从contraindication_map中收集allergy_type名
    allergy_names: Set[str] = set()
    for drug_name, contras in contraindication_map.items():
        for c in contras:
            if c.get('contraindication_type') == 'allergy_type':
                aname = c.get('contraindication_name', '')
                if aname:
                    allergy_names.add(aname)
    allergy_name_list = sorted(allergy_names)

    # 扩展常见疾病池: 从indication_map取高频条件
    all_conditions = sorted(condition_drug_count.keys())
    high_freq_conditions = [
        c for c in all_conditions
        if condition_drug_count[c] >= 15
    ]

    # 合并为primary disease候选池
    primary_pool = list(set(COMMON_DISEASES + high_freq_conditions))

    patients = []

    for i in range(num_patients):
        patient_id = i + 1
        age = _sample_age(rng)
        gender = _sample_gender(rng)
        bmi = _sample_bmi(rng)

        # 主病: 1-2个
        num_primary = rng.choices([1, 2], weights=[0.6, 0.4])[0]
        diseases = _sample_conditions(
            primary_pool, num_primary, condition_drug_count, rng
        )

        # 慢性病: 0-3个 (年龄越大越可能有慢性病)
        if age >= 60:
            num_chronic = rng.choices([0, 1, 2, 3], weights=[0.15, 0.35, 0.35, 0.15])[0]
        elif age >= 40:
            num_chronic = rng.choices([0, 1, 2, 3], weights=[0.30, 0.40, 0.20, 0.10])[0]
        elif age >= 20:
            num_chronic = rng.choices([0, 1, 2], weights=[0.55, 0.35, 0.10])[0]
        else:
            num_chronic = rng.choices([0, 1], weights=[0.80, 0.20])[0]

        chronic_diseases = _sample_conditions(
            CHRONIC_DISEASES, num_chronic, condition_drug_count, rng
        )

        # 过敏: 约15%患者有过敏
        allergies = []
        if rng.random() < 0.15:
            # 1-2个过敏原
            num_allergies = rng.choices([1, 2], weights=[0.75, 0.25])[0]
            # 优先从常见过敏原中选
            if allergy_name_list:
                # 混合常见过敏原和全部过敏原
                pool = list(set(COMMON_ALLERGENS + [
                    a.lower() for a in allergy_name_list[:100]
                ]))
                pool = [a for a in pool if a]
                if pool:
                    allergies = rng.sample(pool, min(num_allergies, len(pool)))

        # 当前用药: 60%患者正在服药
        current_medications = []
        if rng.random() < 0.60:
            # 从主病+慢性病对应的药物中选
            all_patient_conditions = diseases + chronic_diseases
            med_candidates = []
            for cond in all_patient_conditions:
                cond_drugs = _find_drugs_for_condition(
                    cond, indication_map, drug_names, rng, count=3
                )
                med_candidates.extend(cond_drugs)

            # 去重
            med_candidates = list(dict.fromkeys(med_candidates))

            if med_candidates:
                num_meds = rng.choices([1, 2, 3, 4], weights=[0.30, 0.35, 0.25, 0.10])[0]
                num_meds = min(num_meds, len(med_candidates))
                current_medications = rng.sample(med_candidates, num_meds)

        # 肾功能/肝功能: 绝大多数正常
        renal = rng.choices(
            ['normal', 'mild_impairment', 'moderate_impairment', 'severe_impairment', 'unknown'],
            weights=[0.70, 0.10, 0.05, 0.02, 0.13]
        )[0]

        hepatic = rng.choices(
            ['normal', 'mild_impairment', 'moderate_impairment', 'severe_impairment', 'unknown'],
            weights=[0.75, 0.08, 0.04, 0.01, 0.12]
        )[0]

        patient = {
            'id': patient_id,
            'patient_id': f'P{patient_id:04d}',
            'age': age,
            'gender': gender,
            'bmi': bmi,
            'diseases': diseases,
            'chronic_diseases': chronic_diseases,
            'allergies': allergies,
            'current_medications': current_medications,
            'renal_function': renal,
            'hepatic_function': hepatic,
        }
        patients.append(patient)

    return patients


def main():
    """主入口: 生成患者数据并写入pipeline_data.json"""
    logging.basicConfig(level=logging.INFO)

    pipeline_path = Path('data/pipeline_data.json')
    if not pipeline_path.exists():
        logger.error(f'pipeline_data.json not found at {pipeline_path}')
        sys.exit(1)

    logger.info(f'Loading pipeline_data.json...')
    with open(pipeline_path, 'r', encoding='utf-8') as f:
        pipeline_data = json.load(f)

    logger.info(
        f'Loaded: {len(pipeline_data.get("merged_drugs", {}))} drugs, '
        f'{len(pipeline_data.get("indication_map", {}))} indication entries'
    )

    # 生成300患者
    num_patients = 500
    logger.info(f'Generating {num_patients} simulated patients...')
    patients = generate_patients(pipeline_data, num_patients=num_patients, seed=42)

    # 统计
    age_dist = Counter()
    gender_dist = Counter()
    disease_count = Counter()
    chronic_count = Counter()
    allergy_pct = 0
    med_pct = 0

    for p in patients:
        age_dist[f"{(p['age'] // 10) * 10}s"] += 1
        gender_dist[p['gender']] += 1
        for d in p['diseases']:
            disease_count[d] += 1
        for d in p['chronic_diseases']:
            chronic_count[d] += 1
        if p['allergies']:
            allergy_pct += 1
        if p['current_medications']:
            med_pct += 1

    logger.info(f'Age distribution: {dict(sorted(age_dist.items()))}')
    logger.info(f'Gender distribution: {dict(gender_dist)}')
    logger.info(f'Allergy rate: {allergy_pct}/{num_patients} ({allergy_pct/num_patients*100:.1f}%)')
    logger.info(f'Medication rate: {med_pct}/{num_patients} ({med_pct/num_patients*100:.1f}%)')
    logger.info(f'Top 10 diseases: {disease_count.most_common(10)}')
    logger.info(f'Top 10 chronic: {chronic_count.most_common(10)}')

    # 计算平均每患者疾病/用药数
    avg_diseases = sum(len(p['diseases']) for p in patients) / num_patients
    avg_chronic = sum(len(p['chronic_diseases']) for p in patients) / num_patients
    avg_meds = sum(len(p['current_medications']) for p in patients) / num_patients
    logger.info(
        f'Avg per patient: {avg_diseases:.1f} diseases, '
        f'{avg_chronic:.1f} chronic, {avg_meds:.1f} medications'
    )

    # 写入pipeline_data.json
    pipeline_data['patient_records'] = patients
    logger.info(f'Writing {num_patients} patients to pipeline_data.json...')

    with open(pipeline_path, 'w', encoding='utf-8') as f:
        json.dump(pipeline_data, f, ensure_ascii=False, indent=None)

    # 验证
    file_size_mb = pipeline_path.stat().st_size / (1024 * 1024)
    logger.info(f'pipeline_data.json updated: {file_size_mb:.1f} MB')

    # 预估训练样本量
    total_drugs = len(pipeline_data.get('merged_drugs', {}))
    est_indication_pairs = sum(
        len(p['diseases']) + len(p['chronic_diseases'])
        for p in patients
    ) * 3  # 每个条件平均3个匹配药物
    est_contra_pairs = int(num_patients * 0.3 * 2)  # 约30%患者有禁忌配对
    est_random_pairs = num_patients * 10  # 每患者10个随机中性样本
    est_total = est_indication_pairs + est_contra_pairs + est_random_pairs
    logger.info(
        f'Estimated training samples: ~{est_total} '
        f'(indication:{est_indication_pairs} + contra:{est_contra_pairs} + random:{est_random_pairs})'
    )

    try:
        from app.pipeline.schema import get_data_size_category
        category = get_data_size_category(est_total)
        logger.info(f'Data size category: {category}')
    except ImportError:
        if est_total < 5000:
            category = 'small'
        elif est_total < 30000:
            category = 'medium'
        else:
            category = 'large'
        logger.info(f'Data size category: {category} (fallback)')

    logger.info('Done! Patient data generation complete.')


if __name__ == '__main__':
    main()

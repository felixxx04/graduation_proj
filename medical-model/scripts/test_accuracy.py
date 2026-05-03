"""验证用药推荐准确性 — 44种疾病跨科室测试"""
import requests, sys, json

TEST_CASES = [
    # 呼吸系统
    ('common cold', 28, 'MALE', '普通感冒'),
    ('allergic rhinitis', 25, 'MALE', '过敏性鼻炎'),
    ('bronchitis', 45, 'MALE', '支气管炎'),
    ('sinusitis', 35, 'FEMALE', '鼻窦炎'),
    # 心血管
    ('arrhythmia', 62, 'MALE', '心律失常'),
    ('atrial fibrillation', 68, 'FEMALE', '房颤'),
    ('heart failure', 70, 'MALE', '心力衰竭'),
    ('deep vein thrombosis', 55, 'FEMALE', '深静脉血栓'),
    # 消化系统
    ('gastroesophageal reflux disease', 40, 'MALE', '胃食管反流'),
    ('peptic ulcer', 50, 'MALE', '消化性溃疡'),
    ('irritable bowel syndrome', 32, 'FEMALE', '肠易激综合征'),
    ('constipation', 65, 'FEMALE', '便秘'),
    # 神经系统
    ('migraine', 30, 'FEMALE', '偏头痛'),
    ('epilepsy', 25, 'MALE', '癫痫'),
    ('parkinson disease', 70, 'MALE', '帕金森病'),
    ('nerve pain', 50, 'FEMALE', '神经痛'),
    # 精神科
    ('anxiety', 28, 'FEMALE', '焦虑症'),
    ('bipolar disorder', 35, 'MALE', '双相障碍'),
    ('insomnia', 45, 'FEMALE', '失眠'),
    ('panic disorder', 30, 'MALE', '惊恐障碍'),
    # 内分泌
    ('hypercholesterolemia', 55, 'MALE', '高胆固醇血症'),
    ('gout', 50, 'MALE', '痛风'),
    ('hypothyroidism', 40, 'FEMALE', '甲减'),
    ('obesity', 35, 'FEMALE', '肥胖症'),
    # 感染
    ('bacterial urinary tract infection', 28, 'FEMALE', '尿路感染'),
    ('pharyngitis due to streptococcus pyogenes', 12, 'MALE', '链球菌咽炎'),
    ('bacterial skin infection', 40, 'MALE', '皮肤感染'),
    ('otitis media', 5, 'FEMALE', '中耳炎'),
    # 骨科/风湿
    ('osteoarthritis', 65, 'FEMALE', '骨关节炎'),
    ('rheumatoid arthritis', 50, 'FEMALE', '类风湿关节炎'),
    ('back pain', 42, 'MALE', '背痛'),
    ('osteoporosis', 68, 'FEMALE', '骨质疏松'),
    # 皮肤
    ('atopic dermatitis', 8, 'MALE', '特应性皮炎'),
    ('acne', 18, 'FEMALE', '痤疮'),
    ('psoriasis', 40, 'MALE', '银屑病'),
    ('eczema', 22, 'FEMALE', '湿疹'),
    # 眼科
    ('glaucoma', 65, 'MALE', '青光眼'),
    ('conjunctivitis', 15, 'FEMALE', '结膜炎'),
    ('age-related macular degeneration', 72, 'MALE', '黄斑变性'),
    # 其他
    ('anemia', 35, 'FEMALE', '贫血'),
    ('allergy', 20, 'MALE', '过敏'),
    ('benign prostatic hyperplasia', 60, 'MALE', '前列腺增生'),
    ('menopause', 52, 'FEMALE', '更年期'),
    ('erectile dysfunction', 55, 'MALE', '勃起功能障碍'),
]

results = {'passed': [], 'failed': [], 'errors': []}
total = len(TEST_CASES)

for idx, (disease, age, gender, label) in enumerate(TEST_CASES):
    try:
        # Reset budget
        requests.post('http://localhost:8001/model/privacy/budget/reset?userId=default',
                      json={'epsilon_budget': 10.0, 'delta': 1e-5}, timeout=10)
        # Predict
        r = requests.post('http://localhost:8001/model/predict', json={
            'diseases': disease, 'age': age, 'gender': gender,
            'topK': 3, 'userId': 'default', 'dpEnabled': False,
        }, timeout=120)
        data = r.json()
        drugs = data.get('selected', [])

        matched_drugs = [d for d in drugs if d.get('matchedDisease') and d.get('matchedDisease') != '未知']
        top_drug = drugs[0] if drugs else None

        if matched_drugs:
            results['passed'].append(label)
            tag = 'PASS'
        else:
            results['failed'].append(label)
            tag = 'FAIL'

        # Show top drug info
        if top_drug:
            cat = top_drug.get('category', '?')[:25]
            matched = top_drug.get('matchedDisease', '?') or '-'
            score = top_drug['score']
            print(f'[{tag}] {idx+1:2d}/{total} {label:<12} ({disease[:30]}) '
                  f'-> {cat:<25} | matched={matched[:20]} | score={score:.3f}')
        else:
            print(f'[FAIL] {idx+1:2d}/{total} {label} -> NO DRUGS')

    except Exception as e:
        results['errors'].append(label)
        print(f'[ERR] {idx+1:2d}/{total} {label} -> {e}')

# Summary
print(f'\n{"="*60}')
print(f'  PASS: {len(results["passed"])}/{total} ({len(results["passed"])/total*100:.0f}%)')
if results['failed']:
    print(f'  FAIL: {results["failed"]}')
if results['errors']:
    print(f'  ERR:  {results["errors"]}')
print(f'{"="*60}')

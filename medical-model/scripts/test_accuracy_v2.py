"""验证用药推荐准确性 — 60种疾病跨科室测试 v2"""
import requests, sys, time

TEST_CASES = [
    # === 呼吸系统 (6) ===
    ('common cold', 28, 'MALE', '普通感冒'),
    ('allergic rhinitis', 25, 'MALE', '过敏性鼻炎'),
    ('bronchitis', 45, 'MALE', '支气管炎'),
    ('sinusitis', 35, 'FEMALE', '鼻窦炎'),
    ('tonsillitis', 15, 'FEMALE', '扁桃体炎'),
    ('influenza', 40, 'MALE', '流感'),
    # === 心血管 (6) ===
    ('arrhythmia', 62, 'MALE', '心律失常'),
    ('atrial fibrillation', 68, 'FEMALE', '房颤'),
    ('heart failure', 70, 'MALE', '心力衰竭'),
    ('deep vein thrombosis', 55, 'FEMALE', '深静脉血栓'),
    ('angina pectoris', 60, 'MALE', '心绞痛'),
    ('myocardial infarction', 58, 'MALE', '心肌梗死'),
    # === 消化系统 (6) ===
    ('gastroesophageal reflux disease', 40, 'MALE', '胃食管反流'),
    ('peptic ulcer', 50, 'MALE', '消化性溃疡'),
    ('irritable bowel syndrome', 32, 'FEMALE', '肠易激综合征'),
    ('constipation', 65, 'FEMALE', '便秘'),
    ('crohn disease', 30, 'MALE', '克罗恩病'),
    ('ulcerative colitis', 35, 'FEMALE', '溃疡性结肠炎'),
    # === 神经系统 (6) ===
    ('migraine', 30, 'FEMALE', '偏头痛'),
    ('epilepsy', 25, 'MALE', '癫痫'),
    ('parkinson disease', 70, 'MALE', '帕金森病'),
    ('nerve pain', 50, 'FEMALE', '神经痛'),
    ('alzheimer disease', 72, 'FEMALE', '阿尔茨海默病'),
    ('multiple sclerosis', 35, 'FEMALE', '多发性硬化'),
    # === 精神科 (6) ===
    ('anxiety', 28, 'FEMALE', '焦虑症'),
    ('bipolar disorder', 35, 'MALE', '双相障碍'),
    ('insomnia', 45, 'FEMALE', '失眠'),
    ('panic disorder', 30, 'MALE', '惊恐障碍'),
    ('schizophrenia', 30, 'MALE', '精神分裂症'),
    ('adhd', 12, 'MALE', '注意力缺陷多动障碍'),
    # === 内分泌 (6) ===
    ('hypercholesterolemia', 55, 'MALE', '高胆固醇血症'),
    ('gout', 50, 'MALE', '痛风'),
    ('hypothyroidism', 40, 'FEMALE', '甲减'),
    ('obesity', 35, 'FEMALE', '肥胖症'),
    ('hyperthyroidism', 42, 'FEMALE', '甲亢'),
    ('osteoporosis', 68, 'FEMALE', '骨质疏松'),
    # === 感染 (6) ===
    ('urinary tract infection', 28, 'FEMALE', '尿路感染'),
    ('strep throat', 12, 'MALE', '链球菌咽炎'),
    ('bacterial skin infection', 40, 'MALE', '皮肤感染'),
    ('otitis media', 5, 'FEMALE', '中耳炎'),
    ('pneumonia', 65, 'MALE', '肺炎'),
    ('hiv infection', 35, 'MALE', 'HIV感染'),
    # === 骨科/风湿 (6) ===
    ('osteoarthritis', 65, 'FEMALE', '骨关节炎'),
    ('rheumatoid arthritis', 50, 'FEMALE', '类风湿关节炎'),
    ('back pain', 42, 'MALE', '背痛'),
    ('gouty arthritis', 52, 'MALE', '痛风性关节炎'),
    ('fibromyalgia', 38, 'FEMALE', '纤维肌痛'),
    ('ankylosing spondylitis', 35, 'MALE', '强直性脊柱炎'),
    # === 皮肤 (5) ===
    ('atopic dermatitis', 8, 'MALE', '特应性皮炎'),
    ('acne', 18, 'FEMALE', '痤疮'),
    ('psoriasis', 40, 'MALE', '银屑病'),
    ('eczema', 22, 'FEMALE', '湿疹'),
    ('rosacea', 38, 'FEMALE', '玫瑰痤疮'),
    # === 眼科 (3) ===
    ('glaucoma', 65, 'MALE', '青光眼'),
    ('conjunctivitis', 15, 'FEMALE', '结膜炎'),
    ('dry eye syndrome', 55, 'FEMALE', '干眼症'),
    # === 泌尿/男科 (4) ===
    ('benign prostatic hyperplasia', 60, 'MALE', '前列腺增生'),
    ('erectile dysfunction', 55, 'MALE', '勃起功能障碍'),
    ('overactive bladder', 50, 'FEMALE', '膀胱过度活动症'),
    ('chronic kidney disease', 55, 'MALE', '慢性肾病'),
]

results = {'passed': [], 'failed': [], 'errors': []}
total = len(TEST_CASES)
start_time = time.time()

for idx, (disease, age, gender, label) in enumerate(TEST_CASES):
    try:
        requests.post('http://localhost:8001/model/privacy/budget/reset?userId=default',
                      json={'epsilon_budget': 10.0, 'delta': 1e-5}, timeout=10)
        r = requests.post('http://localhost:8001/model/predict', json={
            'diseases': disease, 'age': age, 'gender': gender,
            'topK': 3, 'userId': 'default', 'dpEnabled': False,
        }, timeout=120)
        data = r.json()
        drugs = data.get('selected', [])
        matched_drugs = [d for d in drugs if d.get('matchedDisease') and d.get('matchedDisease') != '未知']
        top = drugs[0] if drugs else None

        if matched_drugs:
            results['passed'].append(label)
            tag = 'PASS'
        else:
            results['failed'].append(label)
            tag = 'FAIL'

        if top:
            cat = top.get('category', '?')[:25]
            matched = top.get('matchedDisease', '-') or '-'
            score = top['score']
            print(f'[{tag}] {idx+1:2d}/{total} {label:<14} ({disease[:30]}) '
                  f'-> {cat:<25} | matched={matched[:22]} | score={score:.3f}')
        else:
            print(f'[FAIL] {idx+1:2d}/{total} {label} -> NO DRUGS')

    except Exception as e:
        results['errors'].append(label)
        print(f'[ERR] {idx+1:2d}/{total} {label} -> {e}')

elapsed = time.time() - start_time
print(f'\n{"="*65}')
print(f'  PASS: {len(results["passed"])}/{total} ({len(results["passed"])/total*100:.0f}%)')
print(f'  Time:  {elapsed:.0f}s')
if results['failed']:
    print(f'  FAIL: {results["failed"]}')
if results['errors']:
    print(f'  ERR:  {results["errors"]}')
print(f'{"="*65}')

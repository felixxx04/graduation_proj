"""
从数据库生成训练数据
连接 MySQL 数据库，读取患者健康记录和药物数据，生成训练样本
"""
import json
import os
import sys
from typing import List, Dict, Any
import numpy as np

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql
from pymysql.cursors import DictCursor

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'Jin200426',  # 根据实际情况填写
    'database': 'medical_recommendation',
    'charset': 'utf8mb4',
    'cursorclass': DictCursor
}


def get_connection():
    """获取数据库连接"""
    return pymysql.connect(**DB_CONFIG)


def fetch_patients(conn) -> List[Dict[str, Any]]:
    """获取患者健康记录"""
    with conn.cursor() as cursor:
        sql = """
        SELECT
            p.id as patient_id,
            p.gender,
            phr.age,
            phr.height,
            phr.weight,
            phr.chronic_diseases,
            phr.allergies,
            phr.current_medications,
            phr.symptoms
        FROM patient p
        JOIN patient_health_record phr ON p.id = phr.patient_id
        WHERE phr.is_latest = TRUE
        """
        cursor.execute(sql)
        return cursor.fetchall()


def fetch_drugs(conn) -> List[Dict[str, Any]]:
    """获取药物数据"""
    with conn.cursor() as cursor:
        sql = """
        SELECT
            id, name, category, indications, contraindications,
            side_effects, interactions, typical_dosage, typical_frequency
        FROM drug
        """
        cursor.execute(sql)
        return cursor.fetchall()


def fetch_recommendations(conn) -> List[Dict[str, Any]]:
    """获取历史推荐记录（作为训练标签）"""
    with conn.cursor() as cursor:
        sql = """
        SELECT
            r.patient_id,
            r.input_data,
            r.result_data
        FROM recommendation r
        WHERE r.patient_id IS NOT NULL
        """
        cursor.execute(sql)
        return cursor.fetchall()


def parse_json_field(value):
    """解析 JSON 字段"""
    if value is None:
        return []
    if isinstance(value, str):
        try:
            return json.loads(value)
        except:
            return []
    return value


def create_feature_vector(patient: Dict, drug: Dict, feature_dim: int = 200) -> np.ndarray:
    """
    创建患者-药物特征向量

    特征组成：
    - 患者特征：年龄、性别、疾病、过敏史
    - 药物特征：类别、适应症匹配度
    - 交互特征：疾病-适应症匹配
    """
    features = np.zeros(feature_dim, dtype=np.float32)
    idx = 0

    # 1. 年龄特征 (归一化)
    age = patient.get('age', 45) or 45
    features[idx] = age / 100.0
    idx += 1

    # 2. 性别特征
    gender = patient.get('gender', 'MALE') or 'MALE'
    features[idx] = 1.0 if gender == 'MALE' else 0.0
    idx += 1

    # 3. 身高体重 BMI
    height = float(patient.get('height', 170) or 170) / 100.0
    weight = float(patient.get('weight', 65) or 65)
    bmi = weight / (height * height) if height > 0 else 22.0
    features[idx] = bmi / 40.0
    idx += 1

    # 4. 慢性疾病特征 (one-hot, 最多 20 种)
    diseases = parse_json_field(patient.get('chronic_diseases'))
    disease_vocab = ['高血压', '糖尿病', '冠心病', '高血脂', '哮喘',
                     '慢性肾病', '肝炎', '胃溃疡', '关节炎', '抑郁症',
                     '甲状腺疾病', '贫血', '痛风', '骨质疏松', '心衰',
                     '脑梗塞', '帕金森', '癫痫', '肿瘤', '其他']
    for i, d in enumerate(disease_vocab):
        if i + idx < feature_dim:
            features[idx + i] = 1.0 if d in diseases else 0.0
    idx += len(disease_vocab)

    # 5. 过敏史特征 (最多 10 种)
    allergies = parse_json_field(patient.get('allergies'))
    allergy_vocab = ['青霉素', '磺胺类', '阿司匹林', '碘造影剂', '头孢类',
                     '链霉素', '万古霉素', '喹诺酮类', '四环素类', '其他']
    for i, a in enumerate(allergy_vocab):
        if i + idx < feature_dim:
            features[idx + i] = 1.0 if a in allergies else 0.0
    idx += len(allergy_vocab)

    # 6. 当前用药特征 (最多 10 种常见药物类别)
    current_meds = parse_json_field(patient.get('current_medications'))
    med_categories = ['降糖药', '降压药', '降脂药', '抗血小板药', '抗凝药',
                      '胃药', '心脏病药', '甲状腺药', '抗抑郁药', '其他']
    # 简单判断用药类别
    for i, cat in enumerate(med_categories):
        if i + idx < feature_dim:
            # 根据药物名称判断类别
            features[idx + i] = 0.0
    idx += len(med_categories)

    # 7. 药物特征
    # 药物类别 (one-hot, 8 类)
    drug_category = drug.get('category', '') or ''
    category_map = {'降糖药': 0, '降压药': 1, '降脂药': 2, '抗血小板药': 3,
                    '消化系统用药': 4, '心血管用药': 5, '抗感染药': 6, '其他': 7}
    cat_idx = category_map.get(drug_category, 7)
    for i in range(8):
        if i + idx < feature_dim:
            features[idx + i] = 1.0 if i == cat_idx else 0.0
    idx += 8

    # 8. 疾病-适应症匹配特征
    drug_indications = parse_json_field(drug.get('indications'))
    match_score = 0.0
    for disease in diseases:
        for indication in drug_indications:
            if disease in indication or indication in disease:
                match_score += 1.0
    match_score = min(match_score / max(len(diseases), 1), 1.0)
    features[idx] = match_score
    idx += 1

    # 9. 禁忌症冲突特征
    contraindications = parse_json_field(drug.get('contraindications'))
    conflict_score = 0.0
    for disease in diseases:
        for contra in contraindications:
            if disease in contra or contra in disease:
                conflict_score += 1.0
    conflict_score = min(conflict_score / max(len(diseases), 1), 1.0)
    features[idx] = conflict_score
    idx += 1

    # 10. 过敏冲突特征
    side_effects = parse_json_field(drug.get('side_effects'))
    allergy_conflict = 0.0
    for allergy in allergies:
        for effect in side_effects:
            if allergy in str(effect) or str(effect) in allergy:
                allergy_conflict += 1.0
    allergy_conflict = min(allergy_conflict / max(len(allergies), 1), 1.0)
    features[idx] = allergy_conflict
    idx += 1

    # 填充剩余特征为随机小噪声
    while idx < feature_dim:
        features[idx] = np.random.randn() * 0.01
        idx += 1

    return features


def create_label(patient: Dict, drug: Dict) -> float:
    """
    创建训练标签

    基于规则计算匹配分数：
    - 适应症匹配：+0.3
    - 禁忌症冲突：-0.5
    - 过敏冲突：-0.3
    - 当前用药相互作用：-0.2
    """
    label = 0.5  # 基础分数

    diseases = parse_json_field(patient.get('chronic_diseases'))
    allergies = parse_json_field(patient.get('allergies'))
    current_meds = parse_json_field(patient.get('current_medications'))

    indications = parse_json_field(drug.get('indications'))
    contraindications = parse_json_field(drug.get('contraindications'))
    side_effects = parse_json_field(drug.get('side_effects'))
    interactions = parse_json_field(drug.get('interactions'))

    # 适应症匹配
    for disease in diseases:
        for ind in indications:
            if disease in ind or ind in disease:
                label += 0.3
                break

    # 禁忌症冲突
    for disease in diseases:
        for contra in contraindications:
            if disease in contra or contra in disease:
                label -= 0.5

    # 过敏冲突
    for allergy in allergies:
        if allergy != '无':
            for effect in side_effects:
                if allergy in str(effect):
                    label -= 0.3

    # 药物相互作用
    for med in current_meds:
        for interaction in interactions:
            if med in str(interaction):
                label -= 0.2

    # 归一化到 [0, 1]
    label = max(0.0, min(1.0, label))

    return label


def generate_training_data(
    num_samples: int = None,
    feature_dim: int = 200,
    output_path: str = None
) -> List[Dict[str, Any]]:
    """
    从数据库生成训练数据

    Args:
        num_samples: 生成样本数量，None 表示生成所有可能的样本
        feature_dim: 特征维度
        output_path: 输出文件路径

    Returns:
        训练样本列表
    """
    print("正在连接数据库...")
    conn = get_connection()

    try:
        # 获取数据
        print("正在获取患者数据...")
        patients = fetch_patients(conn)
        print(f"获取到 {len(patients)} 条患者记录")

        print("正在获取药物数据...")
        drugs = fetch_drugs(conn)
        print(f"获取到 {len(drugs)} 条药物记录")

        print("正在获取历史推荐记录...")
        recommendations = fetch_recommendations(conn)
        print(f"获取到 {len(recommendations)} 条推荐记录")

        # 生成训练样本
        samples = []
        total_pairs = len(patients) * len(drugs)
        print(f"正在生成训练样本（最多 {total_pairs} 条）...")

        count = 0
        for patient in patients:
            for drug in drugs:
                # 创建特征向量
                features = create_feature_vector(patient, drug, feature_dim)

                # 创建标签
                label = create_label(patient, drug)

                # 只保留有意义的样本（标签不为 0.5）
                if label != 0.5 or np.random.random() < 0.1:
                    samples.append({
                        'patient_id': patient['patient_id'],
                        'drug_id': drug['id'],
                        'features': features.tolist(),
                        'label': label
                    })
                    count += 1

                    if num_samples and count >= num_samples:
                        break

            if num_samples and count >= num_samples:
                break

        print(f"生成了 {len(samples)} 条训练样本")

        # 保存到文件
        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'samples': samples,
                    'metadata': {
                        'total_count': len(samples),
                        'feature_dim': feature_dim,
                        'patients_count': len(patients),
                        'drugs_count': len(drugs)
                    }
                }, f, ensure_ascii=False, indent=2)
            print(f"训练数据已保存到 {output_path}")

        return samples

    finally:
        conn.close()


if __name__ == '__main__':
    # 生成训练数据
    output_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'data', 'training_data.json'
    )

    samples = generate_training_data(
        num_samples=None,  # 生成所有可能的样本
        feature_dim=200,
        output_path=output_path
    )

    # 统计标签分布
    labels = [s['label'] for s in samples]
    positive = sum(1 for l in labels if l > 0.5)
    negative = sum(1 for l in labels if l < 0.5)
    neutral = len(labels) - positive - negative

    print(f"\n标签分布:")
    print(f"  正样本 (label > 0.5): {positive}")
    print(f"  负样本 (label < 0.5): {negative}")
    print(f"  中性样本 (label = 0.5): {neutral}")

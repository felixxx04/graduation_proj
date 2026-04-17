"""
从数据库生成训练数据

连接 MySQL 数据库，读取患者健康记录和药物数据，生成训练样本。

改进点：
- 数据库凭据从环境变量读取，不再硬编码
- 使用共享词汇表常量，确保与预测时特征一致
- 使用 _safe_parse_json_list 替代裸 json.loads + bare except
- 添加连接重试与异常处理
- 使用 logging 替代 print
"""

import json
import os
import sys
import time
import logging
from typing import List, Dict, Any, Optional

import numpy as np

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.data.preprocessor import (
    DISEASE_VOCAB,
    ALLERGY_VOCAB,
    DRUG_CATEGORY_MAP,
    FEATURE_DIM,
    _safe_parse_json_list,
)

logger = logging.getLogger(__name__)

# 从环境变量读取数据库配置
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': int(os.environ.get('DB_PORT', '3306')),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': os.environ.get('DB_NAME', 'medical_recommendation'),
    'charset': os.environ.get('DB_CHARSET', 'utf8mb4'),
}

MAX_RETRIES = 3
RETRY_BACKOFF = 2.0


def get_connection():
    """获取数据库连接（带重试）"""
    import pymysql
    from pymysql.cursors import DictCursor

    config = {**DB_CONFIG, 'cursorclass': DictCursor}
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            conn = pymysql.connect(**config)
            logger.info(f"Database connection established (attempt {attempt})")
            return conn
        except pymysql.Error as e:
            last_error = e
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF ** (attempt - 1)
                logger.warning(f"DB connection failed (attempt {attempt}), retrying in {wait:.1f}s: {e}")
                time.sleep(wait)
            else:
                logger.error(f"DB connection failed after {MAX_RETRIES} retries: {e}")

    raise ConnectionError(f"Failed to connect to database after {MAX_RETRIES} retries: {last_error}")


def fetch_patients(conn) -> List[Dict[str, Any]]:
    """获取患者健康记录"""
    try:
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
    except Exception as e:
        logger.error(f"Failed to fetch patients: {e}")
        return []


def fetch_drugs(conn) -> List[Dict[str, Any]]:
    """获取药物数据"""
    try:
        with conn.cursor() as cursor:
            sql = """
            SELECT
                id, name, category, indications, contraindications,
                side_effects, interactions, typical_dosage, typical_frequency
            FROM drug
            """
            cursor.execute(sql)
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Failed to fetch drugs: {e}")
        return []


def fetch_recommendations(conn) -> List[Dict[str, Any]]:
    """获取历史推荐记录（作为训练标签）"""
    try:
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
    except Exception as e:
        logger.error(f"Failed to fetch recommendations: {e}")
        return []


def create_feature_vector(patient: Dict, drug: Dict, feature_dim: int = FEATURE_DIM) -> np.ndarray:
    """
    创建患者-药物特征向量（与 predictor 中的特征构造一致）

    特征组成：
    - 患者特征：年龄、性别、BMI、疾病、过敏史
    - 药物特征：类别、适应症匹配度
    - 交互特征：禁忌症冲突、过敏冲突
    """
    features = np.zeros(feature_dim, dtype=np.float32)
    idx = 0

    # 1. 年龄特征 (归一化)
    age = patient.get('age', 45) or 45
    try:
        age = float(age)
    except (TypeError, ValueError):
        age = 45
    features[idx] = min(age / 100.0, 1.5)
    idx += 1

    # 2. 性别特征
    gender = patient.get('gender', '男') or '男'
    features[idx] = 1.0 if gender in ('男', 'MALE', 'male') else 0.0
    idx += 1

    # 3. 身高体重 BMI
    try:
        height = float(patient.get('height', 170) or 170) / 100.0
        weight = float(patient.get('weight', 65) or 65)
        bmi = weight / (height * height) if height > 0 else 22.0
    except (TypeError, ValueError):
        bmi = 22.0
    features[idx] = bmi / 40.0
    idx += 1

    # 4. 慢性疾病特征 (使用共享词汇表)
    diseases = _safe_parse_json_list(patient.get('chronic_diseases'))
    disease_vocab_map = {d: i for i, d in enumerate(DISEASE_VOCAB)}
    for d in diseases:
        if d in disease_vocab_map:
            v_idx = disease_vocab_map[d]
            if idx + v_idx < feature_dim:
                features[idx + v_idx] = 1.0
        elif '其他' in disease_vocab_map:
            features[idx + disease_vocab_map['其他']] = 1.0
    idx += len(DISEASE_VOCAB)

    # 5. 过敏史特征 (使用共享词汇表)
    allergies = _safe_parse_json_list(patient.get('allergies'))
    allergy_vocab_map = {a: i for i, a in enumerate(ALLERGY_VOCAB)}
    for a in allergies:
        if a == '无':
            continue
        if a in allergy_vocab_map:
            v_idx = allergy_vocab_map[a]
            if idx + v_idx < feature_dim:
                features[idx + v_idx] = 1.0
        elif '其他' in allergy_vocab_map:
            features[idx + allergy_vocab_map['其他']] = 1.0
    idx += len(ALLERGY_VOCAB)

    # 6. 当前用药特征 (10 维占位)
    idx += 10

    # 7. 药物类别特征 (使用共享映射)
    drug_category = str(drug.get('category', '') or '')
    cat_idx = DRUG_CATEGORY_MAP.get(drug_category, DRUG_CATEGORY_MAP.get('其他', len(DRUG_CATEGORY_MAP) - 1))
    for i in range(len(DRUG_CATEGORY_MAP)):
        if idx + i < feature_dim:
            features[idx + i] = 1.0 if i == cat_idx else 0.0
    idx += len(DRUG_CATEGORY_MAP)

    # 8. 疾病-适应症匹配特征
    drug_indications = _safe_parse_json_list(drug.get('indications'))
    match_score = 0.0
    for disease in diseases:
        for indication in drug_indications:
            if disease in indication or indication in disease:
                match_score += 1.0
    match_score = min(match_score / max(len(diseases), 1), 1.0)
    if idx < feature_dim:
        features[idx] = match_score
    idx += 1

    # 9. 禁忌症冲突特征
    contraindications = _safe_parse_json_list(drug.get('contraindications'))
    conflict_score = 0.0
    for disease in diseases:
        for contra in contraindications:
            if disease in contra or contra in disease:
                conflict_score += 1.0
    conflict_score = min(conflict_score / max(len(diseases), 1), 1.0)
    if idx < feature_dim:
        features[idx] = conflict_score
    idx += 1

    # 10. 过敏冲突特征
    side_effects = _safe_parse_json_list(drug.get('side_effects'))
    allergy_conflict = 0.0
    for allergy in allergies:
        if allergy == '无':
            continue
        for effect in side_effects:
            if allergy in str(effect) or str(effect) in allergy:
                allergy_conflict += 1.0
    allergy_conflict = min(allergy_conflict / max(len(allergies), 1), 1.0)
    if idx < feature_dim:
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
    label = 0.5

    diseases = _safe_parse_json_list(patient.get('chronic_diseases'))
    allergies = _safe_parse_json_list(patient.get('allergies'))
    current_meds = _safe_parse_json_list(patient.get('current_medications'))

    indications = _safe_parse_json_list(drug.get('indications'))
    contraindications = _safe_parse_json_list(drug.get('contraindications'))
    side_effects = _safe_parse_json_list(drug.get('side_effects'))
    interactions = _safe_parse_json_list(drug.get('interactions'))

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

    return max(0.0, min(1.0, label))


def generate_training_data(
    num_samples: Optional[int] = None,
    feature_dim: int = FEATURE_DIM,
    output_path: Optional[str] = None,
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
    logger.info("Connecting to database...")
    conn = get_connection()

    try:
        patients = fetch_patients(conn)
        logger.info(f"Fetched {len(patients)} patient records")

        drugs = fetch_drugs(conn)
        logger.info(f"Fetched {len(drugs)} drug records")

        recommendations = fetch_recommendations(conn)
        logger.info(f"Fetched {len(recommendations)} recommendation records")

        if not patients or not drugs:
            logger.warning("Insufficient data: need both patients and drugs")
            return []

        samples = []
        total_pairs = len(patients) * len(drugs)
        logger.info(f"Generating training samples (max {total_pairs} pairs)...")

        count = 0
        for patient in patients:
            for drug in drugs:
                features = create_feature_vector(patient, drug, feature_dim)
                label = create_label(patient, drug)

                if label != 0.5 or np.random.random() < 0.1:
                    samples.append({
                        'patient_id': patient['patient_id'],
                        'drug_id': drug['id'],
                        'features': features.tolist(),
                        'label': label,
                    })
                    count += 1

                    if num_samples and count >= num_samples:
                        break

            if num_samples and count >= num_samples:
                break

        logger.info(f"Generated {len(samples)} training samples")

        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'samples': samples,
                    'metadata': {
                        'total_count': len(samples),
                        'feature_dim': feature_dim,
                        'patients_count': len(patients),
                        'drugs_count': len(drugs),
                    },
                }, f, ensure_ascii=False, indent=2)
            logger.info(f"Training data saved to {output_path}")

        return samples

    finally:
        conn.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

    output_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'data', 'training_data.json',
    )

    samples = generate_training_data(
        num_samples=None,
        feature_dim=FEATURE_DIM,
        output_path=output_path,
    )

    labels = [s['label'] for s in samples]
    positive = sum(1 for l in labels if l > 0.5)
    negative = sum(1 for l in labels if l < 0.5)
    neutral = len(labels) - positive - negative

    logger.info(f"Label distribution: positive={positive}, negative={negative}, neutral={neutral}")

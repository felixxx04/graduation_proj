#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模拟患者数据生成脚本
生成随机的患者信息和健康档案数据，用于开发和测试
"""

import random
import json
from datetime import datetime, timedelta, date
from typing import List, Dict, Any

try:
    from faker import Faker
except ImportError:
    print("请先安装 faker: pip install faker")
    exit(1)

try:
    import mysql.connector
except ImportError:
    print("请先安装 mysql-connector-python: pip install mysql-connector-python")
    exit(1)


DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '',
    'database': 'medical_recommendation',
    'charset': 'utf8mb4'
}

faker = Faker('zh_CN')

CHRONIC_DISEASES = [
    '2型糖尿病', '高血压', '冠心病', '高脂血症', '慢性肾病',
    '慢性支气管炎', '哮喘', '类风湿关节炎', '骨质疏松症',
    '甲状腺功能减退', '痛风', '慢性胃炎', '胃溃疡',
    '心力衰竭', '房颤', '脑梗死后遗症', '帕金森病'
]

ALLERGIES = [
    '青霉素', '磺胺类', '头孢菌素', '阿司匹林', '碘造影剂',
    '花粉', '尘螨', '海鲜', '牛奶', '鸡蛋', '花生', '坚果',
    '无'
]

MEDICATIONS = [
    '二甲双胍缓释片', '氨氯地平片', '阿托伐他汀钙片', '阿司匹林肠溶片',
    '氯沙坦钾片', '奥美拉唑肠溶胶囊', '氯吡格雷片', '美托洛尔片',
    '硝苯地平控释片', '瑞舒伐他汀钙片', '格列美脲片', '阿卡波糖片'
]

SYMPTOMS = [
    '头晕', '头痛', '乏力', '胸闷', '心悸', '气短',
    '咳嗽', '咳痰', '恶心', '呕吐', '腹痛', '腹泻',
    '便秘', '食欲不振', '失眠', '多梦', '关节疼痛',
    '腰背疼痛', '下肢水肿', '视物模糊'
]


def random_date(start_year: int = 1940, end_year: int = 2005) -> date:
    """生成随机出生日期"""
    start = date(start_year, 1, 1)
    end = date(end_year, 12, 31)
    delta = end - start
    random_days = random.randint(0, delta.days)
    return start + timedelta(days=random_days)


def random_items(items: List[str], min_count: int = 0, max_count: int = 3) -> List[str]:
    """从列表中随机选择若干项"""
    count = random.randint(min_count, max_count)
    return random.sample(items, min(count, len(items)))


def generate_patient() -> Dict[str, Any]:
    """生成单个患者数据"""
    gender = random.choice(['男', '女'])
    birth_date = random_date()
    
    age = (date.today() - birth_date).days // 365
    if age >= 60:
        disease_count = random.randint(1, 4)
    elif age >= 40:
        disease_count = random.randint(0, 3)
    else:
        disease_count = random.randint(0, 2)
    
    chronic_diseases = random.sample(CHRONIC_DISEASES, min(disease_count, len(CHRONIC_DISEASES)))
    
    allergies = random_items(ALLERGIES, 0, 2)
    if '无' in allergies:
        allergies = ['无']
    
    if chronic_diseases:
        med_count = random.randint(1, min(len(chronic_diseases) + 1, 5))
    else:
        med_count = random.randint(0, 2)
    
    current_medications = random.sample(MEDICATIONS, min(med_count, len(MEDICATIONS)))
    
    symptoms = random_items(SYMPTOMS, 0, 4)
    
    if gender == '男':
        height = round(random.uniform(160, 185), 1)
        weight = round(random.uniform(55, 90), 1)
    else:
        height = round(random.uniform(150, 170), 1)
        weight = round(random.uniform(45, 75), 1)
    
    return {
        'name': faker.name(),
        'gender': gender,
        'birth_date': birth_date,
        'phone': faker.phone_number(),
        'age': age,
        'height': height,
        'weight': weight,
        'blood_type': random.choice(['A', 'B', 'AB', 'O', '未知']),
        'chronic_diseases': chronic_diseases,
        'allergies': allergies,
        'current_medications': current_medications,
        'medical_history': f"患者有{len(chronic_diseases)}种慢性病史，日常规律用药。" if chronic_diseases else "既往体健。",
        'symptoms': '、'.join(symptoms) if symptoms else '无特殊不适'
    }


def insert_patients(patients: List[Dict[str, Any]], db_config: Dict[str, Any]) -> int:
    """批量插入患者数据"""
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    
    inserted_count = 0
    
    try:
        for patient in patients:
            patient_sql = """
                INSERT INTO patient (name, gender, birth_date, phone)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(patient_sql, (
                patient['name'],
                patient['gender'],
                patient['birth_date'],
                patient['phone']
            ))
            
            patient_id = cursor.lastrowid
            
            record_sql = """
                INSERT INTO patient_health_record 
                (patient_id, record_date, age, height, weight, blood_type,
                 chronic_diseases, allergies, current_medications, medical_history, symptoms)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(record_sql, (
                patient_id,
                date.today(),
                patient['age'],
                patient['height'],
                patient['weight'],
                patient['blood_type'],
                json.dumps(patient['chronic_diseases'], ensure_ascii=False),
                json.dumps(patient['allergies'], ensure_ascii=False),
                json.dumps(patient['current_medications'], ensure_ascii=False),
                patient['medical_history'],
                patient['symptoms']
            ))
            
            inserted_count += 1
        
        conn.commit()
        print(f"成功插入 {inserted_count} 条患者数据")
        
    except Exception as e:
        conn.rollback()
        print(f"插入失败: {e}")
        raise
    finally:
        cursor.close()
        conn.close()
    
    return inserted_count


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='生成模拟患者数据')
    parser.add_argument('-n', '--count', type=int, default=50, help='生成患者数量（默认50）')
    parser.add_argument('--host', default='localhost', help='MySQL主机')
    parser.add_argument('--port', type=int, default=3306, help='MySQL端口')
    parser.add_argument('-u', '--user', default='root', help='MySQL用户名')
    parser.add_argument('-p', '--password', default='', help='MySQL密码')
    parser.add_argument('-d', '--database', default='medical_recommendation', help='数据库名')
    
    args = parser.parse_args()
    
    DB_CONFIG.update({
        'host': args.host,
        'port': args.port,
        'user': args.user,
        'password': args.password,
        'database': args.database
    })
    
    print(f"正在生成 {args.count} 条模拟患者数据...")
    
    patients = [generate_patient() for _ in range(args.count)]
    
    print("\n示例数据:")
    for i, p in enumerate(patients[:3], 1):
        print(f"\n患者 {i}:")
        print(f"  姓名: {p['name']}")
        print(f"  性别: {p['gender']}, 年龄: {p['age']}岁")
        print(f"  慢性病: {', '.join(p['chronic_diseases']) or '无'}")
        print(f"  过敏史: {', '.join(p['allergies'])}")
        print(f"  当前用药: {', '.join(p['current_medications']) or '无'}")
    
    print(f"\n正在插入数据库...")
    insert_patients(patients, DB_CONFIG)


if __name__ == '__main__':
    main()

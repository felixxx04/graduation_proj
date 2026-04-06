"""
数据标准化模块
将 OpenFDA 数据转换为系统统一格式
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# 常见药物中文映射
DRUG_NAME_CN = {
    # 降糖药
    "metformin": "二甲双胍",
    "glipizide": "格列吡嗪",
    "glyburide": "格列本脲",
    "sitagliptin": "西格列汀",
    "linagliptin": "利格列汀",
    "empagliflozin": "恩格列净",
    "dapagliflozin": "达格列净",
    "insulin": "胰岛素",

    # 降压药
    "amlodipine": "氨氯地平",
    "lisinopril": "赖诺普利",
    "losartan": "氯沙坦",
    "valsartan": "缬沙坦",
    "enalapril": "依那普利",
    "nifedipine": "硝苯地平",
    "atenolol": "阿替洛尔",
    "metoprolol": "美托洛尔",
    "carvedilol": "卡维地洛",
    "hydrochlorothiazide": "氢氯噻嗪",

    # 降脂药
    "atorvastatin": "阿托伐他汀",
    "simvastatin": "辛伐他汀",
    "rosuvastatin": "瑞舒伐他汀",
    "pravastatin": "普伐他汀",
    "ezetimibe": "依折麦布",

    # 抗血小板药
    "aspirin": "阿司匹林",
    "clopidogrel": "氯吡格雷",
    "warfarin": "华法林",
    "rivaroxaban": "利伐沙班",
    "dabigatran": "达比加群",

    # 抗生素
    "amoxicillin": "阿莫西林",
    "azithromycin": "阿奇霉素",
    "ciprofloxacin": "环丙沙星",
    "doxycycline": "多西环素",
    "cephalexin": "头孢氨苄",

    # 消化系统
    "omeprazole": "奥美拉唑",
    "esomeprazole": "埃索美拉唑",
    "pantoprazole": "泮托拉唑",
    "ranitidine": "雷尼替丁",
    "famotidine": "法莫替丁",

    # 呼吸系统
    "salbutamol": "沙丁胺醇",
    "salmeterol": "沙美特罗",
    "fluticasone": "氟替卡松",
    "montelukast": "孟鲁司特",

    # 神经系统
    "sertraline": "舍曲林",
    "fluoxetine": "氟西汀",
    "escitalopram": "艾司西酞普兰",
    "diazepam": "地西泮",
    "lorazepam": "劳拉西泮",
    "gabapentin": "加巴喷丁",
    "pregabalin": "普瑞巴林",

    # 镇痛药
    "ibuprofen": "布洛芬",
    "naproxen": "萘普生",
    "acetaminophen": "对乙酰氨基酚",
    "paracetamol": "扑热息痛",
    "tramadol": "曲马多",

    # 激素类
    "levothyroxine": "左甲状腺素",
    "prednisone": "泼尼松",
    "prednisolone": "泼尼松龙",

    # 其他
    "allopurinol": "别嘌醇",
    "colchicine": "秋水仙碱",
    "finasteride": "非那雄胺",
    "tamsulosin": "坦索罗辛",
    "sildenafil": "西地那非",
}

# 药物分类中文映射
DRUG_CATEGORY_CN = {
    "antidiabetic": "降糖药",
    "antihypertensive": "降压药",
    "lipid-modifying": "降脂药",
    "antithrombotic": "抗血栓药",
    "antiplatelet": "抗血小板药",
    "anticoagulant": "抗凝药",
    "antibiotic": "抗生素",
    "antibacterial": "抗菌药",
    "gastrointestinal": "消化系统用药",
    "antiulcer": "抗溃疡药",
    "respiratory": "呼吸系统用药",
    "bronchodilator": "支气管扩张剂",
    "nervous system": "神经系统用药",
    "antidepressant": "抗抑郁药",
    "anxiolytic": "抗焦虑药",
    "analgesic": "镇痛药",
    "anti-inflammatory": "抗炎药",
    "hormone": "激素类药",
    "thyroid": "甲状腺用药",
    "corticosteroid": "皮质激素",
    "cardiovascular": "心血管用药",
    "diuretic": "利尿剂",
    "beta-blocker": "β受体阻滞剂",
    "ace inhibitor": "ACE抑制剂",
    "arb": "ARB类",
    "statin": "他汀类",
}

# 常见适应症中文映射
INDICATION_CN = {
    "diabetes": "糖尿病",
    "diabetes mellitus": "糖尿病",
    "type 2 diabetes": "2型糖尿病",
    "hypertension": "高血压",
    "high blood pressure": "高血压",
    "hyperlipidemia": "高脂血症",
    "hypercholesterolemia": "高胆固醇血症",
    "coronary artery disease": "冠心病",
    "angina": "心绞痛",
    "heart failure": "心力衰竭",
    "atrial fibrillation": "房颤",
    "thrombosis": "血栓",
    "infection": "感染",
    "bacterial infection": "细菌感染",
    "gastric ulcer": "胃溃疡",
    "gerd": "胃食管反流",
    "asthma": "哮喘",
    "copd": "慢阻肺",
    "depression": "抑郁症",
    "anxiety": "焦虑症",
    "pain": "疼痛",
    "inflammation": "炎症",
    "arthritis": "关节炎",
    "hypothyroidism": "甲状腺功能减退",
    "gout": "痛风",
}


@dataclass
class NormalizedDrug:
    """标准化药物数据"""
    id: str
    name_en: str
    name_cn: str
    generic_name_en: str
    generic_name_cn: str
    category: str
    indications: List[str]
    contraindications: List[str]
    warnings: List[str]
    adverse_reactions: List[str]
    interactions: List[str]
    dosage: str
    mechanism: str
    route: str
    pregnancy_category: str
    source: str = "OpenFDA"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DataNormalizer:
    """数据标准化器"""

    def __init__(self):
        self.drug_name_cn = DRUG_NAME_CN
        self.drug_category_cn = DRUG_CATEGORY_CN
        self.indication_cn = INDICATION_CN

    def normalize(self, drug_data: Dict[str, Any]) -> Optional[NormalizedDrug]:
        """
        标准化药物数据

        Args:
            drug_data: 原始药物数据（来自 OpenFDA）

        Returns:
            标准化的药物数据，如果数据不完整则返回 None
        """
        # 提取基本信息
        generic_name = drug_data.get('generic_name', '').lower()
        brand_names = drug_data.get('brand_names', [])

        # 确定药物名称
        name_en = generic_name or (brand_names[0] if brand_names else '')
        if not name_en:
            logger.warning("Drug without name, skipping")
            return None

        # 生成唯一 ID
        fda_id = drug_data.get('fda_id', '') or f"drug_{hash(name_en) % 100000}"

        # 获取中文名称
        name_cn = self._get_chinese_name(name_en)

        # 标准化分类
        category = self._normalize_category(drug_data)

        # 标准化适应症
        indications = self._normalize_indications(drug_data.get('indications', []))

        # 标准化禁忌症
        contraindications = self._normalize_contraindications(drug_data.get('contraindications', []))

        # 标准化警告
        warnings = self._normalize_warnings(drug_data.get('warnings', []))

        # 标准化不良反应
        adverse_reactions = self._normalize_adverse_reactions(drug_data.get('adverse_reactions', []))

        # 标准化相互作用
        interactions = self._normalize_interactions(drug_data.get('interactions', []))

        return NormalizedDrug(
            id=fda_id,
            name_en=name_en,
            name_cn=name_cn,
            generic_name_en=generic_name,
            generic_name_cn=name_cn,
            category=category,
            indications=indications,
            contraindications=contraindications,
            warnings=warnings,
            adverse_reactions=adverse_reactions,
            interactions=interactions,
            dosage=drug_data.get('dosage', '')[:500],
            mechanism=drug_data.get('mechanism', '')[:500],
            route=', '.join(drug_data.get('route', [])),
            pregnancy_category=drug_data.get('pregnancy_category', ''),
            source="OpenFDA"
        )

    def _get_chinese_name(self, name_en: str) -> str:
        """获取药物中文名称"""
        name_lower = name_en.lower()

        # 直接匹配
        if name_lower in self.drug_name_cn:
            return self.drug_name_cn[name_lower]

        # 模糊匹配
        for key, cn_name in self.drug_name_cn.items():
            if key in name_lower or name_lower in key:
                return cn_name

        # 无法翻译则返回英文名
        return name_en

    def _normalize_category(self, drug_data: Dict) -> str:
        """标准化药物分类"""
        product_types = drug_data.get('product_type', [])
        routes = drug_data.get('route', [])

        # 从产品类型推断分类
        for pt in product_types:
            pt_lower = pt.lower()
            for key, cn in self.drug_category_cn.items():
                if key in pt_lower:
                    return cn

        # 无法确定则返回"其他"
        return "其他"

    def _normalize_indications(self, indications: List[str]) -> List[str]:
        """标准化适应症"""
        result = []

        for indication in indications[:5]:  # 限制数量
            text = indication.lower()

            # 尝试匹配中文
            for key, cn in self.indication_cn.items():
                if key in text:
                    result.append(cn)
                    break
            else:
                # 提取关键短语
                sentences = re.split(r'[.,;]', indication)
                for sentence in sentences[:2]:
                    sentence = sentence.strip()
                    if len(sentence) > 10 and len(sentence) < 200:
                        result.append(sentence)
                        break

        return list(set(result))[:5]  # 去重并限制数量

    def _normalize_contraindications(self, contraindications: List[str]) -> List[str]:
        """标准化禁忌症"""
        result = []
        for contra in contraindications[:3]:
            # 提取关键信息
            text = contra.strip()
            if len(text) > 10:
                result.append(text[:200])
        return result

    def _normalize_warnings(self, warnings: List[str]) -> List[str]:
        """标准化警告"""
        result = []
        for warning in warnings[:3]:
            text = warning.strip()
            if len(text) > 10:
                result.append(text[:200])
        return result

    def _normalize_adverse_reactions(self, reactions: List[str]) -> List[str]:
        """标准化不良反应"""
        result = []
        for reaction in reactions[:5]:
            text = reaction.strip()
            if len(text) > 5:
                result.append(text[:100])
        return result

    def _normalize_interactions(self, interactions: List[str]) -> List[str]:
        """标准化药物相互作用"""
        result = []
        for interaction in interactions[:3]:
            text = interaction.strip()
            if len(text) > 10:
                result.append(text[:200])
        return result

    def normalize_batch(self, drugs: List[Dict[str, Any]]) -> List[NormalizedDrug]:
        """
        批量标准化

        Args:
            drugs: 药物数据列表

        Returns:
            标准化后的药物列表
        """
        normalized = []
        seen_names = set()

        for drug in drugs:
            result = self.normalize(drug)
            if result and result.name_en not in seen_names:
                seen_names.add(result.name_en)
                normalized.append(result)

        logger.info(f"Normalized {len(normalized)} drugs from {len(drugs)} input")
        return normalized

    def to_mysql_format(self, drug: NormalizedDrug) -> Dict[str, Any]:
        """
        转换为 MySQL 存储格式

        Args:
            drug: 标准化药物数据

        Returns:
            MySQL 兼容的字典格式
        """
        return {
            'drug_code': drug.id,
            'name': drug.name_cn or drug.name_en,
            'generic_name': drug.generic_name_cn or drug.generic_name_en,
            'category': drug.category,
            'indications': json.dumps(drug.indications, ensure_ascii=False),
            'contraindications': json.dumps(drug.contraindications, ensure_ascii=False),
            'side_effects': json.dumps(drug.adverse_reactions, ensure_ascii=False),
            'interactions': json.dumps(drug.interactions, ensure_ascii=False),
            'typical_dosage': drug.dosage,
            'typical_frequency': '',  # 需要后续补充
            'description': drug.mechanism,
        }


if __name__ == "__main__":
    # 测试代码
    normalizer = DataNormalizer()

    # 模拟 OpenFDA 数据
    test_data = {
        'fda_id': 'test-001',
        'generic_name': 'Metformin',
        'brand_names': ['Glucophage', 'Glucophage XR'],
        'indications': [
            'Type 2 diabetes mellitus',
            'Management of blood glucose levels'
        ],
        'contraindications': [
            'Severe renal impairment',
            'Hypersensitivity to metformin'
        ],
        'warnings': ['Lactic acidosis risk'],
        'adverse_reactions': ['Diarrhea', 'Nausea', 'Abdominal pain'],
        'interactions': ['Contrast agents', 'Alcohol'],
        'dosage': '500mg twice daily',
        'mechanism': 'Decreases hepatic glucose production',
        'route': ['oral'],
        'product_type': ['HUMAN PRESCRIPTION DRUG'],
        'pregnancy_category': 'B'
    }

    result = normalizer.normalize(test_data)
    if result:
        print(f"Name: {result.name_cn} ({result.name_en})")
        print(f"Category: {result.category}")
        print(f"Indications: {result.indications}")
        print(f"Contraindications: {result.contraindications}")
        print(f"Adverse reactions: {result.adverse_reactions}")

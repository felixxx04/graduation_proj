"""
数据标准化模块
将 OpenFDA 数据转换为系统统一格式

改进点：
- 输入校验与防御性编程
- 配置与映射表解耦
- 移除 logging.basicConfig 冲突
- 细化标准化逻辑
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


# 常见药物中文映射
DRUG_NAME_CN: Dict[str, str] = {
    "metformin": "二甲双胍", "glipizide": "格列吡嗪", "glyburide": "格列本脲",
    "sitagliptin": "西格列汀", "linagliptin": "利格列汀", "empagliflozin": "恩格列净",
    "dapagliflozin": "达格列净", "insulin": "胰岛素",
    "amlodipine": "氨氯地平", "lisinopril": "赖诺普利", "losartan": "氯沙坦",
    "valsartan": "缬沙坦", "enalapril": "依那普利", "nifedipine": "硝苯地平",
    "atenolol": "阿替洛尔", "metoprolol": "美托洛尔", "carvedilol": "卡维地洛",
    "hydrochlorothiazide": "氢氯噻嗪",
    "atorvastatin": "阿托伐他汀", "simvastatin": "辛伐他汀", "rosuvastatin": "瑞舒伐他汀",
    "pravastatin": "普伐他汀", "ezetimibe": "依折麦布",
    "aspirin": "阿司匹林", "clopidogrel": "氯吡格雷", "warfarin": "华法林",
    "rivaroxaban": "利伐沙班", "dabigatran": "达比加群",
    "amoxicillin": "阿莫西林", "azithromycin": "阿奇霉素", "ciprofloxacin": "环丙沙星",
    "doxycycline": "多西环素", "cephalexin": "头孢氨苄",
    "omeprazole": "奥美拉唑", "esomeprazole": "埃索美拉唑", "pantoprazole": "泮托拉唑",
    "ranitidine": "雷尼替丁", "famotidine": "法莫替丁",
    "salbutamol": "沙丁胺醇", "salmeterol": "沙美特罗", "fluticasone": "氟替卡松",
    "montelukast": "孟鲁司特",
    "sertraline": "舍曲林", "fluoxetine": "氟西汀", "escitalopram": "艾司西酞普兰",
    "diazepam": "地西泮", "lorazepam": "劳拉西泮", "gabapentin": "加巴喷丁",
    "pregabalin": "普瑞巴林",
    "ibuprofen": "布洛芬", "naproxen": "萘普生", "acetaminophen": "对乙酰氨基酚",
    "paracetamol": "扑热息痛", "tramadol": "曲马多",
    "levothyroxine": "左甲状腺素", "prednisone": "泼尼松", "prednisolone": "泼尼松龙",
    "allopurinol": "别嘌醇", "colchicine": "秋水仙碱", "finasteride": "非那雄胺",
    "tamsulosin": "坦索罗辛", "sildenafil": "西地那非",
}

DRUG_CATEGORY_CN: Dict[str, str] = {
    "antidiabetic": "降糖药", "antihypertensive": "降压药", "lipid-modifying": "降脂药",
    "antithrombotic": "抗血栓药", "antiplatelet": "抗血小板药", "anticoagulant": "抗凝药",
    "antibiotic": "抗生素", "antibacterial": "抗菌药", "gastrointestinal": "消化系统用药",
    "antiulcer": "抗溃疡药", "respiratory": "呼吸系统用药", "bronchodilator": "支气管扩张剂",
    "nervous system": "神经系统用药", "antidepressant": "抗抑郁药", "anxiolytic": "抗焦虑药",
    "analgesic": "镇痛药", "anti-inflammatory": "抗炎药", "hormone": "激素类药",
    "thyroid": "甲状腺用药", "corticosteroid": "皮质激素", "cardiovascular": "心血管用药",
    "diuretic": "利尿剂", "beta-blocker": "β受体阻滞剂", "ace inhibitor": "ACE抑制剂",
    "arb": "ARB类", "statin": "他汀类",
}

INDICATION_CN: Dict[str, str] = {
    "diabetes": "糖尿病", "diabetes mellitus": "糖尿病", "type 2 diabetes": "2型糖尿病",
    "hypertension": "高血压", "high blood pressure": "高血压",
    "hyperlipidemia": "高脂血症", "hypercholesterolemia": "高胆固醇血症",
    "coronary artery disease": "冠心病", "angina": "心绞痛", "heart failure": "心力衰竭",
    "atrial fibrillation": "房颤", "thrombosis": "血栓",
    "infection": "感染", "bacterial infection": "细菌感染",
    "gastric ulcer": "胃溃疡", "gerd": "胃食管反流",
    "asthma": "哮喘", "copd": "慢阻肺",
    "depression": "抑郁症", "anxiety": "焦虑症",
    "pain": "疼痛", "inflammation": "炎症", "arthritis": "关节炎",
    "hypothyroidism": "甲状腺功能减退", "gout": "痛风",
}

# 标准化字段数量限制
MAX_INDICATIONS = 5
MAX_CONTRAINDICATIONS = 3
MAX_WARNINGS = 3
MAX_ADVERSE_REACTIONS = 5
MAX_INTERACTIONS = 3
MAX_TEXT_LENGTH = 500
MAX_SHORT_TEXT_LENGTH = 200
MAX_TINY_TEXT_LENGTH = 100


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
    """数据标准化器，支持配置解耦"""

    def __init__(
        self,
        drug_name_cn: Optional[Dict[str, str]] = None,
        drug_category_cn: Optional[Dict[str, str]] = None,
        indication_cn: Optional[Dict[str, str]] = None,
    ):
        """
        初始化标准化器

        Args:
            drug_name_cn: 药物名称中英文映射，默认使用内置映射
            drug_category_cn: 药物分类中英文映射
            indication_cn: 适应症中英文映射
        """
        self.drug_name_cn = drug_name_cn or DRUG_NAME_CN
        self.drug_category_cn = drug_category_cn or DRUG_CATEGORY_CN
        self.indication_cn = indication_cn or INDICATION_CN

    def normalize(self, drug_data: Dict[str, Any]) -> Optional[NormalizedDrug]:
        """
        标准化药物数据

        Args:
            drug_data: 原始药物数据

        Returns:
            标准化的药物数据，数据不完整则返回 None
        """
        if not isinstance(drug_data, dict):
            logger.warning(f"Invalid drug_data type: {type(drug_data)}, expected dict")
            return None

        # 提取基本信息
        generic_name = str(drug_data.get('generic_name', '') or '').lower().strip()
        brand_names = drug_data.get('brand_names', [])
        if not isinstance(brand_names, list):
            brand_names = [str(brand_names)] if brand_names else []

        name_en = generic_name or (brand_names[0] if brand_names else '')
        if not name_en:
            logger.warning("Drug without name, skipping")
            return None

        # 生成唯一 ID
        fda_id = drug_data.get('fda_id', '') or f"drug_{abs(hash(name_en)) % 100000}"

        name_cn = self._get_chinese_name(name_en)
        category = self._normalize_category(drug_data)
        indications = self._normalize_indications(drug_data.get('indications', []))
        contraindications = self._normalize_contraindications(drug_data.get('contraindications', []))
        warnings = self._normalize_warnings(drug_data.get('warnings', []))
        adverse_reactions = self._normalize_adverse_reactions(drug_data.get('adverse_reactions', []))
        interactions = self._normalize_interactions(drug_data.get('interactions', []))

        dosage = str(drug_data.get('dosage', '') or '')[:MAX_TEXT_LENGTH]
        mechanism = str(drug_data.get('mechanism', '') or '')[:MAX_TEXT_LENGTH]

        routes = drug_data.get('route', [])
        if isinstance(routes, list):
            route = ', '.join(str(r) for r in routes)
        else:
            route = str(routes)

        pregnancy_category = str(drug_data.get('pregnancy_category', '') or '')

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
            dosage=dosage,
            mechanism=mechanism,
            route=route,
            pregnancy_category=pregnancy_category,
            source="OpenFDA"
        )

    def _get_chinese_name(self, name_en: str) -> str:
        """获取药物中文名称（精确匹配优先，模糊匹配次之）"""
        name_lower = name_en.lower()

        # 精确匹配
        if name_lower in self.drug_name_cn:
            return self.drug_name_cn[name_lower]

        # 模糊匹配（仅短名称匹配长名称，避免误匹配）
        for key, cn_name in self.drug_name_cn.items():
            if key in name_lower and len(key) >= 4:
                return cn_name
            if name_lower in key and len(name_lower) >= 4:
                return cn_name

        return name_en

    def _normalize_category(self, drug_data: Dict) -> str:
        """标准化药物分类"""
        product_types = drug_data.get('product_type', [])
        if not isinstance(product_types, list):
            product_types = [str(product_types)] if product_types else []

        for pt in product_types:
            pt_lower = str(pt).lower()
            for key, cn in self.drug_category_cn.items():
                if key in pt_lower:
                    return cn

        return "其他"

    def _normalize_indications(self, indications: Any) -> List[str]:
        """标准化适应症"""
        if not isinstance(indications, list):
            indications = [str(indications)] if indications else []

        result: List[str] = []
        for indication in indications[:MAX_INDICATIONS]:
            text = str(indication).lower()

            matched = False
            for key, cn in self.indication_cn.items():
                if key in text:
                    result.append(cn)
                    matched = True
                    break

            if not matched:
                sentences = re.split(r'[.,;]', str(indication))
                for sentence in sentences[:2]:
                    sentence = sentence.strip()
                    if 10 < len(sentence) < MAX_SHORT_TEXT_LENGTH:
                        result.append(sentence)
                        break

        return list(set(result))[:MAX_INDICATIONS]

    def _normalize_contraindications(self, contraindications: Any) -> List[str]:
        """标准化禁忌症"""
        if not isinstance(contraindications, list):
            contraindications = [str(contraindications)] if contraindications else []

        result: List[str] = []
        for contra in contraindications[:MAX_CONTRAINDICATIONS]:
            text = str(contra).strip()
            if len(text) > 10:
                result.append(text[:MAX_SHORT_TEXT_LENGTH])
        return result

    def _normalize_warnings(self, warnings: Any) -> List[str]:
        """标准化警告"""
        if not isinstance(warnings, list):
            warnings = [str(warnings)] if warnings else []

        result: List[str] = []
        for warning in warnings[:MAX_WARNINGS]:
            text = str(warning).strip()
            if len(text) > 10:
                result.append(text[:MAX_SHORT_TEXT_LENGTH])
        return result

    def _normalize_adverse_reactions(self, reactions: Any) -> List[str]:
        """标准化不良反应"""
        if not isinstance(reactions, list):
            reactions = [str(reactions)] if reactions else []

        result: List[str] = []
        for reaction in reactions[:MAX_ADVERSE_REACTIONS]:
            text = str(reaction).strip()
            if len(text) > 5:
                result.append(text[:MAX_TINY_TEXT_LENGTH])
        return result

    def _normalize_interactions(self, interactions: Any) -> List[str]:
        """标准化药物相互作用"""
        if not isinstance(interactions, list):
            interactions = [str(interactions)] if interactions else []

        result: List[str] = []
        for interaction in interactions[:MAX_INTERACTIONS]:
            text = str(interaction).strip()
            if len(text) > 10:
                result.append(text[:MAX_SHORT_TEXT_LENGTH])
        return result

    def normalize_batch(self, drugs: List[Dict[str, Any]]) -> List[NormalizedDrug]:
        """
        批量标准化

        Args:
            drugs: 药物数据列表

        Returns:
            标准化后的药物列表（去重）
        """
        if not isinstance(drugs, list):
            logger.error(f"Expected list, got {type(drugs)}")
            return []

        normalized: List[NormalizedDrug] = []
        seen_names: set = set()

        for drug in drugs:
            result = self.normalize(drug)
            if result and result.name_en not in seen_names:
                seen_names.add(result.name_en)
                normalized.append(result)

        logger.info(f"Normalized {len(normalized)} drugs from {len(drugs)} input")
        return normalized

    def to_mysql_format(self, drug: NormalizedDrug) -> Dict[str, Any]:
        """转换为 MySQL 存储格式"""
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
            'typical_frequency': '',
            'description': drug.mechanism,
        }

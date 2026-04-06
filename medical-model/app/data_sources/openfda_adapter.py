"""
OpenFDA API 适配器
从 FDA 官方开放数据获取药物信息
API 文档: https://open.fda.gov/apis/drug/label/
"""

import requests
import time
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DrugInfo:
    """药物信息数据类"""
    fda_id: str = ""
    brand_names: List[str] = field(default_factory=list)
    generic_name: str = ""
    indications: List[str] = field(default_factory=list)
    contraindications: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    adverse_reactions: List[str] = field(default_factory=list)
    interactions: List[str] = field(default_factory=list)
    dosage: str = ""
    mechanism: str = ""
    manufacturer: List[str] = field(default_factory=list)
    route: List[str] = field(default_factory=list)
    product_type: List[str] = field(default_factory=list)
    substance_name: List[str] = field(default_factory=list)
    pharmacokinetics: str = ""
    pregnancy_category: str = ""


class OpenFDAAdapter:
    """OpenFDA 数据源适配器"""

    BASE_URL = "https://api.fda.gov/drug"

    def __init__(self, rate_limit_delay: float = 0.5, timeout: int = 30):
        """
        初始化 OpenFDA 适配器

        Args:
            rate_limit_delay: API 调用间隔（秒），避免触发限流
            timeout: 请求超时时间
        """
        self.rate_limit_delay = rate_limit_delay
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'MedicalRecommendationSystem/1.0'
        })

    def search_drugs(self, query: str, limit: int = 100, skip: int = 0) -> List[DrugInfo]:
        """
        搜索药物

        Args:
            query: 搜索查询字符串
            limit: 返回结果数量限制
            skip: 跳过的结果数量（用于分页）

        Returns:
            DrugInfo 对象列表
        """
        url = f"{self.BASE_URL}/label.json"
        params = {
            "search": query,
            "limit": min(limit, 100),  # FDA API 单次最多 100 条
            "skip": skip
        }

        try:
            logger.info(f"Fetching drugs from OpenFDA: {query}")
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            total = data.get("meta", {}).get("results", {}).get("total", 0)
            logger.info(f"Retrieved {len(results)} drugs, total available: {total}")

            return [self._parse_result(item) for item in results]

        except requests.exceptions.RequestException as e:
            logger.error(f"OpenFDA API error: {e}")
            return []
        finally:
            time.sleep(self.rate_limit_delay)

    def get_drug_by_name(self, drug_name: str) -> Optional[DrugInfo]:
        """
        根据药物名称获取详情

        Args:
            drug_name: 药物名称（品牌名或通用名）

        Returns:
            DrugInfo 对象或 None
        """
        # 先尝试品牌名搜索
        results = self.search_drugs(f'openfda.brand_name:"{drug_name}"', limit=1)
        if results:
            return results[0]

        # 再尝试通用名搜索
        results = self.search_drugs(f'openfda.generic_name:"{drug_name}"', limit=1)
        return results[0] if results else None

    def get_drugs_by_indication(self, indication: str, limit: int = 100) -> List[DrugInfo]:
        """
        根据适应症搜索药物

        Args:
            indication: 适应症关键词
            limit: 返回结果数量限制

        Returns:
            DrugInfo 对象列表
        """
        return self.search_drugs(f'indications_and_usage:"{indication}"', limit=limit)

    def fetch_all_drugs(self, batch_size: int = 100, max_total: int = 1000) -> List[DrugInfo]:
        """
        获取所有可用药物数据（分批获取）

        Args:
            batch_size: 每批获取的数量
            max_total: 最大获取总数

        Returns:
            DrugInfo 对象列表
        """
        all_drugs = []
        skip = 0
        seen_ids = set()

        while len(all_drugs) < max_total:
            # 搜索有完整信息的药物
            query = '_exists_:indications_and_usage AND _exists_:openfda.generic_name'
            batch = self.search_drugs(query, limit=batch_size, skip=skip)

            if not batch:
                break

            for drug in batch:
                # 去重
                if drug.fda_id and drug.fda_id not in seen_ids:
                    seen_ids.add(drug.fda_id)
                    all_drugs.append(drug)

            skip += batch_size
            logger.info(f"Total unique drugs collected: {len(all_drugs)}")

            # 如果返回数量少于批次大小，说明没有更多数据
            if len(batch) < batch_size:
                break

        return all_drugs[:max_total]

    def fetch_common_drugs(self, limit: int = 500) -> List[DrugInfo]:
        """
        获取常见药物数据（优先获取常用药物类别）

        Args:
            limit: 最大获取数量

        Returns:
            DrugInfo 对象列表
        """
        # 常见药物类别关键词
        common_categories = [
            "antihypertensive",      # 降压药
            "antidiabetic",          # 降糖药
            "antibiotic",            # 抗生素
            "statin",                # 他汀类
            "anticoagulant",         # 抗凝药
            "analgesic",             # 镇痛药
            "antidepressant",        # 抗抑郁药
            "antihistamine",         # 抗组胺药
            "proton pump inhibitor", # 质子泵抑制剂
            "beta blocker",          # β受体阻滞剂
            "ACE inhibitor",         # ACE抑制剂
            "calcium channel blocker", # 钙通道阻滞剂
            "diuretic",              # 利尿剂
            "insulin",               # 胰岛素
            "metformin",             # 二甲双胍
            "aspirin",               # 阿司匹林
            "omeprazole",            # 奥美拉唑
        ]

        all_drugs = []
        seen_ids = set()

        for category in common_categories:
            if len(all_drugs) >= limit:
                break

            # 使用适应症搜索，获取有完整信息的药物
            results = self.search_drugs(
                f'indications_and_usage:"{category}" AND _exists_:openfda.generic_name',
                limit=50
            )

            for drug in results:
                if drug.fda_id and drug.fda_id not in seen_ids:
                    seen_ids.add(drug.fda_id)
                    all_drugs.append(drug)

            logger.info(f"Category '{category}': collected {len(all_drugs)} total drugs")

        return all_drugs[:limit]

    def _parse_result(self, item: Dict) -> DrugInfo:
        """解析 FDA 返回的单条数据"""
        openfda = item.get("openfda", {})

        return DrugInfo(
            fda_id=self._get_first(openfda.get("spl_id", [])),
            brand_names=openfda.get("brand_name", [])[:5],  # 限制数量
            generic_name=self._get_first(openfda.get("generic_name", [])),
            indications=self._extract_list(item, "indications_and_usage", max_items=3),
            contraindications=self._extract_list(item, "contraindications", max_items=3),
            warnings=self._extract_list(item, "warnings_and_cautions", max_items=3),
            adverse_reactions=self._extract_list(item, "adverse_reactions", max_items=5),
            interactions=self._extract_list(item, "drug_interactions", max_items=3),
            dosage=self._extract_text(item, "dosage_and_administration", max_length=500),
            mechanism=self._extract_text(item, "mechanism_of_action", max_length=500),
            manufacturer=openfda.get("manufacturer_name", [])[:3],
            route=openfda.get("route", []),
            product_type=openfda.get("product_type", []),
            substance_name=openfda.get("substance_name", [])[:3],
            pharmacokinetics=self._extract_text(item, "pharmacokinetics", max_length=300),
            pregnancy_category=self._get_pregnancy_category(item)
        )

    def _get_first(self, items: List[str]) -> str:
        """获取列表第一个元素"""
        return items[0] if items else ""

    def _extract_list(self, item: Dict, key: str, max_items: int = 5) -> List[str]:
        """提取列表字段"""
        value = item.get(key, [])
        if isinstance(value, str):
            return [value[:500]]  # 限制长度
        return [str(v)[:500] for v in value[:max_items]] if value else []

    def _extract_text(self, item: Dict, key: str, max_length: int = 500) -> str:
        """提取文本字段"""
        value = item.get(key, [])
        if isinstance(value, list):
            text = " ".join(str(v) for v in value[:2])
        else:
            text = str(value)
        return text[:max_length]

    def _get_pregnancy_category(self, item: Dict) -> str:
        """获取妊娠分级"""
        pregnancy_info = item.get("pregnancy", [])
        if pregnancy_info:
            text = str(pregnancy_info[0]) if isinstance(pregnancy_info, list) else str(pregnancy_info)
            # 尝试提取分级 (A, B, C, D, X)
            for category in ['A', 'B', 'C', 'D', 'X']:
                if f'category {category}' in text.lower() or f'{category}类' in text:
                    return category
        return ""

    def to_dict(self, drug: DrugInfo) -> Dict[str, Any]:
        """将 DrugInfo 转换为字典"""
        return {
            'fda_id': drug.fda_id,
            'brand_names': drug.brand_names,
            'generic_name': drug.generic_name,
            'indications': drug.indications,
            'contraindications': drug.contraindications,
            'warnings': drug.warnings,
            'adverse_reactions': drug.adverse_reactions,
            'interactions': drug.interactions,
            'dosage': drug.dosage,
            'mechanism': drug.mechanism,
            'manufacturer': drug.manufacturer,
            'route': drug.route,
            'product_type': drug.product_type,
            'substance_name': drug.substance_name,
            'pharmacokinetics': drug.pharmacokinetics,
            'pregnancy_category': drug.pregnancy_category
        }


# 便捷函数
def fetch_drug_data(limit: int = 500) -> List[Dict[str, Any]]:
    """
    获取药物数据的便捷函数

    Args:
        limit: 最大获取数量

    Returns:
        药物数据字典列表
    """
    adapter = OpenFDAAdapter()
    drugs = adapter.fetch_common_drugs(limit=limit)
    return [adapter.to_dict(drug) for drug in drugs]


if __name__ == "__main__":
    # 测试代码
    adapter = OpenFDAAdapter()

    # 测试：获取常见药物
    print("Fetching common drugs...")
    drugs = adapter.fetch_common_drugs(limit=10)

    for drug in drugs[:5]:
        print(f"\n--- {drug.generic_name or drug.brand_names[0] if drug.brand_names else 'Unknown'} ---")
        print(f"FDA ID: {drug.fda_id}")
        print(f"Brand names: {drug.brand_names}")
        print(f"Indications: {drug.indications[:2] if drug.indications else 'N/A'}")
        print(f"Contraindications: {drug.contraindications[:1] if drug.contraindications else 'N/A'}")

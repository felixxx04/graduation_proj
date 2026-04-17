"""
OpenFDA API 适配器
从 FDA 官方开放数据获取药物信息
API 文档: https://open.fda.gov/apis/drug/label/

改进点：
- 指数退避重试机制
- 连接超时与读超时分离
- API Key 支持（提高限流阈值）
- 会话生命周期管理
- 细粒度异常类型
- 请求级日志追踪
"""

import requests
import time
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from app.config import settings
from app.exceptions import (
    DataSourceError,
    DataSourceConnectionError,
    DataSourceRateLimitError,
    DataSourceValidationError,
)

logger = logging.getLogger(__name__)

# 保留旧名称作为别名，兼容已有代码
OpenFDAError = DataSourceError
OpenFDAConnectionError = DataSourceConnectionError
OpenFDARateLimitError = DataSourceRateLimitError
OpenFDAValidationError = DataSourceValidationError


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
    """OpenFDA 数据源适配器，支持重试与配置解耦"""

    DEFAULT_BASE_URL = "https://api.fda.gov/drug"
    MAX_RETRIES = 3
    RETRY_BACKOFF_FACTOR = 2.0
    RETRY_STATUS_CODES = {429, 500, 502, 503, 504}

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        rate_limit_delay: float = 0.5,
        connect_timeout: int = 10,
        read_timeout: int = 30,
        max_retries: int = 3,
    ):
        """
        初始化 OpenFDA 适配器

        Args:
            base_url: API 基础 URL，默认从 settings 获取
            api_key: FDA API Key（可选，提高限流阈值）
            rate_limit_delay: API 调用间隔（秒）
            connect_timeout: 连接超时（秒）
            read_timeout: 读取超时（秒）
            max_retries: 最大重试次数
        """
        self.base_url = base_url or getattr(settings, 'openfda_base_url', self.DEFAULT_BASE_URL)
        self.api_key = api_key or getattr(settings, 'openfda_api_key', None)
        self.rate_limit_delay = rate_limit_delay
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.max_retries = min(max_retries, 5)  # 最多 5 次
        self._last_request_time = 0.0

        self.session = requests.Session()
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'MedicalRecommendationSystem/2.0'
        }
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        self.session.headers.update(headers)

    def _respect_rate_limit(self):
        """遵守 API 限流策略"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)

    def _make_request(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送 HTTP 请求，带重试与退避

        Args:
            url: 请求 URL
            params: 查询参数

        Returns:
            JSON 响应数据

        Raises:
            OpenFDAConnectionError: 连接失败
            OpenFDARateLimitError: 限流
            OpenFDAError: 其他请求异常
        """
        if self.api_key:
            params['api_key'] = self.api_key

        last_exception = None
        for attempt in range(1, self.max_retries + 1):
            self._respect_rate_limit()
            try:
                logger.debug(f"Request attempt {attempt}/{self.max_retries}: {url}")
                response = self.session.get(
                    url,
                    params=params,
                    timeout=(self.connect_timeout, self.read_timeout)
                )
                self._last_request_time = time.time()

                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limited, retrying after {retry_after}s")
                    if attempt < self.max_retries:
                        time.sleep(retry_after)
                        continue
                    raise OpenFDARateLimitError(f"Rate limited after {self.max_retries} retries")

                response.raise_for_status()
                return response.json()

            except requests.exceptions.ConnectionError as e:
                last_exception = e
                logger.warning(f"Connection error (attempt {attempt}): {e}")
            except requests.exceptions.Timeout as e:
                last_exception = e
                logger.warning(f"Timeout (attempt {attempt}): {e}")
            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code if e.response is not None else 0
                if status_code in self.RETRY_STATUS_CODES and attempt < self.max_retries:
                    backoff = self.RETRY_BACKOFF_FACTOR ** (attempt - 1)
                    logger.warning(f"HTTP {status_code}, retrying in {backoff:.1f}s (attempt {attempt})")
                    time.sleep(backoff)
                    continue
                raise OpenFDAError(f"HTTP error {status_code}: {e}") from e
            except requests.exceptions.RequestException as e:
                last_exception = e
                logger.warning(f"Request error (attempt {attempt}): {e}")

            # 退避等待
            if attempt < self.max_retries:
                backoff = self.RETRY_BACKOFF_FACTOR ** (attempt - 1)
                logger.info(f"Retrying in {backoff:.1f}s...")
                time.sleep(backoff)

        raise OpenFDAConnectionError(
            f"Failed after {self.max_retries} retries: {last_exception}"
        ) from last_exception

    def search_drugs(self, query: str, limit: int = 100, skip: int = 0) -> List[DrugInfo]:
        """
        搜索药物

        Args:
            query: 搜索查询字符串
            limit: 返回结果数量限制（最大 100）
            skip: 跳过的结果数量

        Returns:
            DrugInfo 对象列表

        Raises:
            OpenFDAValidationError: 查询参数无效
            OpenFDAError: API 请求失败
        """
        if not query or not query.strip():
            raise OpenFDAValidationError("Search query must not be empty")

        url = f"{self.base_url}/label.json"
        params = {
            "search": query,
            "limit": min(max(limit, 1), 100),
            "skip": max(skip, 0)
        }

        try:
            data = self._make_request(url, params)
            results = data.get("results", [])
            total = data.get("meta", {}).get("results", {}).get("total", 0)
            logger.info(f"Retrieved {len(results)} drugs, total available: {total}")
            return [self._parse_result(item) for item in results]
        except OpenFDARateLimitError:
            raise
        except OpenFDAError as e:
            logger.error(f"OpenFDA search failed: {e}")
            return []

    def get_drug_by_name(self, drug_name: str) -> Optional[DrugInfo]:
        """
        根据药物名称获取详情

        Args:
            drug_name: 药物名称（品牌名或通用名）

        Returns:
            DrugInfo 对象或 None
        """
        if not drug_name or not drug_name.strip():
            logger.warning("Empty drug name provided")
            return None

        # 先尝试品牌名搜索
        results = self.search_drugs(f'openfda.brand_name:"{drug_name}"', limit=1)
        if results:
            return results[0]

        # 再尝试通用名搜索
        results = self.search_drugs(f'openfda.generic_name:"{drug_name}"', limit=1)
        return results[0] if results else None

    def get_drugs_by_indication(self, indication: str, limit: int = 100) -> List[DrugInfo]:
        """根据适应症搜索药物"""
        if not indication or not indication.strip():
            raise OpenFDAValidationError("Indication must not be empty")
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
        all_drugs: List[DrugInfo] = []
        skip = 0
        seen_ids: set = set()
        consecutive_empty = 0
        max_consecutive_empty = 2

        while len(all_drugs) < max_total:
            query = '_exists_:indications_and_usage AND _exists_:openfda.generic_name'
            try:
                batch = self.search_drugs(query, limit=batch_size, skip=skip)
            except OpenFDAError as e:
                logger.error(f"Failed to fetch batch at skip={skip}: {e}")
                break

            if not batch:
                consecutive_empty += 1
                if consecutive_empty >= max_consecutive_empty:
                    logger.info("Multiple empty batches, stopping pagination")
                    break
                skip += batch_size
                continue

            consecutive_empty = 0
            for drug in batch:
                if drug.fda_id and drug.fda_id not in seen_ids:
                    seen_ids.add(drug.fda_id)
                    all_drugs.append(drug)

            skip += batch_size
            logger.info(f"Total unique drugs collected: {len(all_drugs)}")

            if len(batch) < batch_size:
                break

        return all_drugs[:max_total]

    def fetch_common_drugs(self, limit: int = 500) -> List[DrugInfo]:
        """获取常见药物数据"""
        common_categories = [
            "antihypertensive", "antidiabetic", "antibiotic", "statin",
            "anticoagulant", "analgesic", "antidepressant", "antihistamine",
            "proton pump inhibitor", "beta blocker", "ACE inhibitor",
            "calcium channel blocker", "diuretic", "insulin",
            "metformin", "aspirin", "omeprazole",
        ]

        all_drugs: List[DrugInfo] = []
        seen_ids: set = set()

        for category in common_categories:
            if len(all_drugs) >= limit:
                break

            try:
                results = self.search_drugs(
                    f'indications_and_usage:"{category}" AND _exists_:openfda.generic_name',
                    limit=50
                )
            except OpenFDAError as e:
                logger.warning(f"Failed to fetch category '{category}': {e}")
                continue

            for drug in results:
                if drug.fda_id and drug.fda_id not in seen_ids:
                    seen_ids.add(drug.fda_id)
                    all_drugs.append(drug)

            logger.info(f"Category '{category}': collected {len(all_drugs)} total drugs")

        return all_drugs[:limit]

    def _parse_result(self, item: Dict) -> DrugInfo:
        """解析 FDA 返回的单条数据"""
        if not isinstance(item, dict):
            logger.warning(f"Unexpected item type: {type(item)}, skipping")
            return DrugInfo()

        openfda = item.get("openfda", {})

        return DrugInfo(
            fda_id=self._get_first(openfda.get("spl_id", [])),
            brand_names=openfda.get("brand_name", [])[:5],
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
            return [value[:500]]
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

    def close(self):
        """关闭会话，释放资源"""
        if self.session:
            self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


# 便捷函数
def fetch_drug_data(limit: int = 500) -> List[Dict[str, Any]]:
    """
    获取药物数据的便捷函数

    Args:
        limit: 最大获取数量

    Returns:
        药物数据字典列表
    """
    with OpenFDAAdapter() as adapter:
        drugs = adapter.fetch_common_drugs(limit=limit)
        return [adapter.to_dict(drug) for drug in drugs]

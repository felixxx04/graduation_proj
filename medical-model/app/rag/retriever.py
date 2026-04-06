"""
药物检索器
整合向量检索和规则筛选
"""

import logging
from typing import List, Dict, Any, Optional
import json

from app.rag.vector_store import DrugVectorStore
from app.rag.embeddings import ChineseMedicalEmbeddings
from app.utils.json_helpers import safe_parse_json_list
from app.utils.json_helpers import safe_parse_json_list

logger = logging.getLogger(__name__)


class DrugRetriever:
    """药物检索器"""

    def __init__(self, vector_store: Optional[DrugVectorStore] = None):
        """
        初始化检索器

        Args:
            vector_store: 向量存储实例
        """
        self.vector_store = vector_store or DrugVectorStore()
        self.drug_database = {}  # 本地药物数据库缓存

    def set_drug_database(self, drugs: List[Dict[str, Any]]):
        """
        设置药物数据库

        Args:
            drugs: 药物列表
        """
        self.drug_database = {}
        for drug in drugs:
            drug_id = str(drug.get("id", ""))
            if drug_id:
                self.drug_database[drug_id] = drug
        logger.info(f"Loaded {len(self.drug_database)} drugs into database")

    def retrieve(
        self,
        query: str,
        top_k: int = 20,
        use_hybrid: bool = True
    ) -> List[Dict[str, Any]]:
        """
        检索相关药物

        Args:
            query: 查询文本（症状/疾病）
            top_k: 返回数量
            use_hybrid: 是否使用混合检索

        Returns:
            检索结果列表
        """
        if use_hybrid:
            results = self.vector_store.hybrid_search(query, n_results=top_k)
        else:
            results = self.vector_store.search(query, n_results=top_k)

        # 附加完整的药物信息
        for result in results:
            drug_id = result.get("drug_id", "")
            if drug_id in self.drug_database:
                drug_info = self.drug_database[drug_id]
                result["drug_info"] = drug_info

        return results

    def retrieve_by_patient(
        self,
        patient_data: Dict[str, Any],
        top_k: int = 20
    ) -> List[Dict[str, Any]]:
        """
        根据患者信息检索药物

        Args:
            patient_data: 患者数据
            top_k: 返回数量

        Returns:
            检索结果列表
        """
        # 构建查询
        query_parts = []

        # 症状
        symptoms = patient_data.get("symptoms", "")
        if symptoms:
            query_parts.append(symptoms)

        # 慢性病/疾病
        diseases = safe_parse_json_list(patient_data.get("chronic_diseases", []))
        query_parts.extend(diseases)

        query = " ".join(query_parts)

        if not query.strip():
            logger.warning("Empty query for patient")
            return []

        return self.retrieve(query, top_k=top_k)

    def filter_by_contraindications(
        self,
        candidates: List[Dict[str, Any]],
        patient_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        禁忌症过滤

        Args:
            candidates: 候选药物列表
            patient_data: 患者数据

        Returns:
            过滤后的候选列表
        """
        patient_diseases = safe_parse_json_list(patient_data.get("chronic_diseases", []))

        filtered = []
        for candidate in candidates:
            drug_info = candidate.get("drug_info", {})
            contraindications = safe_parse_json_list(drug_info.get("contraindications", []))

            # 检查禁忌症
            has_contraindication = False
            warnings = []

            for disease in patient_diseases:
                for contra in contraindications:
                    if self._text_match(disease, contra):
                        has_contraindication = True
                        warnings.append(f"禁忌症风险: {contra}")

            candidate["contraindication_warning"] = warnings
            candidate["has_contraindication"] = has_contraindication

            # 不完全排除，但降低排名
            filtered.append(candidate)

        return filtered

    def filter_by_allergies(
        self,
        candidates: List[Dict[str, Any]],
        patient_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        过敏史过滤

        Args:
            candidates: 候选药物列表
            patient_data: 患者数据

        Returns:
            过滤后的候选列表
        """
        allergies = safe_parse_json_list(patient_data.get("allergies", []))

        for candidate in candidates:
            drug_info = candidate.get("drug_info", {})
            drug_name = drug_info.get("name", "")
            generic_name = drug_info.get("generic_name", "")

            allergy_warnings = []
            for allergy in allergies:
                if self._text_match(allergy, drug_name) or self._text_match(allergy, generic_name):
                    allergy_warnings.append(f"过敏风险: 患者对 {allergy} 过敏")

            candidate["allergy_warning"] = allergy_warnings
            candidate["has_allergy_risk"] = len(allergy_warnings) > 0

        return candidates

    def check_interactions(
        self,
        candidates: List[Dict[str, Any]],
        patient_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        检查药物相互作用

        Args:
            candidates: 候选药物列表
            patient_data: 患者数据

        Returns:
            带相互作用警告的候选列表
        """
        current_meds = safe_parse_json_list(patient_data.get("current_medications", []))

        for candidate in candidates:
            drug_info = candidate.get("drug_info", {})
            interactions = safe_parse_json_list(drug_info.get("interactions", []))

            interaction_warnings = []
            for med in current_meds:
                for interaction in interactions:
                    if self._text_match(med, interaction):
                        interaction_warnings.append(f"相互作用风险: 与 {med} 可能存在相互作用")

            candidate["interaction_warnings"] = interaction_warnings
            candidate["has_interaction_risk"] = len(interaction_warnings) > 0

        return candidates

    def rank_candidates(
        self,
        candidates: List[Dict[str, Any]],
        patient_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        综合排序

        Args:
            candidates: 候选药物列表
            patient_data: 患者数据

        Returns:
            排序后的候选列表
        """
        for candidate in candidates:
            # 基础分数（来自 RAG 检索）
            base_score = candidate.get("score", 0.5)

            # 惩罚因子
            penalty = 0.0

            # 禁忌症惩罚
            if candidate.get("has_contraindication"):
                penalty += 0.5

            # 过敏惩罚
            if candidate.get("has_allergy_risk"):
                penalty += 0.8

            # 相互作用惩罚
            if candidate.get("has_interaction_risk"):
                penalty += 0.2

            # 计算最终分数
            final_score = max(0, base_score - penalty)
            candidate["final_score"] = final_score

        # 按最终分数排序
        candidates.sort(key=lambda x: x.get("final_score", 0), reverse=True)
        return candidates

    def _text_match(self, text1: str, text2: str) -> bool:
        """文本匹配（支持部分匹配）"""
        if not text1 or not text2:
            return False
        t1 = text1.lower().strip()
        t2 = text2.lower().strip()
        return t1 in t2 or t2 in t1

    def recommend(
        self,
        patient_data: Dict[str, Any],
        top_k: int = 4
    ) -> List[Dict[str, Any]]:
        """
        完整推荐流程

        Args:
            patient_data: 患者数据
            top_k: 返回数量

        Returns:
            推荐药物列表
        """
        # 1. RAG 检索
        candidates = self.retrieve_by_patient(patient_data, top_k=20)

        if not candidates:
            logger.warning("No candidates found from RAG")
            return []

        # 2. 禁忌症过滤
        candidates = self.filter_by_contraindications(candidates, patient_data)

        # 3. 过敏过滤
        candidates = self.filter_by_allergies(candidates, patient_data)

        # 4. 相互作用检查
        candidates = self.check_interactions(candidates, patient_data)

        # 5. 综合排序
        candidates = self.rank_candidates(candidates, patient_data)

        # 6. 返回 Top-K
        return candidates[:top_k]


if __name__ == "__main__":
    # 测试代码
    print("Testing drug retriever...")

    retriever = DrugRetriever()

    # 设置测试药物数据库
    test_drugs = [
        {
            "id": "1",
            "name": "二甲双胍",
            "generic_name": "Metformin",
            "category": "降糖药",
            "indications": json.dumps(["2型糖尿病", "糖尿病"]),
            "contraindications": json.dumps(["严重肾功能不全"]),
            "interactions": json.dumps(["造影剂", "酒精"])
        },
        {
            "id": "2",
            "name": "氨氯地平",
            "generic_name": "Amlodipine",
            "category": "降压药",
            "indications": json.dumps(["高血压", "冠心病"]),
            "contraindications": json.dumps(["严重低血压"]),
            "interactions": json.dumps(["葡萄柚汁"])
        }
    ]

    retriever.set_drug_database(test_drugs)

    # 测试患者
    patient = {
        "chronic_diseases": json.dumps(["糖尿病", "高血压"]),
        "allergies": json.dumps([]),
        "current_medications": json.dumps(["阿司匹林"])
    }

    results = retriever.recommend(patient, top_k=4)
    print(f"Recommendations: {results}")

"""
RAG 推荐服务
整合向量检索和规则引擎
"""

import logging
from typing import Dict, List, Any, Optional
import json
import numpy as np

from app.rag.vector_store import DrugVectorStore
from app.rag.retriever import DrugRetriever
from app.utils.privacy import laplace_noise, gaussian_noise

logger = logging.getLogger(__name__)


class RAGRecommendationService:
    """RAG 增强的推荐服务"""

    def __init__(
        self,
        vector_store_path: str = "./data/chroma",
        use_mock_embeddings: bool = False
    ):
        """
        初始化 RAG 服务

        Args:
            vector_store_path: 向量存储路径
            use_mock_embeddings: 是否使用 Mock Embedding
        """
        self.vector_store_path = vector_store_path
        self.use_mock_embeddings = use_mock_embeddings

        # 延迟初始化
        self._vector_store = None
        self._retriever = None

    @property
    def vector_store(self) -> DrugVectorStore:
        """懒加载向量存储"""
        if self._vector_store is None:
            self._vector_store = DrugVectorStore(
                persist_directory=self.vector_store_path,
                use_mock_embeddings=self.use_mock_embeddings
            )
        return self._vector_store

    @property
    def retriever(self) -> DrugRetriever:
        """懒加载检索器"""
        if self._retriever is None:
            self._retriever = DrugRetriever(vector_store=self.vector_store)
        return self._retriever

    def is_ready(self) -> bool:
        """检查服务是否就绪"""
        try:
            return self.vector_store.get_stats().get("total_drugs", 0) > 0
        except Exception as e:
            logger.warning(f"RAG service not ready: {e}")
            return False

    def retrieve_relevant_drugs(
        self,
        symptoms: str,
        diseases: List[str],
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        检索相关药物

        Args:
            symptoms: 症状描述
            diseases: 疾病列表
            top_k: 返回数量

        Returns:
            检索结果列表
        """
        # 构建查询
        query_parts = []
        if symptoms:
            query_parts.append(symptoms)
        query_parts.extend(diseases or [])
        query = " ".join(query_parts)

        if not query:
            return []

        # 混合检索
        try:
            results = self.vector_store.hybrid_search(query, n_results=top_k)
            return results
        except Exception as e:
            logger.error(f"RAG search error: {e}")
            return []

    def enhance_recommendation(
        self,
        patient_data: Dict[str, Any],
        base_recommendations: List[Dict[str, Any]],
        top_k: int = 4,
        dp_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        使用 RAG 增强推荐结果

        Args:
            patient_data: 患者数据
            base_recommendations: 基础推荐结果
            top_k: 返回数量
            dp_config: 差分隐私配置

        Returns:
            增强后的推荐结果
        """
        # 1. RAG 检索
        symptoms = patient_data.get("symptoms", "")
        diseases = patient_data.get("chronic_diseases", [])

        if isinstance(diseases, str):
            try:
                diseases = json.loads(diseases)
            except (json.JSONDecodeError, ValueError):
                diseases = [diseases] if diseases else []

        rag_results = self.retrieve_relevant_drugs(symptoms, diseases, top_k=20)

        # 2. 合并结果
        drug_scores = {}

        # 基础推荐分数
        for rec in base_recommendations:
            drug_id = str(rec.get("drugId", rec.get("id", "")))
            drug_scores[drug_id] = {
                "base_score": rec.get("score", 0.5),
                "rag_score": 0,
                "data": rec
            }

        # RAG 检索分数
        for rag in rag_results:
            drug_id = str(rag.get("drug_id", ""))
            if drug_id in drug_scores:
                drug_scores[drug_id]["rag_score"] = rag["similarity"]
            else:
                drug_scores[drug_id] = {
                    "base_score": 0,
                    "rag_score": rag["similarity"],
                    "data": {
                        "drugId": drug_id,
                        "drugName": rag.get("drug_name", ""),
                        "category": rag.get("category", "")
                    }
                }

        # 3. 融合分数
        final_results = []
        for drug_id, scores in drug_scores.items():
            # 加权融合：基础模型 60%, RAG 40%
            final_score = 0.6 * scores["base_score"] + 0.4 * scores["rag_score"]

            result = scores["data"].copy()
            result["score"] = final_score
            result["rag_enhanced"] = True
            result["rag_score"] = scores["rag_score"]
            result["base_score"] = scores["base_score"]
            final_results.append(result)

        # 4. 排序
        final_results.sort(key=lambda x: x["score"], reverse=True)

        # 5. 应用差分隐私噪声
        if dp_config and dp_config.get("enabled", False):
            for result in final_results[:top_k]:
                noisy_score, noise = self._apply_dp_noise(
                    result["score"], dp_config
                )
                result["score"] = noisy_score
                result["dpNoise"] = noise

        # 6. 重新排序（DP 可能改变顺序）
        final_results.sort(key=lambda x: x["score"], reverse=True)

        return {
            "recommendationId": np.random.randint(1000, 9999),
            "selected": final_results[:top_k],
            "base": base_recommendations[:top_k] if base_recommendations else [],
            "dp": final_results[:top_k],
            "dpEnabled": dp_config.get("enabled", False) if dp_config else False,
            "ragEnabled": True,
            "ragCandidates": len(rag_results)
        }

    def _apply_dp_noise(
        self,
        score: float,
        dp_config: Dict[str, Any]
    ) -> tuple:
        """应用差分隐私噪声"""
        epsilon = dp_config.get("epsilon", 0.1)
        delta = dp_config.get("delta", 1e-5)
        sensitivity = dp_config.get("sensitivity", 1.0)
        mechanism = dp_config.get("noiseMechanism", "laplace")

        if mechanism == "gaussian":
            noise = gaussian_noise((1,), epsilon, delta, sensitivity)[0]
        else:
            noise = laplace_noise((1,), epsilon, sensitivity)[0]

        return score + noise, noise

    def set_drug_database(self, drugs: List[Dict[str, Any]]):
        """设置药物数据库"""
        self.retriever.set_drug_database(drugs)

        # 同时更新向量存储
        self.vector_store.add_drugs_batch(drugs)


# 全局实例
rag_service = None


def get_rag_service(
    vector_store_path: str = "./data/chroma",
    use_mock_embeddings: bool = False
) -> RAGRecommendationService:
    """获取 RAG 服务单例"""
    global rag_service
    if rag_service is None:
        rag_service = RAGRecommendationService(
            vector_store_path=vector_store_path,
            use_mock_embeddings=use_mock_embeddings
        )
    return rag_service


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

    logger.info("Testing RAG service...")

    service = RAGRecommendationService(use_mock_embeddings=True)

    # 测试患者
    patient = {
        "chronic_diseases": ["糖尿病", "高血压"],
        "symptoms": "头晕乏力",
        "allergies": [],
        "current_medications": []
    }

    # 测试基础推荐（模拟）
    base_recs = [
        {"drugId": "1", "drugName": "二甲双胍", "score": 0.85},
        {"drugId": "2", "drugName": "氨氯地平", "score": 0.82}
    ]

    result = service.enhance_recommendation(patient, base_recs, top_k=4)
    logger.info(f"Result: {json.dumps(result, indent=2, ensure_ascii=False)}")

"""
向量存储模块
使用 Chroma 进行药物向量索引和检索
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import numpy as np
import logging
import os

from app.rag.embeddings import ChineseMedicalEmbeddings, get_embedder

logger = logging.getLogger(__name__)


class DrugVectorStore:
    """药物向量存储"""

    COLLECTION_NAMES = {
        "indications": "drug_indications",
        "mechanisms": "drug_mechanisms",
        "full_text": "drug_full_text"
    }

    def __init__(
        self,
        persist_directory: str = "./data/chroma",
        embedder: Optional[ChineseMedicalEmbeddings] = None,
        use_mock_embeddings: bool = False
    ):
        """
        初始化向量存储

        Args:
            persist_directory: 持久化目录
            embedder: Embedding 模型实例
            use_mock_embeddings: 是否使用 Mock Embedding
        """
        self.persist_directory = persist_directory
        self.embedder = embedder or get_embedder(use_mock=use_mock_embeddings)

        # 确保目录存在
        os.makedirs(persist_directory, exist_ok=True)

        # 初始化 Chroma 客户端
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collections = {}
        self._init_collections()

        logger.info(f"Vector store initialized at {persist_directory}")

    def _init_collections(self):
        """初始化集合"""
        for key, name in self.COLLECTION_NAMES.items():
            try:
                self.collections[key] = self.client.get_or_create_collection(
                    name=name,
                    metadata={"hnsw:space": "cosine"}
                )
                count = self.collections[key].count()
                logger.info(f"Collection '{name}' loaded with {count} items")
            except Exception as e:
                logger.error(f"Error initializing collection {name}: {e}")
                self.collections[key] = None

    def add_drug(
        self,
        drug_id: str,
        drug_data: Dict[str, Any],
        batch_mode: bool = False
    ):
        """
        添加单个药物到向量库

        Args:
            drug_id: 药物 ID
            drug_data: 药物数据字典
            batch_mode: 是否批量模式（跳过单条添加）
        """
        if batch_mode:
            return

        try:
            # 1. 适应症向量
            indications = drug_data.get("indications", [])
            if indications:
                indication_text = " ".join(indications) if isinstance(indications, list) else str(indications)
                if indication_text.strip():
                    self.collections["indications"].add(
                        ids=[f"{drug_id}_indication"],
                        documents=[indication_text],
                        metadatas=[{
                            "drug_id": drug_id,
                            "type": "indication",
                            "drug_name": drug_data.get("name", "")
                        }]
                    )

            # 2. 作用机制向量
            mechanism = drug_data.get("mechanism", "") or drug_data.get("description", "")
            if mechanism and mechanism.strip():
                self.collections["mechanisms"].add(
                    ids=[f"{drug_id}_mechanism"],
                    documents=[mechanism[:1000]],  # 限制长度
                    metadatas=[{
                        "drug_id": drug_id,
                        "type": "mechanism",
                        "drug_name": drug_data.get("name", "")
                    }]
                )

            # 3. 全文向量
            full_text = self._build_full_text(drug_data)
            if full_text.strip():
                self.collections["full_text"].add(
                    ids=[f"{drug_id}_full"],
                    documents=[full_text],
                    metadatas=[{
                        "drug_id": drug_id,
                        "type": "full_text",
                        "drug_name": drug_data.get("name", "")
                    }]
                )

        except Exception as e:
            logger.error(f"Error adding drug {drug_id}: {e}")

    def add_drugs_batch(self, drugs: List[Dict[str, Any]]):
        """
        批量添加药物

        Args:
            drugs: 药物数据列表
        """
        for collection_type in ["indications", "mechanisms", "full_text"]:
            ids = []
            documents = []
            metadatas = []

            for drug in drugs:
                drug_id = str(drug.get("id") or drug.get("drug_id") or drug.get("drug_code") or drug.get("name", ""))
                if not drug_id:
                    continue

                if collection_type == "indications":
                    indications = drug.get("indications", [])
                    if indications:
                        text = " ".join(indications) if isinstance(indications, list) else str(indications)
                        if text.strip():
                            ids.append(f"{drug_id}_indication")
                            documents.append(text)
                            metadatas.append({
                                "drug_id": drug_id,
                                "type": "indication",
                                "drug_name": drug.get("name", "")
                            })

                elif collection_type == "mechanisms":
                    mechanism = drug.get("mechanism", "") or drug.get("description", "")
                    if mechanism and mechanism.strip():
                        ids.append(f"{drug_id}_mechanism")
                        documents.append(mechanism[:1000])
                        metadatas.append({
                            "drug_id": drug_id,
                            "type": "mechanism",
                            "drug_name": drug.get("name", "")
                        })

                elif collection_type == "full_text":
                    full_text = self._build_full_text(drug)
                    if full_text.strip():
                        ids.append(f"{drug_id}_full")
                        documents.append(full_text)
                        metadatas.append({
                            "drug_id": drug_id,
                            "type": "full_text",
                            "drug_name": drug.get("name", "")
                        })

            if ids and self.collections[collection_type]:
                try:
                    self.collections[collection_type].add(
                        ids=ids,
                        documents=documents,
                        metadatas=metadatas
                    )
                    logger.info(f"Added {len(ids)} items to {collection_type}")
                except Exception as e:
                    logger.error(f"Error batch adding to {collection_type}: {e}")

    def search(
        self,
        query: str,
        collection: str = "indications",
        n_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        语义搜索

        Args:
            query: 查询文本
            collection: 集合名称
            n_results: 返回结果数量

        Returns:
            搜索结果列表
        """
        if collection not in self.collections or not self.collections[collection]:
            logger.warning(f"Collection {collection} not available")
            return []

        try:
            results = self.collections[collection].query(
                query_texts=[query],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )

            if not results["ids"] or not results["ids"][0]:
                return []

            return [
                {
                    "drug_id": meta.get("drug_id", ""),
                    "drug_name": meta.get("drug_name", ""),
                    "document": doc,
                    "distance": dist,
                    "similarity": 1 - dist,  # 转换为相似度
                    "collection": collection
                }
                for meta, doc, dist in zip(
                    results["metadatas"][0],
                    results["documents"][0],
                    results["distances"][0]
                )
            ]

        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

    def hybrid_search(
        self,
        query: str,
        n_results: int = 10,
        collections: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        混合检索：综合多个集合的结果

        Args:
            query: 查询文本
            n_results: 返回结果数量
            collections: 要搜索的集合列表

        Returns:
            合并后的搜索结果
        """
        if collections is None:
            collections = ["indications", "full_text"]

        all_results = {}

        for collection_name in collections:
            results = self.search(query, collection_name, n_results=n_results * 2)
            for r in results:
                drug_id = r["drug_id"]
                if not drug_id:
                    continue
                if drug_id not in all_results:
                    all_results[drug_id] = {
                        "drug_id": drug_id,
                        "drug_name": r.get("drug_name", ""),
                        "scores": [],
                        "documents": []
                    }
                all_results[drug_id]["scores"].append(r["similarity"])
                all_results[drug_id]["documents"].append(r["document"])

        # 加权融合
        final_results = []
        for drug_id, data in all_results.items():
            # 取最高分和平均分的加权组合
            max_score = max(data["scores"]) if data["scores"] else 0
            avg_score = np.mean(data["scores"]) if data["scores"] else 0

            # 70% 最高分 + 30% 平均分
            combined_score = 0.7 * max_score + 0.3 * avg_score

            final_results.append({
                "drug_id": drug_id,
                "drug_name": data["drug_name"],
                "score": combined_score,
                "max_similarity": max_score,
                "avg_similarity": avg_score,
                "collections_matched": len(data["scores"])
            })

        # 排序并返回 Top-K
        final_results.sort(key=lambda x: x["score"], reverse=True)
        return final_results[:n_results]

    def _build_full_text(self, drug_data: Dict) -> str:
        """构建全文用于索引"""
        parts = []

        if drug_data.get("name"):
            parts.append(f"药物名称: {drug_data['name']}")

        if drug_data.get("generic_name"):
            parts.append(f"通用名: {drug_data['generic_name']}")

        if drug_data.get("category"):
            parts.append(f"分类: {drug_data['category']}")

        indications = drug_data.get("indications", [])
        if indications:
            if isinstance(indications, list):
                parts.append(f"适应症: {', '.join(indications[:5])}")
            else:
                parts.append(f"适应症: {indications}")

        mechanism = drug_data.get("mechanism", "") or drug_data.get("description", "")
        if mechanism:
            parts.append(f"作用机制: {mechanism[:200]}")

        return " ".join(parts)

    def get_stats(self) -> Dict[str, int]:
        """获取存储统计"""
        stats = {}
        for key, collection in self.collections.items():
            if collection:
                stats[key] = collection.count()
        return stats

    def clear(self):
        """清空所有集合"""
        for key, collection in self.collections.items():
            if collection:
                try:
                    # 删除并重建
                    self.client.delete_collection(self.COLLECTION_NAMES[key])
                    self.collections[key] = self.client.create_collection(
                        name=self.COLLECTION_NAMES[key],
                        metadata={"hnsw:space": "cosine"}
                    )
                    logger.info(f"Cleared collection: {key}")
                except Exception as e:
                    logger.error(f"Error clearing collection {key}: {e}")


if __name__ == "__main__":
    # 测试代码
    print("Testing vector store...")

    store = DrugVectorStore(use_mock_embeddings=True)

    # 添加测试药物
    test_drugs = [
        {
            "id": "1",
            "name": "二甲双胍",
            "generic_name": "Metformin",
            "category": "降糖药",
            "indications": ["2型糖尿病", "糖尿病"],
            "contraindications": ["严重肾功能不全"],
            "mechanism": "降低肝糖输出，提高胰岛素敏感性"
        },
        {
            "id": "2",
            "name": "氨氯地平",
            "generic_name": "Amlodipine",
            "category": "降压药",
            "indications": ["高血压", "冠心病"],
            "mechanism": "钙通道阻滞剂，扩张血管"
        }
    ]

    store.add_drugs_batch(test_drugs)
    print(f"Stats: {store.get_stats()}")

    # 测试搜索
    results = store.hybrid_search("糖尿病", n_results=5)
    print(f"Search results: {results}")

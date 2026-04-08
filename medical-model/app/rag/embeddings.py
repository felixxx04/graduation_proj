"""
Embedding 模型封装
使用 bge-small-zh 进行中文医学文本向量化
"""

import numpy as np
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class ChineseMedicalEmbeddings:
    """中文医学 Embedding 模型封装"""

    def __init__(self, model_name: str = "BAAI/bge-small-zh"):
        """
        初始化 Embedding 模型

        Args:
            model_name: 模型名称，默认使用 bge-small-zh
        """
        self.model_name = model_name
        self.model = None
        self.dimension = 512  # bge-small-zh 向量维度
        self._load_model()

    def _load_model(self):
        """加载模型"""
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            self.dimension = self.model.get_sentence_embedding_dimension()
            logger.info(f"Model loaded, dimension: {self.dimension}")
        except ImportError:
            logger.warning("sentence-transformers not installed, using fallback")
            self.model = None
            self.dimension = 512
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self.model = None

    def encode(self, texts: List[str], normalize: bool = True) -> np.ndarray:
        """
        将文本编码为向量

        Args:
            texts: 文本列表
            normalize: 是否归一化向量

        Returns:
            向量数组，shape=(len(texts), dimension)
        """
        if self.model is None:
            # 回退：返回随机向量（仅用于测试）
            logger.warning("Using random embeddings (model not loaded)")
            return np.random.randn(len(texts), self.dimension).astype(np.float32)

        embeddings = self.model.encode(
            texts,
            normalize_embeddings=normalize,
            show_progress_bar=False
        )
        return np.array(embeddings)

    def encode_single(self, text: str) -> np.ndarray:
        """
        编码单个文本

        Args:
            text: 输入文本

        Returns:
            向量，shape=(dimension,)
        """
        return self.encode([text])[0]

    def similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        计算余弦相似度

        Args:
            vec1: 向量1
            vec2: 向量2

        Returns:
            相似度分数 [-1, 1]
        """
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(vec1, vec2) / (norm1 * norm2))

    def batch_similarity(self, query_vec: np.ndarray, doc_vecs: np.ndarray) -> np.ndarray:
        """
        批量计算相似度

        Args:
            query_vec: 查询向量，shape=(dimension,)
            doc_vecs: 文档向量，shape=(n_docs, dimension)

        Returns:
            相似度数组，shape=(n_docs,)
        """
        # 归一化
        query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-8)
        doc_norms = doc_vecs / (np.linalg.norm(doc_vecs, axis=1, keepdims=True) + 1e-8)

        # 点积
        similarities = np.dot(doc_norms, query_norm)
        return similarities

    def get_dimension(self) -> int:
        """获取向量维度"""
        return self.dimension

    def is_loaded(self) -> bool:
        """检查模型是否已加载"""
        return self.model is not None


class MockEmbeddings:
    """Mock Embedding 用于测试"""

    def __init__(self, dimension: int = 512):
        self.dimension = dimension
        self.model = None

    def encode(self, texts: List[str], normalize: bool = True) -> np.ndarray:
        # 使用简单的哈希生成确定性向量
        embeddings = []
        for text in texts:
            # 使用哈希生成向量
            np.random.seed(hash(text) % (2**32))
            vec = np.random.randn(self.dimension).astype(np.float32)
            if normalize:
                vec = vec / np.linalg.norm(vec)
            embeddings.append(vec)
        return np.array(embeddings)

    def encode_single(self, text: str) -> np.ndarray:
        return self.encode([text])[0]

    def get_dimension(self) -> int:
        return self.dimension

    def is_loaded(self) -> bool:
        return True


def get_embedder(use_mock: bool = False) -> ChineseMedicalEmbeddings:
    """
    获取 Embedder 实例

    Args:
        use_mock: 是否使用 Mock

    Returns:
        Embedder 实例
    """
    if use_mock:
        return MockEmbeddings()
    return ChineseMedicalEmbeddings()


if __name__ == "__main__":
    # 测试代码
    print("Testing embedding model...")

    embedder = ChineseMedicalEmbeddings()
    print(f"Model loaded: {embedder.is_loaded()}")
    print(f"Dimension: {embedder.get_dimension()}")

    # 测试编码
    texts = [
        "高血压患者用药推荐",
        "糖尿病药物治疗",
        "感冒发烧吃什么药"
    ]

    vectors = embedder.encode(texts)
    print(f"Encoded {len(texts)} texts, shape: {vectors.shape}")

    # 测试相似度
    sim = embedder.similarity(vectors[0], vectors[1])
    print(f"Similarity between text 0 and 1: {sim:.4f}")

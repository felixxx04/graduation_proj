"""
构建药物向量索引
"""

import sys
import os
import json
import argparse

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.rag.vector_store import DrugVectorStore
from app.rag.embeddings import ChineseMedicalEmbeddings

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_drugs_from_json(file_path: str):
    """从 JSON 文件加载药物数据"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_drugs_from_database():
    """从数据库加载药物数据（如果配置了数据库连接）"""
    # TODO: 实现数据库连接
    pass


def build_index(drugs: list, persist_directory: str, use_mock_embeddings: bool = False):
    """
    构建向量索引

    Args:
        drugs: 药物列表
        persist_directory: 向量库持久化目录
        use_mock_embeddings: 是否使用 Mock Embedding
    """
    logger.info(f"Building vector index for {len(drugs)} drugs")

    # 初始化向量存储
    vector_store = DrugVectorStore(
        persist_directory=persist_directory,
        use_mock_embeddings=use_mock_embeddings
    )

    # 检查模型是否加载
    if not vector_store.embedder.is_loaded():
        logger.warning("Embedding model not loaded, using mock embeddings")
        use_mock_embeddings = True
        vector_store = DrugVectorStore(
            persist_directory=persist_directory,
            use_mock_embeddings=True
        )

    # 批量添加药物
    logger.info("Adding drugs to vector store...")
    vector_store.add_drugs_batch(drugs)

    # 获取统计
    stats = vector_store.get_stats()
    logger.info(f"Index stats: {stats}")

    return vector_store


def test_search(vector_store: DrugVectorStore):
    """测试搜索功能"""
    test_queries = [
        "糖尿病",
        "高血压",
        "感冒发烧",
        "胃痛",
        "失眠"
    ]

    logger.info("=" * 50)
    logger.info("Testing search functionality...")

    for query in test_queries:
        logger.info(f"\nQuery: {query}")
        results = vector_store.hybrid_search(query, n_results=3)

        for i, result in enumerate(results):
            logger.info(f"  {i+1}. {result['drug_name']} (score: {result['similarity']:.4f})")


def main():
    parser = argparse.ArgumentParser(description='Build drug vector index')
    parser.add_argument('--input', type=str, default='data/drugs_openfda.json',
                        help='Input drugs JSON file')
    parser.add_argument('--output', type=str, default='data/chroma',
                        help='Output vector store directory')
    parser.add_argument('--mock', action='store_true',
                        help='Use mock embeddings (for testing)')
    parser.add_argument('--test', action='store_true',
                        help='Run search tests after building')

    args = parser.parse_args()

    # 构建路径
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_path = os.path.join(base_dir, args.input)
    output_path = os.path.join(base_dir, args.output)

    # 加载药物数据
    if os.path.exists(input_path):
        logger.info(f"Loading drugs from {input_path}")
        drugs = load_drugs_from_json(input_path)
    else:
        logger.error(f"Input file not found: {input_path}")
        logger.info("Please run sync_external_data.py first to fetch drug data")
        return

    if not drugs:
        logger.error("No drugs loaded")
        return

    # 构建索引
    vector_store = build_index(
        drugs,
        persist_directory=output_path,
        use_mock_embeddings=args.mock
    )

    # 测试搜索
    if args.test:
        test_search(vector_store)

    logger.info("=" * 50)
    logger.info("Index building completed!")
    logger.info(f"Vector store saved to: {output_path}")


if __name__ == "__main__":
    main()

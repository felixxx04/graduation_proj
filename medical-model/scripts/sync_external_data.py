"""
从 OpenFDA 同步药物数据到本地数据库
"""

import sys
import os
import json
import time

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.data_sources.openfda_adapter import OpenFDAAdapter, fetch_drug_data
from app.data_sources.data_normalizer import DataNormalizer

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def sync_from_openfda(limit: int = 500, output_file: str = None):
    """
    从 OpenFDA 同步药物数据

    Args:
        limit: 最大获取数量
        output_file: 输出文件路径（JSON格式）
    """
    logger.info(f"Starting data sync from OpenFDA, limit={limit}")

    # 初始化适配器
    adapter = OpenFDAAdapter(rate_limit_delay=0.6)  # 遵守 API 限流

    # 获取常见药物数据
    drugs = adapter.fetch_common_drugs(limit=limit)
    logger.info(f"Fetched {len(drugs)} drugs from OpenFDA")

    if not drugs:
        logger.error("No drugs fetched, aborting")
        return []

    # 标准化数据
    normalizer = DataNormalizer()
    normalized_drugs = normalizer.normalize_batch([adapter.to_dict(d) for d in drugs])
    logger.info(f"Normalized {len(normalized_drugs)} drugs")

    # 转换为存储格式
    storage_data = [normalizer.to_mysql_format(d) for d in normalized_drugs]

    # 保存到文件
    if output_file:
        os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(storage_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(storage_data)} drugs to {output_file}")

    return storage_data


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='Sync drug data from OpenFDA')
    parser.add_argument('--limit', type=int, default=500, help='Maximum number of drugs to fetch')
    parser.add_argument('--output', type=str, default='data/drugs_openfda.json',
                        help='Output file path')

    args = parser.parse_args()

    # 确保输出目录存在
    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        args.output
    )

    # 同步数据
    drugs = sync_from_openfda(limit=args.limit, output_file=output_path)

    # 打印统计
    if drugs:
        logger.info("=" * 50)
        logger.info("Sync completed!")
        logger.info(f"Total drugs: {len(drugs)}")

        # 分类统计
        categories = {}
        for drug in drugs:
            cat = drug.get('category', 'Unknown')
            categories[cat] = categories.get(cat, 0) + 1

        logger.info("Categories distribution:")
        for cat, count in sorted(categories.items(), key=lambda x: -x[1])[:10]:
            logger.info(f"  {cat}: {count}")


if __name__ == "__main__":
    main()

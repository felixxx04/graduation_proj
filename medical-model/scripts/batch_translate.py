"""批量翻译英文字段为中文 — 生成缓存文件

翻译字段:
1. drug_class_en (药物类别) → drug_class_translations.json
2. indications condition (适应症) → condition_translations.json
3. side_effects_raw (副作用) → side_effects_translations.json

策略: googletrans 自动翻译 + 人工校验关键映射
"""

import json
import sys
import os
import time
import logging

sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

PIPELINE_DATA = "data/pipeline_data.json"
OUTPUT_DIR = "data/translations"

os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_pipeline():
    with open(PIPELINE_DATA, 'r', encoding='utf-8') as f:
        return json.load(f)


def translate_batch(names: list, cache: dict, checkpoint_path: str,
                    checkpoint_interval: int = 50) -> dict:
    """批量翻译，增量缓存，失败保留英文原名"""
    from googletrans import Translator
    translator = Translator()

    result = dict(cache)
    need_translate = [n for n in names if n not in result]
    success = 0

    logger.info(f"需要翻译: {len(need_translate)} 项, 已缓存: {len(cache)} 项")

    for i, name in enumerate(need_translate):
        try:
            r = translator.translate(name, src="en", dest="zh-CN")
            translated = r.text.strip()
            if translated and translated != name:
                result[name] = translated
                success += 1
            else:
                result[name] = name  # 翻译失败保留英文
        except Exception as e:
            logger.warning(f"翻译失败 '{name}': {e}")
            result[name] = name

        # 增量保存
        if (i + 1) % checkpoint_interval == 0:
            logger.info(f"进度: {i + 1}/{len(need_translate)} ({success} 成功)")
            save_cache(result, checkpoint_path)
            time.sleep(2)

    # 最终保存
    save_cache(result, checkpoint_path)
    logger.info(f"翻译完成: {success}/{len(need_translate)} 成功翻译为中文")
    return result


def save_cache(cache: dict, path: str):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def load_cache(path: str) -> dict:
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def translate_drug_classes():
    """翻译所有 drug_class_en"""
    logger.info("\n=== 翻译 drug_class_en ===")
    data = load_pipeline()
    drugs = data['merged_drugs']

    # 收集所有类别（含多类别逗号分隔）
    classes = set()
    for d in drugs.values():
        cls = d.get('drug_class_en', '')
        if cls:
            for c in cls.split(','):
                c = c.strip()
                if c:
                    classes.add(c)

    names = sorted(classes)
    cache_path = os.path.join(OUTPUT_DIR, "drug_class_translations.json")
    cache = load_cache(cache_path)

    result = translate_batch(names, cache, cache_path)

    # 统计
    translated = sum(1 for k, v in result.items() if k != v)
    logger.info(f"drug_class_en: {translated}/{len(names)} 翻译为中文")
    return result


def translate_conditions():
    """翻译所有适应症 condition 名"""
    logger.info("\n=== 翻译 conditions ===")
    data = load_pipeline()
    drugs = data['merged_drugs']

    conditions = set()
    for d in drugs.values():
        inds = d.get('indications', [])
        for ind in inds:
            if isinstance(ind, dict):
                c = ind.get('condition', '')
                if c:
                    conditions.add(c)

    names = sorted(conditions)
    cache_path = os.path.join(OUTPUT_DIR, "condition_translations.json")
    cache = load_cache(cache_path)

    result = translate_batch(names, cache, cache_path)

    translated = sum(1 for k, v in result.items() if k != v)
    logger.info(f"conditions: {translated}/{len(names)} 翻译为中文")
    return result


def translate_side_effects():
    """翻译 side_effects_raw — 提取关键词并翻译

    side_effects_raw 格式复杂（长句子、逗号分隔词列表等），
    策略: 提取独立副作用关键词 → 翻译每个关键词 → 组装为中文副作用列表
    """
    logger.info("\n=== 翻译 side_effects ===")
    data = load_pipeline()
    drugs = data['merged_drugs']

    # 提取所有副作用关键词
    keywords = set()
    for d in drugs.values():
        raw = d.get('side_effects_raw', '')
        if not raw:
            continue
        # 逗号和分号分隔
        parts = [p.strip().lower() for p in raw.replace(';', ',').split(',')]
        for p in parts:
            # 过滤太长的（整句话）和太短的（1-2字符）
            if 3 <= len(p) <= 60:
                # 去掉常见前缀词
                p = p.replace('may cause ', '').replace('call your doctor at once if you have: ', '')
                p = p.replace('stop using ', '').replace('severe ', '').strip()
                if p and len(p) >= 3:
                    keywords.add(p)

    names = sorted(keywords)
    logger.info(f"提取副作用关键词: {len(names)} 个")

    cache_path = os.path.join(OUTPUT_DIR, "side_effects_keyword_translations.json")
    cache = load_cache(cache_path)

    result = translate_batch(names, cache, cache_path)

    translated = sum(1 for k, v in result.items() if k != v)
    logger.info(f"side_effects keywords: {translated}/{len(names)} 翻译为中文")
    return result


def build_safety_enum_map():
    """构建 safetyType 和 qualityWarning 的中文映射"""
    logger.info("\n=== 构建枚举翻译映射 ===")
    map_path = os.path.join(OUTPUT_DIR, "enum_translations.json")

    enum_map = {
        # safetyType 枚举
        "safe": "安全",
        "relative_contraindication": "相对禁忌",
        "moderate_interaction": "中度交互",
        "severe_interaction": "严重交互",
        "absolute_contraindication": "绝对禁忌",

        # qualityWarning 枚举
        "NO_RELIABLE_RECOMMENDATION": "无可信推荐",
        "LOW_CONFIDENCE": "置信度低",

        # mode 枚举
        "model": "模型推理",
        "demo": "演示模式",
    }

    save_cache(enum_map, map_path)
    logger.info(f"枚举映射: {len(enum_map)} 项 → {map_path}")
    return enum_map


def main():
    logger.info("开始批量翻译...")

    # 1. 翻译 drug_class_en
    class_trans = translate_drug_classes()

    # 2. 翻译 conditions (matchedDisease)
    condition_trans = translate_conditions()

    # 3. 翻译 side_effects keywords
    se_trans = translate_side_effects()

    # 4. 构建枚举映射
    enum_map = build_safety_enum_map()

    # 汇总
    logger.info("\n=== 翻译汇总 ===")
    logger.info(f"drug_class: {len(class_trans)} 项")
    logger.info(f"conditions: {len(condition_trans)} 项")
    logger.info(f"side_effects keywords: {len(se_trans)} 项")
    logger.info(f"enum mappings: {len(enum_map)} 项")
    logger.info(f"缓存目录: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
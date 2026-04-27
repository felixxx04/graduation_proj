"""药物英文名→中文名翻译模块

启动时一次性翻译所有药物名并缓存到 data/drug_name_translations.json。
智能检测：药物数量变化或缓存不存在时重新翻译。

翻译策略:
1. 优先使用已有翻译缓存
2. 缓存不存在或药物数量变化时，逐个调用 googletrans 翻译
3. 翻译失败时保留英文原名
4. 每批次翻译后增量保存缓存，避免中途失败丢失进度
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict

from app.config import settings

logger = logging.getLogger(__name__)

CACHE_FILENAME = "drug_name_translations.json"


def _get_cache_path() -> Path:
    return Path(settings.data_dir) / CACHE_FILENAME


def load_translation_cache() -> Dict[str, str]:
    """加载翻译缓存文件

    Returns:
        英文名→中文名映射字典
    """
    cache_path = _get_cache_path()
    if not cache_path.exists():
        logger.info(f"Translation cache not found at {cache_path}")
        return {}

    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            cache = json.load(f)
        logger.info(f"Loaded translation cache: {len(cache)} entries from {cache_path}")
        return cache
    except Exception as e:
        logger.error(f"Failed to load translation cache: {e}", exc_info=True)
        return {}


def _save_cache(cache: Dict[str, str]) -> None:
    """保存翻译缓存到文件"""
    cache_path = _get_cache_path()
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved translation cache: {len(cache)} entries to {cache_path}")
    except Exception as e:
        logger.error(f"Failed to save translation cache: {e}", exc_info=True)


def _translate_one(name: str, translator) -> str:
    """翻译单个药物名，失败时返回英文原名"""
    try:
        result = translator.translate(name, src="en", dest="zh-CN")
        translated = result.text.strip()
        # 翻译结果验证：不为空且不是原文
        if translated and translated != name:
            return translated
        return name
    except Exception as e:
        logger.warning(f"Failed to translate '{name}': {e}")
        return name


def _translate_with_googletrans(names: list[str]) -> Dict[str, str]:
    """使用 googletrans 逐个翻译药物名

    每翻译50个药物名后增量保存缓存，避免中途失败丢失进度。

    Args:
        names: 英文药物名列表

    Returns:
        英文名→中文翻译名映射
    """
    from googletrans import Translator

    translator = Translator()
    result: Dict[str, str] = {}
    checkpoint_interval = 50
    success_count = 0

    for i, name in enumerate(names):
        translated = _translate_one(name, translator)
        result[name] = translated
        if translated != name:
            success_count += 1

        # 增量保存 + 日志
        if (i + 1) % checkpoint_interval == 0:
            logger.info(
                f"Translation progress: {i + 1}/{len(names)} names, "
                f"{success_count} successfully translated"
            )
            # 增量保存
            _save_cache(result)
            # 避免请求过快
            time.sleep(2)

    # 最终保存
    if result:
        _save_cache(result)

    logger.info(
        f"Translation complete: {len(names)} names, "
        f"{success_count}/{len(names)} successfully translated to Chinese"
    )
    return result


def build_translation_cache(drugs_data: list[dict]) -> Dict[str, str]:
    """构建翻译缓存

    智能检测：如果缓存文件存在且药物数量匹配，直接使用缓存；
    否则重新翻译并保存。

    Args:
        drugs_data: 药物数据列表，每项需有 generic_name 或 name 字段

    Returns:
        英文名→中文名映射字典
    """
    existing_cache = load_translation_cache()

    # 提取所有英文药物名
    english_names = []
    for drug in drugs_data:
        name = drug.get("generic_name", drug.get("name", ""))
        if name:
            english_names.append(name)

    # 智能检测：药物数量是否变化
    if existing_cache and len(existing_cache) >= len(english_names):
        # 检查是否有新增药物名不在缓存中
        missing = [n for n in english_names if n not in existing_cache]
        if not missing:
            translated_count = sum(1 for k, v in existing_cache.items() if k != v)
            logger.info(
                f"Translation cache valid: {len(existing_cache)} entries "
                f"({translated_count} translated) match current {len(english_names)} drugs"
            )
            return existing_cache
        else:
            logger.info(f"Translation cache missing {len(missing)} new drug names, will translate those")

    # 需要翻译的药物名：已有缓存中成功翻译的不重新翻译
    already_translated = {
        k: v for k, v in existing_cache.items()
        if k != v  # 只保留成功翻译的
    }
    need_translate = [n for n in english_names if n not in already_translated]

    logger.info(
        f"Building translation cache: {len(need_translate)} names need translation, "
        f"{len(already_translated)} already cached"
    )

    if need_translate:
        try:
            new_translations = _translate_with_googletrans(need_translate)
            # 合并：已有翻译 + 新翻译
            merged = dict(already_translated)
            merged.update(new_translations)
        except Exception as e:
            logger.error(f"Translation failed: {e}", exc_info=True)
            # 翻译完全失败，保留已有缓存
            merged = dict(existing_cache)
            for name in english_names:
                if name not in merged:
                    merged[name] = name
    else:
        merged = dict(already_translated)

    # 确保所有药物名都在映射中
    for name in english_names:
        if name not in merged:
            merged[name] = name

    # 保存最终缓存
    _save_cache(merged)

    return merged


def translate_drug_name(
    english_name: str,
    translation_map: Dict[str, str],
) -> str:
    """翻译单个药物名

    Args:
        english_name: 英文药物名
        translation_map: 翻译映射字典

    Returns:
        中文药物名，找不到时返回英文原名
    """
    if not english_name:
        return english_name
    return translation_map.get(english_name, english_name)
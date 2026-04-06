"""
JSON 解析辅助函数
统一处理 JSON 字符串解析，避免重复代码
"""

import json
from typing import Any, List


def safe_parse_json_list(value: Any, default: List = None) -> List[Any]:
    """
    安全地将字符串或列表转换为列表

    Args:
        value: 输入值（可能是字符串、列表或其他）
        default: 解析失败时的默认返回值

    Returns:
        解析后的列表
    """
    if default is None:
        default = []

    if isinstance(value, list):
        return value

    if isinstance(value, str):
        if not value.strip():
            return default
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
            return [parsed] if parsed else default
        except (json.JSONDecodeError, TypeError):
            return [value] if value else default

    return default


def safe_parse_json_dict(value: Any, default: dict = None) -> dict:
    """
    安全地将字符串或字典转换为字典

    Args:
        value: 输入值
        default: 解析失败时的默认返回值

    Returns:
        解析后的字典
    """
    if default is None:
        default = {}

    if isinstance(value, dict):
        return value

    if isinstance(value, str):
        if not value.strip():
            return default
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
            return default
        except (json.JSONDecodeError, TypeError):
            return default

    return default

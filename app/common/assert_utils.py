from __future__ import annotations

from typing import Any


def assert_not_none(value: Any, message: str) -> None:
    """要求值不为 None，否则抛出 ValueError。"""
    if value is None:
        raise ValueError(message)


def assert_not_blank(value: str | None, message: str) -> None:
    """要求字符串非空（非 None 且 strip 后非空），否则抛出 ValueError。"""
    if not value or not value.strip():
        raise ValueError(message)


def assert_not_empty(collection: list | dict | set | None, message: str) -> None:
    """要求集合非空，否则抛出 ValueError。"""
    if not collection:
        raise ValueError(message)


def assert_true(condition: bool, message: str) -> None:
    """要求条件为 True，否则抛出 ValueError。"""
    if not condition:
        raise ValueError(message)


def assert_in(key: str, mapping: dict, message: str) -> Any:
    """要求 key 存在于 mapping 中，否则抛出 ValueError。返回对应值。"""
    value = mapping.get(key)
    if value is None:
        raise ValueError(message)
    return value

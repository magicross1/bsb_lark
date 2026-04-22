from __future__ import annotations

from typing import Any, Callable


def pluck(records: list[dict[str, Any]], field: str) -> list[str]:
    """提取所有记录中指定字段的非空值列表。

    等价于 ``[v for r in records if (v := r.get(field))]``
    """
    return [v for r in records if (v := r.get(field))]


def to_map(
    records: list[dict[str, Any]],
    key_field: str,
    value_field: str = "record_id",
) -> dict[str, Any]:
    """构建 key_field → value_field 的映射（跳过 key 为空的记录）。

    等价于 ``{r[key_field]: r[value_field] for r in records if r.get(key_field)}``
    """
    return {r[key_field]: r[value_field] for r in records if r.get(key_field)}


def filter_by(
    records: list[dict[str, Any]],
    field: str,
    values: set[str] | list[str],
) -> list[dict[str, Any]]:
    """过滤出指定字段值在 values 中的记录。"""
    s = values if isinstance(values, set) else set(values)
    return [r for r in records if r.get(field) in s]


def group_by(
    records: list[dict[str, Any]],
    key_fn: Callable[[dict[str, Any]], str | None],
) -> dict[str, list[dict[str, Any]]]:
    """按 key_fn 分组，跳过返回 None 的记录。"""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for r in records:
        key = key_fn(r)
        if key is not None:
            grouped.setdefault(key, []).append(r)
    return grouped


def partition(
    records: list[dict[str, Any]],
    predicate: Callable[[dict[str, Any]], bool],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """按谓词将记录分为 (匹配, 不匹配) 两组。"""
    yes: list[dict[str, Any]] = []
    no: list[dict[str, Any]] = []
    for r in records:
        (yes if predicate(r) else no).append(r)
    return yes, no

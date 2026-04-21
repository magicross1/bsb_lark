from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from app.core.lark_bitable_value import extract_cell_text


@dataclass(frozen=True)
class _Clause:
    expr: str | None
    predicate: Callable[[dict[str, Any]], bool] | None = None


def _field_text(record: dict[str, Any], key: str) -> str | None:
    return extract_cell_text(record.get(key))


class BitableQuery:
    """链式 Bitable 过滤条件构建器。

    每个子句同时存储服务端 filter_expr 和客户端 predicate:
    - build()   → 服务端预筛选，减少数据拉取
    - filter()  → 客户端精筛，处理 Bitable 无法表达的条件

    用法:
        q = (BitableQuery()
             .not_empty("Terminal Full Name")
             .not_in("Clear Status", ["CLEAR", "RELEASED"]))
        filter_expr = q.build()        # 服务端
        pending = q.filter(records)    # 客户端

        # 任一字段为空
        BitableQuery().any_empty(["VesselIn", "InVoyage"])

        # 字段为空或不在列表中
        BitableQuery().not_in_or_empty("Status", ["Y", "SP"])

        # 纯客户端条件 (Bitable 无法表达)
        BitableQuery().is_empty("DISCHARGE_Time").client_filter(_eta_passed)
    """

    def __init__(self) -> None:
        self._clauses: list[_Clause] = []

    # ── 基础条件 ─────────────────────────────────────────────

    def eq(self, field: str, value: str) -> BitableQuery:
        self._clauses.append(_Clause(
            expr=f'CurrentValue.[{field}]="{value}"',
            predicate=lambda r, _f=field, _v=value: _field_text(r, _f) == _v,
        ))
        return self

    def ne(self, field: str, value: str) -> BitableQuery:
        self._clauses.append(_Clause(
            expr=f'CurrentValue.[{field}]!="{value}"',
            predicate=lambda r, _f=field, _v=value: _field_text(r, _f) != _v,
        ))
        return self

    def not_empty(self, field: str) -> BitableQuery:
        self._clauses.append(_Clause(
            expr=f'CurrentValue.[{field}]!=""',
            predicate=lambda r, _f=field: bool(_field_text(r, _f)),
        ))
        return self

    def is_empty(self, field: str) -> BitableQuery:
        self._clauses.append(_Clause(
            expr=f'CurrentValue.[{field}]=""',
            predicate=lambda r, _f=field: not bool(_field_text(r, _f)),
        ))
        return self

    def not_in(self, field: str, values: list[str]) -> BitableQuery:
        expr_parts = [f'CurrentValue.[{field}]!="{v}"' for v in values]
        expr = f'AND({", ".join(expr_parts)})' if len(expr_parts) > 1 else expr_parts[0]
        values_set = set(v.upper() for v in values)
        self._clauses.append(_Clause(
            expr=expr,
            predicate=lambda r, _f=field, _vs=values_set: (
                (t := _field_text(r, _f)) is not None and t.upper() not in _vs
            ),
        ))
        return self

    def in_list(self, field: str, values: list[str]) -> BitableQuery:
        parts = [f'CurrentValue.[{field}]="{v}"' for v in values]
        expr = f'OR({", ".join(parts)})'
        values_set = set(v.upper() for v in values)
        self._clauses.append(_Clause(
            expr=expr,
            predicate=lambda r, _f=field, _vs=values_set: (
                (t := _field_text(r, _f)) is not None and t.upper() in _vs
            ),
        ))
        return self

    # ── 组合条件 ─────────────────────────────────────────────

    def any_empty(self, fields: list[str]) -> BitableQuery:
        """任一字段为空 → OR(f1="", f2="", ...)。"""
        parts = [f'CurrentValue.[{f}]=""' for f in fields]
        expr = f'OR({", ".join(parts)})' if len(parts) > 1 else parts[0]
        fields_tuple = tuple(fields)
        self._clauses.append(_Clause(
            expr=expr,
            predicate=lambda r, _fs=fields_tuple: any(not bool(_field_text(r, f)) for f in _fs),
        ))
        return self

    def not_in_or_empty(self, field: str, values: list[str]) -> BitableQuery:
        """字段为空或不在列表中 → OR(field="", AND(field!="v1", field!="v2"))。

        比 not_in 多包含空值记录，适合"状态未确认"类筛选。
        """
        ne_parts = [f'CurrentValue.[{field}]!="{v}"' for v in values]
        ne_expr = f'AND({", ".join(ne_parts)})' if len(ne_parts) > 1 else ne_parts[0]
        expr = f'OR(CurrentValue.[{field}]="", {ne_expr})'
        values_set = set(v.upper() for v in values)
        self._clauses.append(_Clause(
            expr=expr,
            predicate=lambda r, _f=field, _vs=values_set: (
                (t := _field_text(r, _f)) is None or not t or t.upper() not in _vs
            ),
        ))
        return self

    # ── 数值比较 ─────────────────────────────────────────────

    def gt(self, field: str, value: Any) -> BitableQuery:
        self._clauses.append(_Clause(
            expr=f'CurrentValue.[{field}]>{value}',
            predicate=lambda r, _f=field, _v=value: _compare(r, _f, lambda x: x > _v),
        ))
        return self

    def gte(self, field: str, value: Any) -> BitableQuery:
        self._clauses.append(_Clause(
            expr=f'CurrentValue.[{field}]>={value}',
            predicate=lambda r, _f=field, _v=value: _compare(r, _f, lambda x: x >= _v),
        ))
        return self

    def lt(self, field: str, value: Any) -> BitableQuery:
        self._clauses.append(_Clause(
            expr=f'CurrentValue.[{field}]<{value}',
            predicate=lambda r, _f=field, _v=value: _compare(r, _f, lambda x: x < _v),
        ))
        return self

    def lte(self, field: str, value: Any) -> BitableQuery:
        self._clauses.append(_Clause(
            expr=f'CurrentValue.[{field}]<={value}',
            predicate=lambda r, _f=field, _v=value: _compare(r, _f, lambda x: x <= _v),
        ))
        return self

    # ── 扩展入口 ─────────────────────────────────────────────

    def client_filter(self, predicate: Callable[[dict[str, Any]], bool]) -> BitableQuery:
        """纯客户端筛选 — 用于 Bitable 无法表达的条件 (如 ETA < now)。"""
        self._clauses.append(_Clause(expr=None, predicate=predicate))
        return self

    def raw(self, expr: str, predicate: Callable[[dict[str, Any]], bool] | None = None) -> BitableQuery:
        """直接拼接原始 filter_expr (仅在其他方法无法表达时使用)。"""
        self._clauses.append(_Clause(expr=expr, predicate=predicate))
        return self

    # ── 输出 ─────────────────────────────────────────────────

    def build(self) -> str | None:
        """构建服务端 filter_expr。无条件时返回 None。"""
        exprs = [c.expr for c in self._clauses if c.expr is not None]
        if not exprs:
            return None
        if len(exprs) == 1:
            return exprs[0]
        return f'AND({", ".join(exprs)})'

    def filter(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """客户端精筛 — 对记录应用所有子句的 predicate。"""
        predicates = [c.predicate for c in self._clauses if c.predicate is not None]
        if not predicates:
            return records
        return [r for r in records if all(p(r) for p in predicates)]

    def has_client_filter(self) -> bool:
        return any(c.predicate is not None for c in self._clauses)


def _compare(record: dict[str, Any], field: str, op: Callable[[float], bool]) -> bool:
    text = _field_text(record, field)
    if not text:
        return False
    try:
        return op(float(text))
    except (ValueError, TypeError):
        return False

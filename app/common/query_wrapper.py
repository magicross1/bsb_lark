from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class _Clause:
    condition_node: dict[str, Any] | None  # 服务端过滤节点（None = 纯客户端条件）
    predicate: Callable[[dict[str, Any]], bool] | None = None  # 客户端精筛谓词


def _fv(record: dict[str, Any], field: str) -> str:
    """获取字段值为字符串（None / 缺失 → 空字符串）。"""
    v = record.get(field)
    return str(v).strip() if v is not None else ""


class QueryWrapper:
    """链式 Bitable 查询条件构建器（类 MyBatis-Plus QueryWrapper）。

    用法::

        records = await repo.list(
            QueryWrapper()
            .select("Container Number", "Terminal Full Name")
            .not_empty("Terminal Full Name")
            .not_in("Clear Status", ["CLEAR", "RELEASED"])
            .order_by("EstimatedArrival")
        )

        record = await repo.findOne(
            QueryWrapper().eq("Container Number", "ABCD1234567")
        )
    """

    def __init__(self) -> None:
        self._clauses: list[_Clause] = []
        self._field_names: list[str] | None = None
        self._sort_list: list[dict[str, Any]] | None = None
        self._record_id_hint: str | None = None   # eq("record_id", ...) 时写入，供 findOne/delete 直连 API 使用
        self._record_ids_hint: list[str] | None = None  # in_list("record_id", ...) 时写入，供 list() 走 batch_get API

    # ── 投影 ─────────────────────────────────────────────────

    def select(self, *field_names: str) -> QueryWrapper:
        """指定返回的字段列表（不调用则返回所有字段）。"""
        self._field_names = list(field_names)
        return self

    # ── 排序 ─────────────────────────────────────────────────

    def order_by(self, field: str, *, desc: bool = False) -> QueryWrapper:
        """添加排序字段，可多次链式调用叠加多列排序。"""
        if self._sort_list is None:
            self._sort_list = []
        self._sort_list.append({"field_name": field, "desc": desc})
        return self

    # ── 基础条件 ─────────────────────────────────────────────

    def eq(self, field: str, value: str) -> QueryWrapper:
        if field == "record_id":
            # record_id 不是 Bitable 可筛选字段，仅记录提示供 find/delete 直接调用 API
            self._record_id_hint = value
            self._clauses.append(_Clause(
                condition_node=None,
                predicate=lambda r, _v=value: r.get("record_id") == _v,
            ))
        else:
            self._clauses.append(_Clause(
                condition_node={"field_name": field, "operator": "is", "value": [value]},
                predicate=lambda r, _f=field, _v=value: _fv(r, _f) == _v,
            ))
        return self

    def ne(self, field: str, value: str) -> QueryWrapper:
        self._clauses.append(_Clause(
            condition_node={"field_name": field, "operator": "isNot", "value": [value]},
            predicate=lambda r, _f=field, _v=value: _fv(r, _f) != _v,
        ))
        return self

    def not_empty(self, field: str) -> QueryWrapper:
        self._clauses.append(_Clause(
            condition_node={"field_name": field, "operator": "isNotEmpty", "value": []},
            predicate=lambda r, _f=field: bool(_fv(r, _f)),
        ))
        return self

    def is_empty(self, field: str) -> QueryWrapper:
        self._clauses.append(_Clause(
            condition_node={"field_name": field, "operator": "isEmpty", "value": []},
            predicate=lambda r, _f=field: not bool(_fv(r, _f)),
        ))
        return self

    def not_in(self, field: str, values: list[str]) -> QueryWrapper:
        ne_nodes = [{"field_name": field, "operator": "isNot", "value": [v]} for v in values]
        condition_node = ne_nodes[0] if len(ne_nodes) == 1 else {"conjunction": "and", "conditions": ne_nodes}
        values_upper = {v.upper() for v in values}
        self._clauses.append(_Clause(
            condition_node=condition_node,
            predicate=lambda r, _f=field, _vs=values_upper: (
                (v := _fv(r, _f)) != "" and v.upper() not in _vs
            ),
        ))
        return self

    def in_list(self, field: str, values: list[str]) -> QueryWrapper:
        if field == "record_id":
            # record_id 不是 Bitable 可筛选字段，记录 hint 供 list() 走 batch_get API
            self._record_ids_hint = list(values)
            self._clauses.append(_Clause(
                condition_node=None,
                predicate=lambda r, _vs=set(values): r.get("record_id") in _vs,
            ))
        else:
            values_upper = {v.upper() for v in values}
            self._clauses.append(_Clause(
                condition_node={"field_name": field, "operator": "is", "value": values},
                predicate=lambda r, _f=field, _vs=values_upper: _fv(r, _f).upper() in _vs,
            ))
        return self

    # ── 组合条件 ─────────────────────────────────────────────

    def any_empty(self, fields: list[str]) -> QueryWrapper:
        """任一字段为空（OR 逻辑）。"""
        empty_nodes = [{"field_name": f, "operator": "isEmpty", "value": []} for f in fields]
        condition_node = (
            empty_nodes[0] if len(empty_nodes) == 1
            else {"conjunction": "or", "conditions": empty_nodes}
        )
        fields_tuple = tuple(fields)
        self._clauses.append(_Clause(
            condition_node=condition_node,
            predicate=lambda r, _fs=fields_tuple: any(not bool(_fv(r, f)) for f in _fs),
        ))
        return self

    def not_in_or_empty(self, field: str, values: list[str]) -> QueryWrapper:
        """字段为空 或 不在给定列表中。"""
        ne_nodes = [{"field_name": field, "operator": "isNot", "value": [v]} for v in values]
        not_in_part = ne_nodes[0] if len(ne_nodes) == 1 else {"conjunction": "and", "conditions": ne_nodes}
        condition_node = {
            "conjunction": "or",
            "conditions": [{"field_name": field, "operator": "isEmpty", "value": []}, not_in_part],
        }
        values_upper = {v.upper() for v in values}
        self._clauses.append(_Clause(
            condition_node=condition_node,
            predicate=lambda r, _f=field, _vs=values_upper: (
                (v := _fv(r, _f)) == "" or v.upper() not in _vs
            ),
        ))
        return self

    # ── 数值比较 ─────────────────────────────────────────────

    def gt(self, field: str, value: Any) -> QueryWrapper:
        self._clauses.append(_Clause(
            condition_node={"field_name": field, "operator": "isGreater", "value": [str(value)]},
            predicate=lambda r, _f=field, _v=value: _numeric_cmp(r, _f, lambda x: x > _v),
        ))
        return self

    def gte(self, field: str, value: Any) -> QueryWrapper:
        self._clauses.append(_Clause(
            condition_node={"field_name": field, "operator": "isGreaterEqual", "value": [str(value)]},
            predicate=lambda r, _f=field, _v=value: _numeric_cmp(r, _f, lambda x: x >= _v),
        ))
        return self

    def lt(self, field: str, value: Any) -> QueryWrapper:
        self._clauses.append(_Clause(
            condition_node={"field_name": field, "operator": "isLess", "value": [str(value)]},
            predicate=lambda r, _f=field, _v=value: _numeric_cmp(r, _f, lambda x: x < _v),
        ))
        return self

    def lte(self, field: str, value: Any) -> QueryWrapper:
        self._clauses.append(_Clause(
            condition_node={"field_name": field, "operator": "isLessEqual", "value": [str(value)]},
            predicate=lambda r, _f=field, _v=value: _numeric_cmp(r, _f, lambda x: x <= _v),
        ))
        return self

    # ── 纯客户端条件 ─────────────────────────────────────────

    def client_filter(self, predicate: Callable[[dict[str, Any]], bool]) -> QueryWrapper:
        """添加纯客户端筛选（用于 Bitable 无法表达的条件，如 ETA < now）。"""
        self._clauses.append(_Clause(condition_node=None, predicate=predicate))
        return self

    # ── 内部输出（仅供 BaseRepository 调用）─────────────────

    def _get_record_id_hint(self) -> str | None:
        """返回通过 eq('record_id', ...) 写入的 record_id，供 findOne/delete 走直连 API 路径。"""
        return self._record_id_hint

    def _get_record_ids_hint(self) -> list[str] | None:
        """返回通过 in_list('record_id', ...) 写入的 id 列表，供 list() 走 batch_get API 路径。"""
        return self._record_ids_hint

    def _to_filter(self) -> dict[str, Any] | None:
        """构建服务端过滤条件（传给 search API 的 filter 字段）。"""
        nodes = [c.condition_node for c in self._clauses if c.condition_node is not None]
        if not nodes:
            return None
        if len(nodes) == 1:
            node = nodes[0]
            if "conjunction" in node:
                return node
            return {"conjunction": "and", "conditions": [node]}
        return {"conjunction": "and", "conditions": nodes}

    def _to_field_names(self) -> list[str] | None:
        return self._field_names

    def _to_sort(self) -> list[dict[str, Any]] | None:
        return self._sort_list

    def _apply_client_filter(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """对已有记录应用所有客户端谓词。"""
        predicates = [c.predicate for c in self._clauses if c.predicate is not None]
        if not predicates:
            return records
        return [r for r in records if all(p(r) for p in predicates)]


def _numeric_cmp(record: dict[str, Any], field: str, op: Callable[[float], bool]) -> bool:
    v = _fv(record, field)
    if not v:
        return False
    try:
        return op(float(v))
    except (ValueError, TypeError):
        return False

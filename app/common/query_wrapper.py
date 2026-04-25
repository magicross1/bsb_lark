from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class _Clause:
    condition_node: dict[str, Any] | None
    predicate: Callable[[dict[str, Any]], bool] | None = None


def _fv(record: dict[str, Any], field: str) -> str:
    v = record.get(field)
    if v is None:
        return ""
    if isinstance(v, list):
        return ", ".join(str(item).strip() for item in v if item)
    return str(v).strip()


class QueryWrapper:
    """链式 Bitable 查询条件构建器（类 MyBatis-Plus QueryWrapper）。

    用法::

        # 服务端+客户端双筛（Repository 日常查询）
        records = await repo.list(
            QueryWrapper()
            .select("Container Number", "Terminal Full Name")
            .not_empty("Terminal Full Name")
            .not_in("Clear Status", ["CLEAR", "RELEASED"])
        )

        # 纯客户端筛（批量同步条件，避免 Bitable filter 语法坑）
        records = await repo.list(
            QueryWrapper().client_only()
            .not_empty("Terminal Full Name")
            .is_empty("GATEOUT_Time")
        )

        record = await repo.findOne(
            QueryWrapper().eq("Container Number", "ABCD1234567")
        )
    """

    def __init__(self) -> None:
        self._clauses: list[_Clause] = []
        self._field_names: list[str] | None = None
        self._sort_list: list[dict[str, Any]] | None = None
        self._record_id_hint: str | None = None
        self._record_ids_hint: list[str] | None = None
        self._client_only: bool = False

    def client_only(self) -> QueryWrapper:
        """纯客户端筛模式：不生成服务端 filter，只靠本地 predicate 筛选。

        适用于批量同步条件配置，避免 Bitable filter 语法兼容性问题。
        数据量小时（<1000条）无性能差异。
        """
        self._client_only = True
        return self

    def _cn(self, node: dict[str, Any] | None) -> dict[str, Any] | None:
        return None if self._client_only else node

    # ── 投影 ─────────────────────────────────────────────────

    def select(self, *field_names: str) -> QueryWrapper:
        self._field_names = list(field_names)
        return self

    # ── 排序 ─────────────────────────────────────────────────

    def order_by(self, field: str, *, desc: bool = False) -> QueryWrapper:
        if self._sort_list is None:
            self._sort_list = []
        self._sort_list.append({"field_name": field, "desc": desc})
        return self

    # ── 基础条件 ─────────────────────────────────────────────

    def eq(self, field: str, value: str) -> QueryWrapper:
        if field == "record_id":
            self._record_id_hint = value
            self._clauses.append(_Clause(
                condition_node=None,
                predicate=lambda r, _v=value: r.get("record_id") == _v,
            ))
        else:
            self._clauses.append(_Clause(
                condition_node=self._cn({"field_name": field, "operator": "is", "value": [value]}),
                predicate=lambda r, _f=field, _v=value: _fv(r, _f) == _v,
            ))
        return self

    def ne(self, field: str, value: str) -> QueryWrapper:
        self._clauses.append(_Clause(
            condition_node=self._cn({"field_name": field, "operator": "isNot", "value": [value]}),
            predicate=lambda r, _f=field, _v=value: _fv(r, _f) != _v,
        ))
        return self

    def not_empty(self, field: str) -> QueryWrapper:
        self._clauses.append(_Clause(
            condition_node=self._cn({"field_name": field, "operator": "isNotEmpty", "value": []}),
            predicate=lambda r, _f=field: bool(_fv(r, _f)),
        ))
        return self

    def is_empty(self, field: str) -> QueryWrapper:
        self._clauses.append(_Clause(
            condition_node=self._cn({"field_name": field, "operator": "isEmpty", "value": []}),
            predicate=lambda r, _f=field: not bool(_fv(r, _f)),
        ))
        return self

    def not_in(self, field: str, values: list[str]) -> QueryWrapper:
        ne_nodes = [{"field_name": field, "operator": "isNot", "value": [v]} for v in values]
        condition_node = ne_nodes[0] if len(ne_nodes) == 1 else {"conjunction": "and", "conditions": ne_nodes}
        values_upper = {v.upper() for v in values}
        self._clauses.append(_Clause(
            condition_node=self._cn(condition_node),
            predicate=lambda r, _f=field, _vs=values_upper: (
                (v := _fv(r, _f)) != "" and v.upper() not in _vs
            ),
        ))
        return self

    def in_list(self, field: str, values: list[str]) -> QueryWrapper:
        if field == "record_id":
            self._record_ids_hint = list(values)
            self._clauses.append(_Clause(
                condition_node=None,
                predicate=lambda r, _vs=set(values): r.get("record_id") in _vs,
            ))
        else:
            values_upper = {v.upper() for v in values}
            self._clauses.append(_Clause(
                condition_node=self._cn({"field_name": field, "operator": "is", "value": values}),
                predicate=lambda r, _f=field, _vs=values_upper: _fv(r, _f).upper() in _vs,
            ))
        return self

    # ── 组合条件 ─────────────────────────────────────────────

    def any_empty(self, fields: list[str]) -> QueryWrapper:
        empty_nodes = [{"field_name": f, "operator": "isEmpty", "value": []} for f in fields]
        condition_node = (
            empty_nodes[0] if len(empty_nodes) == 1
            else {"conjunction": "or", "conditions": empty_nodes}
        )
        fields_tuple = tuple(fields)
        self._clauses.append(_Clause(
            condition_node=self._cn(condition_node),
            predicate=lambda r, _fs=fields_tuple: any(not bool(_fv(r, f)) for f in _fs),
        ))
        return self

    def not_in_or_empty(self, field: str, values: list[str]) -> QueryWrapper:
        ne_nodes = [{"field_name": field, "operator": "isNot", "value": [v]} for v in values]
        not_in_part = ne_nodes[0] if len(ne_nodes) == 1 else {"conjunction": "and", "conditions": ne_nodes}
        condition_node = {
            "conjunction": "or",
            "conditions": [{"field_name": field, "operator": "isEmpty", "value": []}, not_in_part],
        }
        values_upper = {v.upper() for v in values}
        self._clauses.append(_Clause(
            condition_node=self._cn(condition_node),
            predicate=lambda r, _f=field, _vs=values_upper: (
                (v := _fv(r, _f)) == "" or v.upper() not in _vs
            ),
        ))
        return self

    # ── 数值比较 ─────────────────────────────────────────────

    def gt(self, field: str, value: Any) -> QueryWrapper:
        self._clauses.append(_Clause(
            condition_node=self._cn({"field_name": field, "operator": "isGreater", "value": [str(value)]}),
            predicate=lambda r, _f=field, _v=value: _numeric_cmp(r, _f, lambda x: x > _v),
        ))
        return self

    def gte(self, field: str, value: Any) -> QueryWrapper:
        self._clauses.append(_Clause(
            condition_node=self._cn({"field_name": field, "operator": "isGreaterEqual", "value": [str(value)]}),
            predicate=lambda r, _f=field, _v=value: _numeric_cmp(r, _f, lambda x: x >= _v),
        ))
        return self

    def lt(self, field: str, value: Any) -> QueryWrapper:
        self._clauses.append(_Clause(
            condition_node=self._cn({"field_name": field, "operator": "isLess", "value": [str(value)]}),
            predicate=lambda r, _f=field, _v=value: _numeric_cmp(r, _f, lambda x: x < _v),
        ))
        return self

    def lte(self, field: str, value: Any) -> QueryWrapper:
        self._clauses.append(_Clause(
            condition_node=self._cn({"field_name": field, "operator": "isLessEqual", "value": [str(value)]}),
            predicate=lambda r, _f=field, _v=value: _numeric_cmp(r, _f, lambda x: x <= _v),
        ))
        return self

    # ── 纯客户端条件 ─────────────────────────────────────────

    def client_filter(self, predicate: Callable[[dict[str, Any]], bool]) -> QueryWrapper:
        self._clauses.append(_Clause(condition_node=None, predicate=predicate))
        return self

    # ── 内部输出（仅供 BaseRepository 调用）─────────────────

    def _get_record_id_hint(self) -> str | None:
        return self._record_id_hint

    def _get_record_ids_hint(self) -> list[str] | None:
        return self._record_ids_hint

    def _to_filter(self) -> dict[str, Any] | None:
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

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.common.query_wrapper import QueryWrapper


class UpdateWrapper:
    """链式 Bitable 更新条件 + 赋值构造器（类 MyBatis-Plus LambdaUpdateWrapper）。

    用法::

        # 按 record_id 更新单条
        await repo.update(
            UpdateWrapper().eq("record_id", rid).set("Status", "Done").set("Tag", "OK")
        )

        # 条件更新：所有满足条件的记录统一 set
        await repo.update(
            UpdateWrapper().eq("Status", "Pending").set("Status", "Processing")
        )

        # 批量 by-id 更新（sync 场景，每条字段不同）
        await repo.update_many([
            UpdateWrapper().eq("record_id", r.record_id).set_all(r.fields).with_label(r.cn)
            for r in data_list
        ])
    """

    def __init__(self) -> None:
        from app.common.query_wrapper import QueryWrapper
        self._query: QueryWrapper = QueryWrapper()
        self._updates: dict[str, Any] = {}
        self._label: str = ""

    # ── 条件（委托给内部 QueryWrapper）────────────────────────

    def eq(self, field: str, value: str) -> UpdateWrapper:
        self._query.eq(field, value)
        return self

    def not_empty(self, field: str) -> UpdateWrapper:
        self._query.not_empty(field)
        return self

    def is_empty(self, field: str) -> UpdateWrapper:
        self._query.is_empty(field)
        return self

    def not_in(self, field: str, values: list[str]) -> UpdateWrapper:
        self._query.not_in(field, values)
        return self

    def ne(self, field: str, value: str) -> UpdateWrapper:
        self._query.ne(field, value)
        return self

    # ── 赋值 ─────────────────────────────────────────────────

    def set(self, field: str, value: Any) -> UpdateWrapper:
        """设置单个字段值。"""
        self._updates[field] = value
        return self

    def set_all(self, fields: dict[str, Any]) -> UpdateWrapper:
        """批量设置字段值（合并到已有 set 中）。"""
        self._updates.update(fields)
        return self

    # ── 元数据 ────────────────────────────────────────────────

    def with_label(self, label: str) -> UpdateWrapper:
        """设置日志标签（不写入 Bitable）。"""
        self._label = label
        return self

    # ── 内部接口（仅供 BaseRepository 调用）──────────────────

    def _get_query(self) -> QueryWrapper:
        return self._query

    def _get_fields(self) -> dict[str, Any]:
        return self._updates

    def _get_label(self) -> str:
        return self._label

    def _get_record_id_hint(self) -> str | None:
        return self._query._get_record_id_hint()

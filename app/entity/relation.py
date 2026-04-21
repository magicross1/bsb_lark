from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.common.lark_repository import BaseRepository
from app.common.query_wrapper import QueryWrapper
from app.core.lark_bitable_value import extract_cell_text, extract_link_record_ids

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RelationHop:
    table_id: str
    link_field: str
    field_names: list[str] | None = None

    @property
    def cache_key(self) -> str:
        return f"relation:{self.table_id}"


class RelationResolver:
    """声明式跨表关联解析器。

    用法::

        resolver = RelationResolver()

        # 定义路径: Op-Cartage → (Consingee link) → MD-Consingee.Name
        result = await resolver.resolve(
            start_table_id="tblKUPmqga4woLk5",
            start_record_id="recXXX",
            path=[
                RelationHop(table_id="tbli30rPlY5X5KT5", link_field="Consingee", field_names=["Name"]),
            ],
            target_field="Name",
        )
        # result = "APLUS MATERIALS"

    # 两跳: Cartage → Consingee → Warehouse Address
    result = await resolver.resolve(
        start_table_id="tblKUPmqga4woLk5",
        start_record_id="recXXX",
        path=[
            RelationHop(
                table_id="tbli30rPlY5X5KT5",
                link_field="Consingee",
                field_names=["Name", "MD-Warehouse Address"],
            ),
            RelationHop(
                table_id="tblDpXM58OER6hfB",
                link_field="MD-Warehouse Address",
                field_names=["Address"],
            ),
        ],
        target_field="Address",
    )
    """

    def __init__(self) -> None:
        self._record_cache: dict[str, dict[str, dict[str, Any]]] = {}
        self._repo_cache: dict[str, BaseRepository] = {}

    async def resolve(
        self,
        start_table_id: str,
        start_record_id: str,
        path: list[RelationHop],
        target_field: str | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]] | str | None:
        if not path:
            return None

        current_ids = [start_record_id]
        current_table_id = start_table_id

        for i, hop in enumerate(path):
            if not current_ids:
                return None

            records = await self._fetch_records(current_table_id, current_ids)

            next_ids: list[str] = []
            for rid in current_ids:
                rec = records.get(rid)
                if rec:
                    link_value = rec.get(hop.link_field)
                    ids = extract_link_record_ids(link_value)
                    next_ids.extend(ids)

            next_ids = list(dict.fromkeys(next_ids))

            is_last = i == len(path) - 1
            if is_last:
                if not next_ids:
                    return None
                target_records = await self._fetch_records(hop.table_id, next_ids)
                if target_field:
                    results: list[str | None] = []
                    for rid in next_ids:
                        rec = target_records.get(rid)
                        if rec:
                            results.append(extract_cell_text(rec.get(target_field)))
                    if not results:
                        return None
                    return results[0] if len(results) == 1 else [r for r in results if r is not None]
                else:
                    return [target_records[rid] for rid in next_ids if rid in target_records]

            current_ids = next_ids
            current_table_id = hop.table_id

        return None

    async def resolve_single(
        self,
        start_table_id: str,
        start_record_id: str,
        path: list[RelationHop],
        target_field: str,
    ) -> str | None:
        result = await self.resolve(start_table_id, start_record_id, path, target_field)
        if isinstance(result, str):
            return result
        if isinstance(result, list) and result:
            return str(result[0]) if result[0] else None
        return None

    async def resolve_records(
        self,
        start_table_id: str,
        start_record_id: str,
        path: list[RelationHop],
    ) -> list[dict[str, Any]]:
        result = await self.resolve(start_table_id, start_record_id, path)
        if isinstance(result, list):
            return result
        return []

    async def _fetch_records(
        self,
        table_id: str,
        record_ids: list[str],
    ) -> dict[str, dict[str, Any]]:
        cache_key = f"relation:{table_id}"
        cached = self._record_cache.get(cache_key, {})
        missing = [rid for rid in record_ids if rid not in cached]

        if missing:
            repo = self._get_repo(table_id)
            fetched = await repo.list(QueryWrapper().in_list("record_id", missing))
            for rec in fetched:
                rid = rec.get("record_id", "")
                if rid:
                    cached[rid] = rec
            self._record_cache[cache_key] = cached

        return {rid: cached[rid] for rid in record_ids if rid in cached}

    def _get_repo(self, table_id: str) -> BaseRepository:
        if table_id not in self._repo_cache:
            from app.common.lark_repository import BaseRepository

            class _DynamicRepo(BaseRepository):
                pass

            _DynamicRepo.table_id = table_id
            self._repo_cache[table_id] = _DynamicRepo()
        return self._repo_cache[table_id]

    def clear_cache(self) -> None:
        self._record_cache.clear()

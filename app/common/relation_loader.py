from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.common.lark_repository import LarkRepository

_BATCH_CHUNK_SIZE = 100


def extract_linked_ids(field_value: object) -> list[str]:
    """从关联字段值中提取所有 record_id。

    Lark 关联字段返回格式不固定，可能是：
    - str: 单个 record_id
    - list[str]: 多个 record_id
    - list[dict]: 每个 dict 含 record_ids (list) 或 record_id (str)
    """
    if field_value is None:
        return []
    if isinstance(field_value, str):
        return [field_value] if field_value else []
    if isinstance(field_value, list):
        ids: list[str] = []
        for item in field_value:
            if isinstance(item, str):
                ids.append(item)
            elif isinstance(item, dict):
                record_ids = item.get("record_ids")
                if record_ids:
                    ids.extend(record_ids)
                elif "record_id" in item:
                    ids.append(item["record_id"])
        return ids
    return []


@dataclass
class RelationConfig:
    """单条关联关系声明。

    Args:
        field_name:  主记录中存放关联 record_id 的字段名。
        repository:  关联表对应的 repository 实例。
        as_field:    注入到结果中的字段名；不填则使用 ``{field_name}__resolved``。
        load_fields: 只从关联表加载哪些字段；None 表示加载全部字段。
    """

    field_name: str
    repository: LarkRepository
    as_field: str | None = None
    load_fields: list[str] | None = None


class RelationLoader:
    """批量解析关联字段，消除 service 层的 N+1 串行调用。

    用法示例::

        resolved = await RelationLoader([
            RelationConfig("driver_field",    driver_repo,    as_field="driver"),
            RelationConfig("warehouse_field", warehouse_repo, as_field="warehouse"),
        ]).load(records)

    工作流程：
    1. 扫描主记录，收集每个关联字段的全部 record_id（去重）。
    2. 用 asyncio.gather 并发向所有关联表发 batch_get 请求。
    3. 每张表内部按 100 条分块再并发（规避 API 上限）。
    4. 将拉回的记录注入主记录：单值关联拆包为 dict，多值保留 list。
    """

    def __init__(self, relations: list[RelationConfig]) -> None:
        self._relations = relations

    async def load(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not records or not self._relations:
            return records

        resolved_maps: list[dict[str, dict[str, Any]]] = list(
            await asyncio.gather(*[self._fetch_relation(records, rel) for rel in self._relations])
        )

        result = [dict(r) for r in records]
        for rel, resolved_map in zip(self._relations, resolved_maps):
            inject_key = rel.as_field or f"{rel.field_name}__resolved"
            for record in result:
                linked_ids = extract_linked_ids(record.get(rel.field_name))
                resolved = [resolved_map[rid] for rid in linked_ids if rid in resolved_map]
                record[inject_key] = resolved[0] if len(resolved) == 1 else resolved

        return result

    async def _fetch_relation(
        self,
        records: list[dict[str, Any]],
        rel: RelationConfig,
    ) -> dict[str, dict[str, Any]]:
        all_ids: set[str] = set()
        for record in records:
            all_ids.update(extract_linked_ids(record.get(rel.field_name)))

        if not all_ids:
            return {}

        id_list = list(all_ids)
        chunks = [id_list[i : i + _BATCH_CHUNK_SIZE] for i in range(0, len(id_list), _BATCH_CHUNK_SIZE)]

        chunk_results: list[list[dict[str, Any]]] = list(
            await asyncio.gather(*[rel.repository.batch_get_records(chunk) for chunk in chunks])
        )

        return {r["record_id"]: r for chunk in chunk_results for r in chunk}

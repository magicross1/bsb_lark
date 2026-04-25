from __future__ import annotations

from typing import Any

from app.common.lark_repository import BaseRepository
from app.common.query_wrapper import QueryWrapper
from app.service.sync.utils.link_config import LinkConfig


async def build_select_field_map(
    repo: BaseRepository, field_name: str,
) -> dict[str, str]:
    """预加载目标表，构建 {多选字段值(大写): record_id} 映射。

    用于「A表文本值 → B表多选字段匹配 → 写回A表link」场景。
    自动处理 list[str]（多选）和逗号拼接 str（旧格式）。
    """
    records = await repo.list(QueryWrapper().select(field_name))
    result: dict[str, str] = {}
    for r in records:
        raw = r.get(field_name)
        if not raw:
            continue
        values = raw if isinstance(raw, list) else [v.strip() for v in str(raw).split(",") if v.strip()]
        for v in values:
            result[v.strip().upper()] = r["record_id"]
    return result


class LinkResolver:
    """通用关联字段解析器 — 根据显示文本查找目标表记录的 record_id。

    同一请求内自动缓存，相同 table+field+value 只查一次 Bitable。
    """

    def __init__(self) -> None:
        self._cache: dict[str, str | None] = {}

    async def resolve(self, config: LinkConfig, search_value: str) -> str | None:
        if not search_value:
            return None

        cache_key = f"{config.table_id}|{config.search_field}={search_value}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        from app.common.query_wrapper import QueryWrapper
        repo = _get_repo(config.table_id)
        record = await repo.findOne(QueryWrapper().eq(config.search_field, search_value))
        record_id = record.get("record_id") if record else None
        self._cache[cache_key] = record_id
        return record_id


_repo_cache: dict[str, Any] = {}


def _get_repo(table_id: str) -> Any:
    if table_id not in _repo_cache:
        from app.common.lark_repository import BaseRepository

        class _DynamicRepo(BaseRepository):
            pass

        _DynamicRepo.table_id = table_id
        _repo_cache[table_id] = _DynamicRepo()
    return _repo_cache[table_id]

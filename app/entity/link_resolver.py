from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.common.lark_repository import BaseRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NestedLink:
    source_key: str
    lookup: LinkLookup


@dataclass(frozen=True)
class LinkLookup:
    target_table_id: str
    search_field: str
    create_if_missing: bool = False
    create_fields: dict[str, str] = field(default_factory=dict)
    create_links: dict[str, NestedLink] = field(default_factory=dict)
    filter_conditions: list[tuple[str, str]] = field(default_factory=list)
    sort_field: str | None = None
    sort_desc: bool = False
    default_if_missing: str | None = None


class LinkFieldResolver:
    def __init__(self) -> None:
        self._repo_cache: dict[str, BaseRepository] = {}
        self._resolve_cache: dict[str, list[str]] = {}

    def _cache_key(self, lookup: LinkLookup, value: str, context: dict[str, Any] | None) -> str:
        extra = ""
        if lookup.filter_conditions and context:
            extra = "|".join(f"{fn}={context.get(ck, '')}" for fn, ck in lookup.filter_conditions)
        return f"{lookup.target_table_id}|{lookup.search_field}={value}|{extra}"

    async def resolve(
        self,
        lookup: LinkLookup,
        value: str,
        context: dict[str, Any] | None = None,
    ) -> list[str] | None:
        if not value:
            return None

        cache_key = self._cache_key(lookup, value, context)
        if cache_key in self._resolve_cache:
            logger.debug("Link cache hit: %s", cache_key)
            return self._resolve_cache[cache_key]

        repo = self._get_repo(lookup.target_table_id)
        ctx = {**(context or {}), "value": value}

        existing = await self._find_existing(repo, lookup, value, ctx)
        if existing:
            rid = existing["record_id"]
            logger.info("Link resolved: %s=%s → existing %s", lookup.search_field, value, rid)
            result = [rid]
            self._resolve_cache[cache_key] = result
            return result

        if lookup.create_if_missing:
            fields = await self._build_create_fields(lookup, value, context)
            created = await repo.createOne(fields)
            rid = created["record_id"]
            logger.info("Link resolved: %s=%s → created %s", lookup.search_field, value, rid)
            result = [rid]
            self._resolve_cache[cache_key] = result
            return result

        if lookup.default_if_missing:
            logger.warning("Link unresolved: %s=%s → default %s", lookup.search_field, value, lookup.default_if_missing)
            return None

        logger.warning("Link unresolved: %s=%s → no match and create_if_missing=False", lookup.search_field, value)
        return None

    async def _find_existing(
        self,
        repo: BaseRepository,
        lookup: LinkLookup,
        value: str,
        ctx: dict[str, Any],
    ) -> dict[str, Any] | None:
        from app.common.query_wrapper import QueryWrapper
        q = QueryWrapper().eq(lookup.search_field, value)
        for field_name, ctx_key in lookup.filter_conditions:
            ctx_value = ctx.get(ctx_key, "")
            if ctx_value:
                q = q.eq(field_name, str(ctx_value))
        return await repo.findOne(q)

    async def _build_create_fields(
        self,
        lookup: LinkLookup,
        value: str,
        context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        ctx = {**(context or {}), "value": value}
        fields: dict[str, Any] = {}
        for k, template in lookup.create_fields.items():
            if template.startswith("{") and template.endswith("}"):
                key = template[1:-1]
                fields[k] = ctx.get(key, "")
            else:
                fields[k] = template
        if lookup.search_field not in fields:
            fields[lookup.search_field] = value

        for field_name, nested in lookup.create_links.items():
            sub_value = ctx.get(nested.source_key, "")
            if sub_value:
                sub_ids = await self.resolve(nested.lookup, sub_value, context)
                if sub_ids:
                    fields[field_name] = sub_ids

        return fields

    def _get_repo(self, table_id: str) -> BaseRepository:
        if table_id not in self._repo_cache:

            class _DynamicRepo(BaseRepository):
                pass

            _DynamicRepo.table_id = table_id
            self._repo_cache[table_id] = _DynamicRepo()
        return self._repo_cache[table_id]

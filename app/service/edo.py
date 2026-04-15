from __future__ import annotations

from typing import Any

from app.cache.constants import EdoMatchingCacheKey
from app.cache.factory import CacheFactory
from app.core.lark_bitable_value import extract_cell_text
from app.repository.empty_park import EmptyParkRepository
from app.repository.shipping_line import ShippingLineRepository
from app.service.llm_service.edo.schemas import EdoDictValues, EmptyParkDictEntry


class EdoService:
    """EDO 领域 Service：组合 Shipping Line / Empty Park Repository，提供带缓存的主数据查询。"""

    def __init__(
        self,
        cache_factory: CacheFactory | None = None,
        shipping_line_repo: ShippingLineRepository | None = None,
        empty_park_repo: EmptyParkRepository | None = None,
    ) -> None:
        self._cache_factory = cache_factory if cache_factory is not None else CacheFactory()
        self._shipping_line_repo = shipping_line_repo or ShippingLineRepository()
        self._empty_park_repo = empty_park_repo or EmptyParkRepository()

    @property
    def cache_factory(self) -> CacheFactory:
        return self._cache_factory

    async def list_shipping_lines_for_matching(self) -> list[dict[str, Any]]:
        c = self._cache_factory
        key = EdoMatchingCacheKey.SHIPPING_LINES
        cached = c.get(key)
        if cached is None:
            records = await self._shipping_line_repo.list_all_records(
                field_names=["Shipping Line", "Shiiping Line Short Name"],
            )
            c.set(key, records)
            return records
        return cached

    async def list_empty_parks_for_matching(self) -> list[dict[str, Any]]:
        c = self._cache_factory
        key = EdoMatchingCacheKey.EMPTY_PARKS
        cached = c.get(key)
        if cached is None:
            records = await self._empty_park_repo.list_all_records(
                field_names=["Empty Park", "Facility Address", "Alias"],
            )
            c.set(key, records)
            return records
        return cached

    def clear_cache(self) -> None:
        self._cache_factory.clear()

    async def build_dict_values(self) -> EdoDictValues:
        sl_records = await self.list_shipping_lines_for_matching()
        ep_records = await self.list_empty_parks_for_matching()

        shipping_lines: list[str] = []
        for rec in sl_records:
            name = extract_cell_text(rec.get("Shipping Line", rec.get("shipping_line")))
            if name:
                shipping_lines.append(name.strip())

        empty_parks: list[EmptyParkDictEntry] = []
        for rec in ep_records:
            name = extract_cell_text(rec.get("Empty Park", rec.get("empty_park")))
            addr = extract_cell_text(rec.get("Facility Address", rec.get("facility_address")))
            alias_raw = extract_cell_text(rec.get("Alias", rec.get("alias")))
            aliases = [a.strip() for a in alias_raw.split(";") if a.strip()] if alias_raw else []
            if name:
                empty_parks.append(
                    EmptyParkDictEntry(
                        name=name.strip(),
                        address=addr.strip() if addr else None,
                        aliases=aliases,
                    )
                )

        return EdoDictValues(shipping_lines=shipping_lines, empty_parks=empty_parks)

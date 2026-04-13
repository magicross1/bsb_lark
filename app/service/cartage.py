from __future__ import annotations

from typing import Any

from app.cache.constants import CartageMatchingCacheKey
from app.cache.factory import CacheFactory
from app.repository.cartage import CartageRepository
from app.repository.consingee import ConsingeeRepository
from app.repository.warehouse_address import WarehouseAddressRepository
from app.repository.warehouse_deliver_config import WarehouseDeliverConfigRepository


class CartageService:
    """Cartage 领域 Service：只在此处组合多个 Repository。

    - :class:`CartageRepository` → Bitable「Op-Cartage」业务表（单表读写与其它 Repository 相同）。
    - 另三张 MD 表用于解析后地址/交付类型/收货人匹配时的批量读；
      缓存在 :class:`CacheFactory`，用 :class:`CartageMatchingCacheKey` 作为名字 ``get`` / ``set``。
    """

    def __init__(
        self,
        cache_factory: CacheFactory | None = None,
        op_cartage_repo: CartageRepository | None = None,
        warehouse_address_repo: WarehouseAddressRepository | None = None,
        warehouse_deliver_config_repo: WarehouseDeliverConfigRepository | None = None,
        consingee_repo: ConsingeeRepository | None = None,
    ) -> None:
        self._cache_factory = cache_factory if cache_factory is not None else CacheFactory()
        self._op_cartage_repo = op_cartage_repo or CartageRepository()
        self._warehouse_address_repo = warehouse_address_repo or WarehouseAddressRepository()
        self._warehouse_deliver_config_repo = warehouse_deliver_config_repo or WarehouseDeliverConfigRepository()
        self._consingee_repo = consingee_repo or ConsingeeRepository()

    @property
    def cache_factory(self) -> CacheFactory:
        return self._cache_factory

    @property
    def op_cartage(self) -> CartageRepository:
        """Op-Cartage 表数据访问（写入/查询业务单等）。"""
        return self._op_cartage_repo

    async def list_addresses_for_matching(self) -> list[dict[str, Any]]:
        c = self._cache_factory
        key = CartageMatchingCacheKey.ADDRESSES
        cached = c.get(key)
        if cached is None:
            records = await self._warehouse_address_repo.list_all_records(
                field_names=["Address"],
            )
            c.set(key, records)
            return records
        return cached

    async def list_deliver_configs_for_matching(self) -> list[dict[str, Any]]:
        c = self._cache_factory
        key = CartageMatchingCacheKey.DELIVER_CONFIGS
        cached = c.get(key)
        if cached is None:
            records = await self._warehouse_deliver_config_repo.list_all_records(
                field_names=["Deliver Config", "Deliver Type", "Warehouse Address"],
            )
            c.set(key, records)
            return records
        return cached

    async def list_consingees_for_matching(self) -> list[dict[str, Any]]:
        c = self._cache_factory
        key = CartageMatchingCacheKey.CONSINGEES
        cached = c.get(key)
        if cached is None:
            records = await self._consingee_repo.list_all_records(
                field_names=["Name", "MD-Warehouse Address"],
            )
            c.set(key, records)
            return records
        return cached

    def clear_cache(self) -> None:
        self._cache_factory.clear()

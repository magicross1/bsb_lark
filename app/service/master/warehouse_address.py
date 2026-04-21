from __future__ import annotations

from app.common.update_wrapper import UpdateWrapper
from app.common.query_wrapper import QueryWrapper

from typing import Any

from app.core.base_service import BaseService
from app.repository.warehouse_address import WarehouseAddressRepository


class WarehouseAddressService(BaseService):
    def __init__(self, repository: WarehouseAddressRepository | None = None) -> None:
        super().__init__(repository or WarehouseAddressRepository())

    async def list_warehouse_addresses(self, *, page_size: int = 100, page_token: str | None = None) -> tuple[list[dict[str, Any]], str | None]:
        return await self.repository.page(page_size=page_size, page_token=page_token)

    async def list_all_warehouse_addresses(self) -> list[dict[str, Any]]:
        return await self.repository.list()

    async def get_warehouse_address(self, record_id: str) -> dict[str, Any]:
        return await self.repository.findOne(QueryWrapper().eq("record_id", record_id))

    async def create_warehouse_address(self, fields: dict[str, Any]) -> dict[str, Any]:
        return await self.repository.createOne(fields)

    async def update_warehouse_address(self, record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        return await self.repository.updateOne(UpdateWrapper().eq("record_id", record_id).set_all(fields))

    async def delete_warehouse_address(self, record_id: str) -> None:
        await self.repository.deleteOne(QueryWrapper().eq("record_id", record_id))


warehouse_address_service = WarehouseAddressService()

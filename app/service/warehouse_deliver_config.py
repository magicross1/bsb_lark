from __future__ import annotations

from typing import Any

from app.core.base_service import BaseService
from app.repository.warehouse_deliver_config import WarehouseDeliverConfigRepository


class WarehouseDeliverConfigService(BaseService):
    def __init__(self, repository: WarehouseDeliverConfigRepository) -> None:
        super().__init__(repository)

    async def list_warehouse_deliver_configs(self, **kwargs: Any) -> tuple[list[dict[str, Any]], str | None]:
        return await self.repository.list_records(**kwargs)

    async def list_all_warehouse_deliver_configs(self, **kwargs: Any) -> list[dict[str, Any]]:
        return await self.repository.list_all_records(**kwargs)

    async def get_warehouse_deliver_config(self, record_id: str) -> dict[str, Any]:
        return await self.repository.get_record(record_id)

    async def create_warehouse_deliver_config(self, fields: dict[str, Any]) -> dict[str, Any]:
        return await self.repository.create_record(fields)

    async def update_warehouse_deliver_config(self, record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        return await self.repository.update_record(record_id, fields)

    async def delete_warehouse_deliver_config(self, record_id: str) -> None:
        await self.repository.delete_record(record_id)

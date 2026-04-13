from __future__ import annotations

from typing import Any

from app.core.base_service import BaseService
from app.repository.driver import DriverRepository


class DriverService(BaseService):
    def __init__(self, repository: DriverRepository | None = None) -> None:
        super().__init__(repository or DriverRepository())

    async def list_drivers(self, **kwargs: Any) -> tuple[list[dict[str, Any]], str | None]:
        return await self.repository.list_records(**kwargs)

    async def list_all_drivers(self, **kwargs: Any) -> list[dict[str, Any]]:
        return await self.repository.list_all_records(**kwargs)

    async def create_driver(self, fields: dict[str, Any]) -> dict[str, Any]:
        return await self.repository.create_record(fields)

    async def update_driver(self, record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        return await self.repository.update_record(record_id, fields)

    async def delete_driver(self, record_id: str) -> None:
        await self.repository.delete_record(record_id)


driver_service = DriverService()

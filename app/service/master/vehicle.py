from __future__ import annotations

from typing import Any

from app.core.base_service import BaseService
from app.repository.vehicle import VehicleRepository


class VehicleService(BaseService):
    def __init__(self, repository: VehicleRepository | None = None) -> None:
        super().__init__(repository or VehicleRepository())

    async def list_vehicles(self, **kwargs: Any) -> tuple[list[dict[str, Any]], str | None]:
        return await self.repository.list_records(**kwargs)

    async def list_all_vehicles(self, **kwargs: Any) -> list[dict[str, Any]]:
        return await self.repository.list_all_records(**kwargs)

    async def create_vehicle(self, fields: dict[str, Any]) -> dict[str, Any]:
        return await self.repository.create_record(fields)

    async def update_vehicle(self, record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        return await self.repository.update_record(record_id, fields)

    async def delete_vehicle(self, record_id: str) -> None:
        await self.repository.delete_record(record_id)


vehicle_service = VehicleService()

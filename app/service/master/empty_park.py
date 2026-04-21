from __future__ import annotations

from typing import Any

from app.core.base_service import BaseService
from app.repository.empty_park import EmptyParkRepository


class EmptyParkService(BaseService):
    def __init__(self, repository: EmptyParkRepository | None = None) -> None:
        super().__init__(repository or EmptyParkRepository())

    async def list_empty_parks(self, **kwargs: Any) -> tuple[list[dict[str, Any]], str | None]:
        return await self.repository.list_records(**kwargs)

    async def list_all_empty_parks(self, **kwargs: Any) -> list[dict[str, Any]]:
        return await self.repository.list_all_records(**kwargs)

    async def create_empty_park(self, fields: dict[str, Any]) -> dict[str, Any]:
        return await self.repository.create_record(fields)

    async def update_empty_park(self, record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        return await self.repository.update_record(record_id, fields)

    async def delete_empty_park(self, record_id: str) -> None:
        await self.repository.delete_record(record_id)


empty_park_service = EmptyParkService()

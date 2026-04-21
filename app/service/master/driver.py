from __future__ import annotations

from app.common.update_wrapper import UpdateWrapper
from app.common.query_wrapper import QueryWrapper

from typing import Any

from app.core.base_service import BaseService
from app.repository.driver import DriverRepository


class DriverService(BaseService):
    def __init__(self, repository: DriverRepository | None = None) -> None:
        super().__init__(repository or DriverRepository())

    async def list_drivers(self, *, page_size: int = 100, page_token: str | None = None) -> tuple[list[dict[str, Any]], str | None]:
        return await self.repository.page(page_size=page_size, page_token=page_token)

    async def list_all_drivers(self) -> list[dict[str, Any]]:
        return await self.repository.list()

    async def create_driver(self, fields: dict[str, Any]) -> dict[str, Any]:
        return await self.repository.createOne(fields)

    async def update_driver(self, record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        return await self.repository.updateOne(UpdateWrapper().eq("record_id", record_id).set_all(fields))

    async def delete_driver(self, record_id: str) -> None:
        await self.repository.deleteOne(QueryWrapper().eq("record_id", record_id))


driver_service = DriverService()

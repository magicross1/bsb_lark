from __future__ import annotations

from typing import Any

from app.core.base_service import BaseService
from app.repository.freight_forwarder import FreightForwarderRepository


class FreightForwarderService(BaseService):
    def __init__(self, repository: FreightForwarderRepository | None = None) -> None:
        super().__init__(repository or FreightForwarderRepository())

    async def list_freight_forwarders(self, **kwargs: Any) -> tuple[list[dict[str, Any]], str | None]:
        return await self.repository.list_records(**kwargs)

    async def list_all_freight_forwarders(self, **kwargs: Any) -> list[dict[str, Any]]:
        return await self.repository.list_all_records(**kwargs)

    async def create_freight_forwarder(self, fields: dict[str, Any]) -> dict[str, Any]:
        return await self.repository.create_record(fields)

    async def update_freight_forwarder(self, record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        return await self.repository.update_record(record_id, fields)

    async def delete_freight_forwarder(self, record_id: str) -> None:
        await self.repository.delete_record(record_id)


freight_forwarder_service = FreightForwarderService()

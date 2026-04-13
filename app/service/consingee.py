from __future__ import annotations

from typing import Any

from app.core.base_service import BaseService
from app.repository.consingee import ConsingeeRepository


class ConsingeeService(BaseService):
    def __init__(self, repository: ConsingeeRepository | None = None) -> None:
        super().__init__(repository or ConsingeeRepository())

    async def list_consingees(self, **kwargs: Any) -> tuple[list[dict[str, Any]], str | None]:
        return await self.repository.list_records(**kwargs)

    async def list_all_consingees(self, **kwargs: Any) -> list[dict[str, Any]]:
        return await self.repository.list_all_records(**kwargs)

    async def get_consingee(self, record_id: str) -> dict[str, Any]:
        return await self.repository.get_record(record_id)

    async def create_consingee(self, fields: dict[str, Any]) -> dict[str, Any]:
        return await self.repository.create_record(fields)

    async def update_consingee(self, record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        return await self.repository.update_record(record_id, fields)

    async def delete_consingee(self, record_id: str) -> None:
        await self.repository.delete_record(record_id)


consingee_service = ConsingeeService()

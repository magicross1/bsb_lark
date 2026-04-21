from __future__ import annotations

from typing import Any

from app.core.base_service import BaseService
from app.repository.terminal import TerminalRepository


class TerminalService(BaseService):
    def __init__(self, repository: TerminalRepository | None = None) -> None:
        super().__init__(repository or TerminalRepository())

    async def list_terminals(self, **kwargs: Any) -> tuple[list[dict[str, Any]], str | None]:
        return await self.repository.list_records(**kwargs)

    async def list_all_terminals(self, **kwargs: Any) -> list[dict[str, Any]]:
        return await self.repository.list_all_records(**kwargs)

    async def create_terminal(self, fields: dict[str, Any]) -> dict[str, Any]:
        return await self.repository.create_record(fields)

    async def update_terminal(self, record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        return await self.repository.update_record(record_id, fields)

    async def delete_terminal(self, record_id: str) -> None:
        await self.repository.delete_record(record_id)


terminal_service = TerminalService()

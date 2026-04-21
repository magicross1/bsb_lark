from __future__ import annotations

from typing import Any

from app.core.base_service import BaseService
from app.repository.distance_matrix import DistanceMatrixRepository


class DistanceMatrixService(BaseService):
    def __init__(self, repository: DistanceMatrixRepository | None = None) -> None:
        super().__init__(repository or DistanceMatrixRepository())

    async def list_distance_matrix(self, **kwargs: Any) -> tuple[list[dict[str, Any]], str | None]:
        return await self.repository.list_records(**kwargs)

    async def list_all_distance_matrix(self, **kwargs: Any) -> list[dict[str, Any]]:
        return await self.repository.list_all_records(**kwargs)

    async def create_distance_matrix(self, fields: dict[str, Any]) -> dict[str, Any]:
        return await self.repository.create_record(fields)

    async def update_distance_matrix(self, record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        return await self.repository.update_record(record_id, fields)

    async def delete_distance_matrix(self, record_id: str) -> None:
        await self.repository.delete_record(record_id)


distance_matrix_service = DistanceMatrixService()

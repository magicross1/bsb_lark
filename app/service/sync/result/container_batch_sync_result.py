from __future__ import annotations

from pydantic import BaseModel

from app.service.sync.result.container_sync_result import ContainerSyncResult


class ContainerBatchSyncResult(BaseModel):
    total: int = 0
    synced: int = 0
    errors: int = 0
    details: list[ContainerSyncResult] = []

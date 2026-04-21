from __future__ import annotations

from pydantic import BaseModel

from app.service.sync.result.clear_sync_result import ClearSyncResult


class ClearBatchSyncResult(BaseModel):
    total: int = 0
    synced: int = 0
    errors: int = 0
    details: list[ClearSyncResult] = []

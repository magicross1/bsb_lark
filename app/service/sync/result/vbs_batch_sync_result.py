from __future__ import annotations

from pydantic import BaseModel

from app.service.sync.result.vbs_sync_result import VbsSyncResult


class VbsBatchSyncResult(BaseModel):
    total: int = 0
    synced: int = 0
    errors: int = 0
    details: list[VbsSyncResult] = []

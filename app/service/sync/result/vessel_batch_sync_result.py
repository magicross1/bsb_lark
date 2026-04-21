from __future__ import annotations

from pydantic import BaseModel

from app.service.sync.result.vessel_sync_result import VesselSyncResult


class VesselBatchSyncResult(BaseModel):
    total: int = 0
    synced: int = 0
    errors: int = 0
    details: list[VesselSyncResult] = []

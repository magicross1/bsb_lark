from __future__ import annotations

from pydantic import BaseModel


class VesselSyncResult(BaseModel):
    record_id: str
    updated_fields: list[str] = []
    error: str | None = None
    raw: dict | None = None

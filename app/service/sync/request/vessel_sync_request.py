from __future__ import annotations

from pydantic import BaseModel


class VesselSyncRequest(BaseModel):
    record_id: str  # Op-Vessel Schedule record_id

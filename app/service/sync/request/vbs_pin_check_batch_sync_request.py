from __future__ import annotations

from pydantic import BaseModel, Field


class VbsPinCheckBatchSyncRequest(BaseModel):
    condition: str = Field(default="pending")

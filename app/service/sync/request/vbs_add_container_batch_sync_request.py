from __future__ import annotations

from pydantic import BaseModel, Field


class VbsAddContainerBatchSyncRequest(BaseModel):
    condition: str = Field(default="pending")

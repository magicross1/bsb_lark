from __future__ import annotations

from pydantic import BaseModel, Field


class EdoWritebackEntryRef(BaseModel):
    record_id: str
    container_number: str
    status: str


class EdoWritebackResult(BaseModel):
    updated: list[EdoWritebackEntryRef] = Field(default_factory=list)
    skipped: list[EdoWritebackEntryRef] = Field(default_factory=list)

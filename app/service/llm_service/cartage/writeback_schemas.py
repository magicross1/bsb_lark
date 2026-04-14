from __future__ import annotations

from pydantic import BaseModel, Field


class WritebackRecordRef(BaseModel):
    record_id: str
    table_name: str


class SkippedContainer(BaseModel):
    container_number: str
    reason: str
    existing_record_id: str | None = None


class CartageWritebackResult(BaseModel):
    cartage_refs: list[WritebackRecordRef] = Field(default_factory=list)
    imports: list[WritebackRecordRef] = Field(default_factory=list)
    exports: list[WritebackRecordRef] = Field(default_factory=list)
    skipped: list[SkippedContainer] = Field(default_factory=list)

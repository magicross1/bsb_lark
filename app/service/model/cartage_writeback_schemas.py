from __future__ import annotations

from pydantic import BaseModel, Field


class WritebackRecordRef(BaseModel):
    """写回操作创建或更新的记录引用。"""

    record_id: str
    table_name: str


class SkippedContainer(BaseModel):
    """写回时跳过的箱号及原因。"""

    container_number: str
    reason: str
    existing_record_id: str | None = None


class CartageWritebackResult(BaseModel):
    """Cartage 写回结果汇总。"""

    cartage_refs: list[WritebackRecordRef] = Field(default_factory=list)
    imports: list[WritebackRecordRef] = Field(default_factory=list)
    exports: list[WritebackRecordRef] = Field(default_factory=list)
    skipped: list[SkippedContainer] = Field(default_factory=list)

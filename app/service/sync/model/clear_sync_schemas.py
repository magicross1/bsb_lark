from __future__ import annotations

from pydantic import BaseModel, Field


class ClearSyncRequest(BaseModel):
    container_numbers: list[str] = Field(
        description="柜号列表",
    )
    terminal_full_name: str | None = Field(
        default=None,
        description="Op-Import 中的 Terminal Full Name 字段值，用于选择 Provider",
    )


class ClearBatchSyncRequest(BaseModel):
    condition: str = Field(
        default="pending",
        description=(
            "批量查询条件名称。内置条件: "
            "pending = Terminal Full Name 不为空且 Clear Status 未完结; "
            "all = 全部记录"
        ),
    )


class ClearSyncResult(BaseModel):
    container_number: str
    provider: str | None = None
    updated_fields: list[str] = []
    error: str | None = None
    raw: dict | None = None


class ClearBatchSyncResult(BaseModel):
    total: int = 0
    synced: int = 0
    errors: int = 0
    details: list[ClearSyncResult] = []

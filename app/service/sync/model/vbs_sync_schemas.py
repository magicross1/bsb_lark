from __future__ import annotations

from pydantic import BaseModel, Field


class VbsSyncRequest(BaseModel):
    container_numbers: list[str] = Field(description="柜号列表")
    terminal_full_name: str | None = Field(
        default=None,
        description="Op-Import 中的 Terminal Full Name，用于路由 VBS operation",
    )


class VbsBatchSyncRequest(BaseModel):
    condition: str = Field(
        default="pending",
        description=(
            "批量查询条件名称。内置条件: "
            "pending = GATEOUT_Time 为空且 Terminal 可路由; "
            "all = 全部可路由记录"
        ),
    )


class VbsSyncResult(BaseModel):
    container_number: str
    operation: str | None = None
    updated_fields: list[str] = []
    error: str | None = None


class VbsBatchSyncResult(BaseModel):
    total: int = 0
    synced: int = 0
    errors: int = 0
    details: list[VbsSyncResult] = []

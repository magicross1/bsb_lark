from __future__ import annotations

from pydantic import BaseModel, Field


class ContainerSyncRequest(BaseModel):
    container_numbers: list[str] = Field(
        description="柜号列表，支持单个或多个",
    )


class ContainerBatchSyncRequest(BaseModel):
    condition: str = Field(
        default="basic",
        description=(
            "批量查询条件名称。内置条件: "
            "basic = VesselIn/InVoyage/PortOfDischarge 任一为空; "
            "terminal = 码头或 ETA 为空; "
            "vessel_schedule = ImportAvailability 或 StorageStartDate 为空; "
            "discharge = ETA 已过但未卸船; "
            "gateout = 已卸船但未提柜; "
            "all = 全部记录"
        ),
    )


class ContainerSyncResult(BaseModel):
    container_number: str
    updated_fields: list[str] = []
    error: str | None = None
    raw: dict | None = None


class ContainerBatchSyncResult(BaseModel):
    total: int = 0
    synced: int = 0
    errors: int = 0
    details: list[ContainerSyncResult] = []

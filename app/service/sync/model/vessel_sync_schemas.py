from __future__ import annotations

from pydantic import BaseModel, Field


class VesselSyncRequest(BaseModel):
    record_id: str = Field(description="Op-Vessel Schedule record_id")


class VesselBatchSyncRequest(BaseModel):
    """船期批量同步请求体"""

    condition: str = Field(
        default="pending_arrival",
        description=(
            "批量查询条件名称。内置条件: "
            "pending_arrival = Actual Arrival 不为 Y/SP; "
            "missing_eta = ETA 为空; "
            "all = 全部记录"
        ),
    )
    base_node: str | None = Field(
        default=None,
        description="可选：按 Base Node 过滤，如 PORT OF SYDNEY",
    )


class VesselSyncResult(BaseModel):
    """单条同步结果"""

    record_id: str
    updated_fields: list[str] = []
    error: str | None = None
    raw: dict | None = None


class VesselBatchSyncResult(BaseModel):
    """批量同步结果"""

    total: int = 0
    synced: int = 0
    errors: int = 0
    details: list[VesselSyncResult] = []

from __future__ import annotations

from pydantic import BaseModel, Field


class ContainerBatchSyncRequest(BaseModel):
    # 可用条件:
    # basic           — VesselIn/InVoyage/PortOfDischarge 任一为空
    # terminal        — 码头或 ETA 为空
    # vessel_schedule — ImportAvailability 或 StorageStartDate 为空
    # discharge       — ETA 已过但未卸船
    # gateout         — 已卸船但未提柜
    # all             — 全部记录
    condition: str = Field(default="basic")

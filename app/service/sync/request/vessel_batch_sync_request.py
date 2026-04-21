from __future__ import annotations

from pydantic import BaseModel, Field


class VesselBatchSyncRequest(BaseModel):
    # 可用条件:
    # pending_arrival — Actual Arrival 不为 Y/SP（含空值）
    # missing_eta     — ETA 为空
    # all             — 全部记录
    condition: str = Field(default="pending_arrival")
    # 可选：按 Base Node 过滤，如 PORT OF SYDNEY
    base_node: str | None = None

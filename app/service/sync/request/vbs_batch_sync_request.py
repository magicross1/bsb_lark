from __future__ import annotations

from pydantic import BaseModel, Field


class VbsBatchSyncRequest(BaseModel):
    # 可用条件:
    # pending — GATEOUT_Time 为空且 Terminal 可路由到 VBS
    # all     — 全部可路由到 VBS 的记录
    condition: str = Field(default="pending")

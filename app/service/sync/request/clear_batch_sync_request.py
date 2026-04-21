from __future__ import annotations

from pydantic import BaseModel, Field


class ClearBatchSyncRequest(BaseModel):
    # 可用条件:
    # pending — Terminal 不为空且 Clear Status 未完结（非 CLEAR/UNDERBOND APPROVAL/RELEASED，含空值）
    # all     — 全部记录
    condition: str = Field(default="pending")

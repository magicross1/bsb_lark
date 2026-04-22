from __future__ import annotations

from pydantic import BaseModel


class BatchSyncResult(BaseModel):
    """同步结果（通用，所有场景共用）。"""

    total: int = 0
    synced: int = 0
    errors: int = 0

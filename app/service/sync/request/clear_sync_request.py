from __future__ import annotations

from pydantic import BaseModel


class ClearSyncRequest(BaseModel):
    container_numbers: list[str]
    # 用于选择 Provider，为空时自动路由
    terminal_full_name: str | None = None

from __future__ import annotations

from pydantic import BaseModel


class VbsSyncRequest(BaseModel):
    container_numbers: list[str]
    # 用于路由 VBS operation，为空时无法路由
    terminal_full_name: str | None = None

from __future__ import annotations

from pydantic import BaseModel


class VbsAddContainerSyncRequest(BaseModel):
    container_number: str
    terminal_full_name: str

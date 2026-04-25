from __future__ import annotations

from pydantic import BaseModel


class VbsPinCheckSyncRequest(BaseModel):
    container_number: str
    terminal_full_name: str

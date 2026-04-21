from __future__ import annotations

from pydantic import BaseModel


class ContainerSyncRequest(BaseModel):
    container_numbers: list[str]

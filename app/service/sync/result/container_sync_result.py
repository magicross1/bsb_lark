from __future__ import annotations

from pydantic import BaseModel


class ContainerSyncResult(BaseModel):
    container_number: str
    updated_fields: list[str] = []
    error: str | None = None
    raw: dict | None = None

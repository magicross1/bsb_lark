from __future__ import annotations

from pydantic import BaseModel


class ClearSyncResult(BaseModel):
    container_number: str
    provider: str | None = None
    updated_fields: list[str] = []
    error: str | None = None
    raw: dict | None = None

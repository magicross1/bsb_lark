from __future__ import annotations

from pydantic import BaseModel


class VbsSyncResult(BaseModel):
    container_number: str
    operation: str | None = None
    updated_fields: list[str] = []
    error: str | None = None

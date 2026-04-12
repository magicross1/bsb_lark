from __future__ import annotations

from pydantic import BaseModel


class EdoEntry(BaseModel):
    container_number: str
    edo_pin: str | None = None
    shipping_line: str | None = None
    empty_park: str | None = None


class EdoParseResult(BaseModel):
    entries: list[EdoEntry]
    raw_response: str | None = None

from __future__ import annotations

from pydantic import BaseModel, Field


class EdoEntry(BaseModel):
    container_number: str
    edo_pin: str | None = None
    shipping_line: str | None = None
    empty_park: str | None = None
    empty_park_address: str | None = None


class EmptyParkDictEntry(BaseModel):
    name: str
    address: str | None = None
    aliases: list[str] = Field(default_factory=list)


class EdoDictValues(BaseModel):
    shipping_lines: list[str] = Field(
        default_factory=lambda: [
            "COSCO",
            "OOCL",
            "MSC",
            "ANL",
            "HMM",
            "TS LINES",
            "Hapag Lioyd",
            "Evergreen Line",
            "YANG MING",
            "PIL",
            "Maersk",
            "Hamburg Sud",
            "ZIM",
            "ONE",
            "Nautical",
            "SWIRE",
            "BAL",
            "QUAY",
            "OTHER",
        ]
    )
    empty_parks: list[EmptyParkDictEntry] = Field(default_factory=list)


class EdoParseResult(BaseModel):
    entries: list[EdoEntry]
    raw_response: str | None = None


class ShippingLineMatch(BaseModel):
    record_id: str
    name: str


class EmptyParkMatch(BaseModel):
    record_id: str
    name: str
    address: str | None = None


class EdoEntryMatch(EdoEntry):
    shipping_line_match: ShippingLineMatch | None = None
    empty_park_match: EmptyParkMatch | None = None


class EdoProcessResult(BaseModel):
    entries: list[EdoEntryMatch] = Field(default_factory=list)
    raw_response: str | None = None

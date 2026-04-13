from __future__ import annotations

from pydantic import BaseModel, Field


class ImportContainerEntry(BaseModel):
    container_number: str
    vessel_name: str | None = None
    voyage: str | None = None
    base_node: str | None = None
    container_type: str | None = None
    commodity: str | None = None
    container_weight: float | None = None


class ExportBookingEntry(BaseModel):
    booking_reference: str | None = None
    release_qty: int = 1
    vessel_name: str | None = None
    voyage: str | None = None
    base_node: str | None = None
    container_type: str | None = None
    commodity: str | None = None
    shipping_line: str | None = None
    container_number: str | None = None


class CartageDictValues(BaseModel):
    base_nodes: list[str] = Field(
        default_factory=lambda: [
            "PORT OF SYDNEY",
            "PORT OF MELBOURNE",
            "PORT OF BRISBANE",
            "PORT OF FREMANTLE",
            "PORT OF ADELAIDE",
        ]
    )
    container_types: list[str] = Field(
        default_factory=lambda: [
            "20GP",
            "20HC",
            "20RE",
            "20OT",
            "40GP",
            "40HC",
            "40RE",
            "40OT",
        ]
    )
    commodities: list[str] = Field(
        default_factory=lambda: [
            "GEN",
            "HAZ",
            "REE",
            "OOG",
            "EMPTY",
        ]
    )
    shipping_lines: list[str] = Field(
        default_factory=lambda: [
            "COSCO",
            "MAERSK",
            "ONE",
            "HAPAG-LLOYD",
            "OOCL",
            "EVERGREEN",
            "YANG MING",
            "PIL",
            "MSC",
            "CMA CGM",
            "ZIM",
        ]
    )
    deliver_types: list[str] = Field(
        default_factory=lambda: [
            "Sideloader(SDL)",
            "Drop Trailer(DROP)",
            "Standard Trailer(STD)",
        ]
    )


class CartageParseResult(BaseModel):
    booking_reference: str | None = None
    direction: str | None = None
    consingee_name: str | None = None
    deliver_address: str | None = None
    deliver_type: str | None = None
    deliver_type_raw: str | None = None
    import_containers: list[ImportContainerEntry] = Field(default_factory=list)
    export_bookings: list[ExportBookingEntry] = Field(default_factory=list)
    raw_response: str | None = None

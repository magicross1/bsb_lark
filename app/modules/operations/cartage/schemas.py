from __future__ import annotations

from pydantic import BaseModel


class CartageContainerEntry(BaseModel):
    container_number: str
    container_type: str | None = None
    container_weight: float | None = None
    commodity: str | None = None


class CartageParseResult(BaseModel):
    booking_reference: str | None = None
    direction: str | None = None
    consingee_name: str | None = None
    deliver_address: str | None = None
    deliver_type_raw: str | None = None
    vessel_name: str | None = None
    voyage: str | None = None
    port_of_discharge: str | None = None
    containers: list[CartageContainerEntry] = []
    raw_response: str | None = None

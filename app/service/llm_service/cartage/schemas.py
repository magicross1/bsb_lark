from __future__ import annotations

from pydantic import BaseModel, Field

# Cartage 大模型解析阶段的数据模型（不含主数据匹配后的字段）。


class CartageContainerEntry(BaseModel):
    container_number: str
    container_type: str | None = None
    container_weight: float | None = None
    commodity: str | None = None


class ImportContainerMatch(BaseModel):
    """进口方向集装箱（解析阶段与主数据匹配前）。"""

    container_number: str
    container_type: str | None = None
    container_weight: float | None = None
    commodity: str | None = None


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
    """解析时可选注入的上下文（例如已知交付类型）。"""

    deliver_type: str | None = None


class CartageParseResult(BaseModel):
    """单次 LLM 解析的完整结果。"""

    booking_reference: str | None = None
    direction: str | None = None
    consingee_name: str | None = None
    deliver_address: str | None = None
    deliver_type: str | None = None
    deliver_type_raw: str | None = None
    vessel_name: str | None = None
    voyage: str | None = None
    port_of_discharge: str | None = None
    containers: list[CartageContainerEntry] = Field(default_factory=list)
    import_containers: list[ImportContainerMatch] = Field(default_factory=list)
    export_bookings: list[ExportBookingEntry] = Field(default_factory=list)
    raw_response: str | None = None

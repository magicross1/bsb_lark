from __future__ import annotations

from pydantic import BaseModel, Field

from app.service.llm_service.cartage.schemas import ExportBookingEntry, ImportContainerMatch

# 主数据富化之后对外暴露的 Cartage 结果模型（依赖 schemas 中的解析类型）。


class ExportBookingMatch(ExportBookingEntry):
    """出口订舱行（与 :class:`ExportBookingEntry` 字段一致，用于 process 输出）。"""


class AddressMatch(BaseModel):
    record_id: str
    address: str
    score: float
    deliver_config_id: str | None = None
    deliver_config: str | None = None
    consingee_id: str | None = None
    consingee_name: str | None = None


class CartageProcessResult(BaseModel):
    booking_reference: str | None = None
    direction: str | None = None
    consingee_name: str | None = None
    deliver_address: str | None = None
    deliver_type: str | None = None
    deliver_type_raw: str | None = None
    address_match: AddressMatch | None = None
    address_needs_review: bool = False
    import_containers: list[ImportContainerMatch] = Field(default_factory=list)
    export_bookings: list[ExportBookingMatch] = Field(default_factory=list)
    raw_response: str | None = None

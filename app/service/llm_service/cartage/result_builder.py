from __future__ import annotations

from typing import Any

from app.core.base_parser import extract_json_from_response
from app.service.llm_service.cartage.schemas import (
    CartageContainerEntry,
    CartageDictValues,
    CartageParseResult,
    ExportBookingEntry,
    ImportContainerMatch,
)


def build_cartage_parse_result(
    raw_llm_response: str,
    *,
    dict_values: CartageDictValues | None = None,
) -> CartageParseResult:
    """将模型原始输出中的 JSON 转为 :class:`CartageParseResult`（无 HTTP / 无智谱客户端）。"""
    data = extract_json_from_response(raw_llm_response)
    if data is None:
        return CartageParseResult(raw_response=raw_llm_response)

    containers = _containers_from_payload(data.get("containers", []))
    direction_raw = data.get("direction")
    direction_key = (direction_raw or "").strip().lower()
    deliver_type = dict_values.deliver_type if dict_values else None

    import_containers: list[ImportContainerMatch] = []
    export_bookings: list[ExportBookingEntry] = []
    if direction_key == "export":
        for c in containers:
            export_bookings.append(
                ExportBookingEntry(
                    booking_reference=data.get("booking_reference"),
                    release_qty=1,
                    vessel_name=data.get("vessel_name"),
                    voyage=data.get("voyage"),
                    base_node=data.get("port_of_discharge"),
                    container_type=c.container_type,
                    commodity=c.commodity,
                    shipping_line=None,
                    container_number=c.container_number,
                )
            )
    else:
        import_containers = [ImportContainerMatch(**c.model_dump()) for c in containers]

    return CartageParseResult(
        booking_reference=data.get("booking_reference"),
        direction=direction_raw,
        consingee_name=data.get("consingee_name"),
        deliver_address=data.get("deliver_address"),
        deliver_type=deliver_type,
        deliver_type_raw=data.get("deliver_type_raw"),
        vessel_name=data.get("vessel_name"),
        voyage=data.get("voyage"),
        port_of_discharge=data.get("port_of_discharge"),
        containers=containers,
        import_containers=import_containers,
        export_bookings=export_bookings,
        raw_response=raw_llm_response,
    )


def _containers_from_payload(items: list[Any]) -> list[CartageContainerEntry]:
    containers: list[CartageContainerEntry] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        cn = item.get("container_number", "")
        if cn:
            containers.append(
                CartageContainerEntry(
                    container_number=cn,
                    container_type=item.get("container_type"),
                    container_weight=item.get("container_weight"),
                    commodity=item.get("commodity"),
                )
            )
    return containers

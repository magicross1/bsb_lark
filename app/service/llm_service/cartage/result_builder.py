from __future__ import annotations

import logging

from app.core.base_parser import extract_json_from_response
from app.service.llm_service.cartage.schemas import (
    CartageDictValues,
    CartageParseResult,
    ExportBookingEntry,
    ImportContainerEntry,
)

_logger = logging.getLogger(__name__)


def _validate_choice(value: str | None, valid: list[str]) -> str | None:
    if value is None:
        return None
    if value in valid:
        return value
    lower_map = {v.lower(): v for v in valid}
    matched = lower_map.get(value.lower())
    if matched:
        return matched
    for v in valid:
        if f"({value})" in v:
            return v
    _logger.warning("AI returned unrecognized value %r not in %s", value, valid[:5])
    return None


def build_cartage_parse_result(
    raw_llm_response: str,
    *,
    dict_values: CartageDictValues | None = None,
) -> CartageParseResult:
    data = extract_json_from_response(raw_llm_response)
    if data is None:
        return CartageParseResult(raw_response=raw_llm_response)

    dv = dict_values or CartageDictValues()
    deliver_type = _validate_choice(data.get("deliver_type"), dv.deliver_types)
    direction_key = (data.get("direction") or "").strip().lower()

    import_containers: list[ImportContainerEntry] = []
    export_bookings: list[ExportBookingEntry] = []

    if direction_key == "export":
        for item in data.get("export_bookings", []):
            ref = item.get("booking_reference", "")
            cn = item.get("container_number", "")
            if ref or cn:
                export_bookings.append(
                    ExportBookingEntry(
                        booking_reference=ref or None,
                        release_qty=item.get("release_qty", 1),
                        vessel_name=item.get("vessel_name"),
                        voyage=item.get("voyage"),
                        base_node=_validate_choice(item.get("base_node"), dv.base_nodes),
                        container_type=_validate_choice(item.get("container_type"), dv.container_types),
                        commodity=_validate_choice(item.get("commodity"), dv.commodities),
                        shipping_line=_validate_choice(item.get("shipping_line"), dv.shipping_lines),
                        container_number=cn or None,
                    )
                )
    else:
        for item in data.get("import_containers", []):
            cn = item.get("container_number", "")
            if cn:
                import_containers.append(
                    ImportContainerEntry(
                        container_number=cn,
                        vessel_name=item.get("vessel_name"),
                        voyage=item.get("voyage"),
                        base_node=_validate_choice(item.get("base_node"), dv.base_nodes),
                        container_type=_validate_choice(item.get("container_type"), dv.container_types),
                        commodity=_validate_choice(item.get("commodity"), dv.commodities),
                        container_weight=item.get("container_weight"),
                        shipping_line=_validate_choice(item.get("shipping_line"), dv.shipping_lines),
                    )
                )

    return CartageParseResult(
        booking_reference=data.get("booking_reference"),
        direction=data.get("direction"),
        consingee_name=data.get("consingee_name"),
        deliver_address=data.get("deliver_address"),
        deliver_type=deliver_type,
        deliver_type_raw=data.get("deliver_type_raw"),
        import_containers=import_containers,
        export_bookings=export_bookings,
        raw_response=raw_llm_response,
    )

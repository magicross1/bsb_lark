from __future__ import annotations

from app.service.llm_service.cartage.schemas import ExportBookingEntry


def expand_export_bookings(bookings: list[ExportBookingEntry]) -> list[ExportBookingEntry]:
    """按 release_qty 将出口订舱行拆成多行（每行 qty=1）。"""
    expanded: list[ExportBookingEntry] = []
    for booking in bookings:
        qty = max(booking.release_qty, 1)
        if qty == 1:
            expanded.append(booking)
            continue
        for i in range(1, qty + 1):
            suffix = f"-{i}" if booking.booking_reference else ""
            expanded.append(
                ExportBookingEntry(
                    booking_reference=f"{booking.booking_reference}{suffix}" if booking.booking_reference else None,
                    release_qty=1,
                    vessel_name=booking.vessel_name,
                    voyage=booking.voyage,
                    base_node=booking.base_node,
                    container_type=booking.container_type,
                    commodity=booking.commodity,
                    shipping_line=booking.shipping_line,
                    container_number=booking.container_number,
                )
            )
    return expanded

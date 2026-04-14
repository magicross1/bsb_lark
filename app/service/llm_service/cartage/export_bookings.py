from __future__ import annotations

from app.service.llm_service.cartage.schemas import ExportBookingEntry


def expand_export_bookings(bookings: list[ExportBookingEntry]) -> list[ExportBookingEntry]:
    """按 release_qty 将出口订舱行拆成多行。

    Booking Reference 和 Release Qty 保持原值不变，Container Number 加序号后缀。
    例: RSG20811, qty=2 → 两行: booking_ref=RSG20811, release_qty=2, container_number=RSG20811-1 / RSG20811-2
    """
    expanded: list[ExportBookingEntry] = []
    for booking in bookings:
        qty = max(booking.release_qty, 1)
        if qty == 1:
            expanded.append(booking)
            continue
        for i in range(1, qty + 1):
            base = booking.booking_reference or booking.container_number or ""
            cn = f"{base}-{i}" if base else None
            expanded.append(
                ExportBookingEntry(
                    booking_reference=booking.booking_reference,
                    release_qty=booking.release_qty,
                    vessel_name=booking.vessel_name,
                    voyage=booking.voyage,
                    base_node=booking.base_node,
                    container_type=booking.container_type,
                    commodity=booking.commodity,
                    shipping_line=booking.shipping_line,
                    container_number=cn,
                )
            )
    return expanded

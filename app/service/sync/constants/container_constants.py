from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.common.query_wrapper import QueryWrapper as BitableQuery


def _to_datetime(value: Any) -> datetime | None:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, tz=UTC)
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(value, fmt)
                return dt.replace(tzinfo=UTC)
            except (ValueError, OSError):
                continue
    return None


def _eta_passed(record: dict[str, Any]) -> bool:
    eta_val = record.get("EstimatedArrival")
    if not eta_val:
        return False
    eta = _to_datetime(eta_val)
    return eta is not None and eta < datetime.now(UTC)


# VesselIn/InVoyage/PortOfDischarge 任一为空
_CONDITIONS: dict[str, BitableQuery] = {
    "basic": (
        BitableQuery().client_only()
        .any_empty(["VesselIn", "InVoyage", "PortOfDischarge"])
    ),
    # 船舶信息完整，Terminal/ETA 任一为空
    "terminal": (
        BitableQuery().client_only()
        .not_empty("VesselIn")
        .not_empty("InVoyage")
        .not_empty("PortOfDischarge")
        .any_empty(["Terminal Full Name", "EstimatedArrival"])
    ),
    # 码头/ETA 已有，ImportAvailability/StorageStartDate 任一为空
    "vessel_schedule": (
        BitableQuery().client_only()
        .not_empty("VesselIn")
        .not_empty("InVoyage")
        .not_empty("PortOfDischarge")
        .not_empty("Terminal Full Name")
        .not_empty("EstimatedArrival")
        .any_empty(["ImportAvailability", "StorageStartDate"])
    ),
    # ETA 已过，DISCHARGE_Time 为空
    "discharge": (
        BitableQuery().client_only()
        .not_empty("VesselIn")
        .not_empty("InVoyage")
        .not_empty("PortOfDischarge")
        .not_empty("Terminal Full Name")
        .not_empty("EstimatedArrival")
        .is_empty("DISCHARGE_Time")
        .client_filter(_eta_passed)
    ),
    # 已卸船，GATEOUT_Time 为空
    "gateout": (
        BitableQuery().client_only()
        .not_empty("VesselIn")
        .not_empty("InVoyage")
        .not_empty("PortOfDischarge")
        .not_empty("Terminal Full Name")
        .not_empty("EstimatedArrival")
        .not_empty("DISCHARGE_Time")
        .is_empty("GATEOUT_Time")
        .client_filter(_eta_passed)
    ),
    "all": BitableQuery().client_only(),
}

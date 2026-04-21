from __future__ import annotations

from app.common.query_wrapper import QueryWrapper as BitableQuery
from app.service.sync.utils.datetime_parser import parse_datetime_to_timestamp

# 客户端过滤：ETA 已过（Bitable filter_expr 无法表达时间比较）
from datetime import UTC, datetime
from typing import Any

def _parse_bitable_datetime(value: str) -> datetime | None:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(value, fmt)
            return dt.replace(tzinfo=UTC)
        except (ValueError, OSError):
            continue
    return None


def _eta_passed(record: dict[str, Any]) -> bool:
    """ETA 已过（早于当前 UTC 时间）— Bitable filter_expr 无法表达时间比较。"""
    eta_str = record.get("EstimatedArrival")
    if not eta_str:
        return False
    eta = _parse_bitable_datetime(eta_str)
    return eta is not None and eta < datetime.now(UTC)


_CONDITIONS: dict[str, BitableQuery] = {
    # VesselIn/InVoyage/PortOfDischarge 任一为空
    "basic": BitableQuery().any_empty(["VesselIn", "InVoyage", "PortOfDischarge"]),
    # 船舶信息完整，Terminal/ETA 为空
    "terminal": (
        BitableQuery()
        .not_empty("VesselIn")
        .not_empty("InVoyage")
        .not_empty("PortOfDischarge")
        .any_empty(["Terminal Full Name", "EstimatedArrival"])
    ),
    # 码头/ETA 已有，ImportAvailability/StorageStartDate 为空
    "vessel_schedule": (
        BitableQuery()
        .not_empty("VesselIn")
        .not_empty("InVoyage")
        .not_empty("PortOfDischarge")
        .not_empty("Terminal Full Name")
        .not_empty("EstimatedArrival")
        .any_empty(["ImportAvailability", "StorageStartDate"])
    ),
    # ETA 已过，DISCHARGE_Time 为空
    "discharge": (
        BitableQuery()
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
        BitableQuery()
        .not_empty("VesselIn")
        .not_empty("InVoyage")
        .not_empty("PortOfDischarge")
        .not_empty("Terminal Full Name")
        .not_empty("EstimatedArrival")
        .not_empty("DISCHARGE_Time")
        .is_empty("GATEOUT_Time")
        .client_filter(_eta_passed)
    ),
    # all — 全部记录
    "all": BitableQuery(),
}

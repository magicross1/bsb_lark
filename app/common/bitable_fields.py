from __future__ import annotations

"""全局 Bitable 字段类型注册表。

每个字段的类型只在这里定义一次，所有模块共享。
FieldMapping 不再需要 field_type 参数——类型从此表自动解析。

类型: text / number / datetime / link / select
"""

FIELD_TYPES: dict[str, str] = {
    # ── Op-Vessel Schedule ──────────────────────────────
    "ETA": "datetime",
    "ETD": "datetime",
    "First Free": "datetime",
    "Last Free": "datetime",
    "Export Start": "datetime",
    "Export Cutoff": "datetime",
    "Actual Arrival": "text",
    "Terminal Name": "link",
    "Voyage": "text",
    "FULL Vessel Name": "text",
    "Vessel Name": "text",
    "Base Node": "link",
    # ── Op-Import ───────────────────────────────────────
    "Container Number": "text",
    "VesselIn": "text",
    "InVoyage": "text",
    "PortOfDischarge": "text",
    "Terminal Full Name": "text",
    "EstimatedArrival": "datetime",
    "ImportAvailability": "datetime",
    "StorageStartDate": "datetime",
    "ISO": "text",
    "CommodityIn": "text",
    "Gross Weight": "number",
    "ON_BOARD_VESSEL": "text",
    "ON_BOARD_VESSEL_Time": "datetime",
    "DISCHARGE": "text",
    "DISCHARGE_Time": "datetime",
    "GATEOUT": "text",
    "GATEOUT_Time": "datetime",
    "Clear Status": "text",
    "Quarantine": "text",
    "EDO PIN": "text",
    "Shipping Line": "link",
    "Empty Park": "link",
    "Record Status": "text",
    "Source EDO": "link",
    "Container Type": "select",
    "Commodity": "select",
    "Container Weight": "number",
    "Add Container": "select",
    "First Free": "datetime",
    "Last Free": "datetime",
    "ETA": "datetime",
    "FULL Vessel In": "link",
    "Terminal Name": "link",
    # ── Op-Export ────────────────────────────────────────
    "Booking Reference": "text",
    "Release Qty": "number",
    "Release Status": "text",
    # ── Op-Cartage ───────────────────────────────────────
    "Consingnee Name": "link",
    "Deliver Config": "link",
    "Import Booking": "link",
    "Export Booking": "link",
    "Source Cartage": "link",
}


def get_field_type(field_name: str, default: str = "text") -> str:
    return FIELD_TYPES.get(field_name, default)

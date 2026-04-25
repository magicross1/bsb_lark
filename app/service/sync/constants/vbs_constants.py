from __future__ import annotations

from app.common.query_wrapper import QueryWrapper as BitableQuery
from app.core.lark_bitable_value import extract_select_text

# ── VBS 通用：Terminal Full Name → operation 映射 ─────────────
_TERMINAL_TO_OPERATION: dict[str, str] = {
    "DP WORLD NS PORT BOTANY": "dpWorldNSW",
    "PATRICK NS PORT BOTANY": "patrickNSW",
    "DP WORLD, VI, WEST SWANSON": "dpWorldVIC",
    "PATRICK, VI, EAST SWANSON": "patrickVIC",
    "VICTORIA INTERNATIONAL CONTAINER TERMINAL": "victVIC",
}


def get_operation(terminal_full_name: object) -> str | None:
    """按 Terminal Full Name 返回 VBS operation，无映射返回 None。"""
    tfn = extract_select_text(terminal_full_name).strip().upper()
    return _TERMINAL_TO_OPERATION.get(tfn)


# ── VBS 可用性同步条件 ────────────────────────────────────────
# GATEOUT_Time 为空
_CONDITIONS: dict[str, BitableQuery] = {
    "pending": (
        BitableQuery().client_only()
        .is_empty("GATEOUT_Time")
    ),
    "all": BitableQuery().client_only(),
}

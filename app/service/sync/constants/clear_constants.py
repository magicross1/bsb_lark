from __future__ import annotations

from app.common.query_wrapper import QueryWrapper as BitableQuery

_HUTCHISON_TERMINAL = "HUTCHISON PORTS - PORT BOTANY"
_CLEAR_FINAL_STATUSES = {"CLEAR", "UNDERBOND APPROVAL", "RELEASED"}

# Terminal 不为空 + Clear Status 非终态
_CONDITIONS: dict[str, BitableQuery] = {
    "pending": (
        BitableQuery().client_only()
        .not_empty("Terminal Full Name")
        .not_in_or_empty("Clear Status", list(_CLEAR_FINAL_STATUSES))
    ),
    "all": BitableQuery().client_only(),
}

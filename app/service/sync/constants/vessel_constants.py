from __future__ import annotations

from app.common.query_wrapper import QueryWrapper as BitableQuery

_KEY_SEP = "|"

_BASE_NODE_MAP: dict[str, str] = {
    "SYDNEY": "PORT OF SYDNEY",
    "MELBOURNE": "PORT OF MELBOURNE",
}

_FINAL_ARRIVAL = {"Y", "SP"}

# Actual Arrival 为空或非终态
_CONDITIONS: dict[str, BitableQuery] = {
    "pending_arrival": (
        BitableQuery().client_only()
        .not_in_or_empty("Actual Arrival", list(_FINAL_ARRIVAL))
    ),
    "missing_eta": (
        BitableQuery().client_only()
        .is_empty("ETA")
    ),
    "all": BitableQuery().client_only(),
}

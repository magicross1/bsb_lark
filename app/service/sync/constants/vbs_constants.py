from __future__ import annotations

from app.common.query_wrapper import QueryWrapper as BitableQuery

# GATEOUT_Time 为空
_CONDITIONS: dict[str, BitableQuery] = {
    "pending": (
        BitableQuery().client_only()
        .is_empty("GATEOUT_Time")
    ),
    "all": BitableQuery().client_only(),
}

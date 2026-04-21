from __future__ import annotations

from app.common.query_wrapper import QueryWrapper as BitableQuery

# VBS 同步条件
_CONDITIONS: dict[str, BitableQuery] = {
    # pending — GATEOUT_Time 为空且 Terminal 可路由到 VBS
    "pending": BitableQuery().is_empty("GATEOUT_Time"),
    # all — 全部可路由到 VBS 的记录
    "all": BitableQuery(),
}

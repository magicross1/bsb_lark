from __future__ import annotations

from app.common.query_wrapper import QueryWrapper as BitableQuery

# EDO Pin Match 不为 Y（含空值）+ GATEOUT_Time 为空 + EDO PIN 不为空
# 注：Add Container=Y 条件在 fetch_records 的 Python 过滤中
_CONDITIONS: dict[str, BitableQuery] = {
    "pending": (
        BitableQuery().client_only()
        .not_in_or_empty("EDO Pin Match", ["Y"])
        .is_empty("GATEOUT_Time")
        .not_empty("EDO PIN")
    ),
    "all": BitableQuery().client_only(),
}

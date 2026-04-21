from __future__ import annotations

from app.common.query_wrapper import QueryWrapper as BitableQuery

_HUTCHISON_TERMINAL = "HUTCHISON PORTS - PORT BOTANY"
_CLEAR_FINAL_STATUSES = ["CLEAR", "UNDERBOND APPROVAL", "RELEASED"]

_CONDITIONS: dict[str, BitableQuery] = {
    # pending — Terminal 不为空且 Clear Status 未完结（非 CLEAR/UNDERBOND APPROVAL/RELEASED，含空值）
    "pending": BitableQuery().not_empty("Terminal Full Name").not_in_or_empty("Clear Status", _CLEAR_FINAL_STATUSES),
    # all — 全部记录
    "all": BitableQuery(),
}

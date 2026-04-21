from __future__ import annotations

from app.common.query_wrapper import QueryWrapper as BitableQuery
from app.common.lark_tables import T
from app.service.sync.utils.link_config import LinkConfig

# vessel key 分隔符
_KEY_SEP = "|"

# Base Node 文本 → 1-Stop base_node 参数
_BASE_NODE_MAP: dict[str, str] = {
    "SYDNEY": "PORT OF SYDNEY",
    "MELBOURNE": "PORT OF MELBOURNE",
}

_CONDITIONS: dict[str, BitableQuery] = {
    # pending_arrival — Actual Arrival 不为 Y 或 SP（含空值）
    "pending_arrival": BitableQuery().not_in_or_empty("Actual Arrival", ["Y", "SP"]),
    # missing_eta — ETA 为空
    "missing_eta": BitableQuery().is_empty("ETA"),
    # all — 全部记录
    "all": BitableQuery(),
}

# Terminal Name 关联字段配置
_TERMINAL_LINK = LinkConfig(table=T.md_terminal, search_field="Terminal Full Name")

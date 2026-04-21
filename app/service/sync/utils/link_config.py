from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LinkConfig:
    """关联字段解析配置 — 指定目标表和搜索字段，自动查找 record_id。

    用法:
        LinkConfig(table=T.md_terminal, search_field="Terminal Full Name")
        → 按 "Terminal Full Name" 搜索 MD-Terminal 表，返回匹配记录的 record_id
    """

    table: Any  # TableDef from lark_tables (e.g. T.md_terminal)
    search_field: str  # 目标表中的搜索字段 Bitable 显示名

    @property
    def table_id(self) -> str:
        return self.table.id

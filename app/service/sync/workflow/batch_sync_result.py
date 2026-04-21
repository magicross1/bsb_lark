from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BatchSyncResult:
    """sync_template 内部通用结果，具体业务 service 可转换为对应 schema。"""

    total: int = 0
    synced: int = 0
    errors: int = 0
    details: list[dict] = field(default_factory=list)

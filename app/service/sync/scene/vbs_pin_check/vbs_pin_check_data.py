from __future__ import annotations

from pydantic import Field

from app.service.sync.workflow.sync_data import SyncData


class VbsPinCheckData(SyncData):
    """VBS PIN Check 同步结果 — 只更新 EDO Pin Match 字段。"""

    container_number: str
    operation: str

    edo_pin_match: str | None = Field(None, alias="EDO Pin Match")

    def _metadata_fields(self) -> set[str]:
        return {"record_id", "container_number", "operation"}

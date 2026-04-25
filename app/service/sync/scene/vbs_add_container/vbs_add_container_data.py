from __future__ import annotations

from pydantic import Field

from app.service.sync.workflow.sync_data import SyncData


class VbsAddContainerData(SyncData):
    """VBS Add Container 同步结果。

    只更新 Add Container 字段（select: Y/N）。
    """

    container_number: str
    operation: str

    add_container: str | None = Field(None, alias="Add Container")

    def _metadata_fields(self) -> set[str]:
        return {"record_id", "container_number", "operation"}

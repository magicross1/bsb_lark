from __future__ import annotations

from pydantic import Field

from app.common.update_wrapper import UpdateWrapper
from app.service.sync.workflow.sync_data import SyncData


class ClearData(SyncData):
    """清关状态同步数据对象。

    1-Stop customs 返回: Clear Status + Quarantine
    Hutchison 额外返回: ISO + Gross Weight
    """

    container_number: str

    clear_status: str | None = Field(None, alias="Clear Status")
    quarantine: str | None = Field(None, alias="Quarantine")
    iso: str | None = Field(None, alias="ISO")
    gross_weight: float | None = Field(None, alias="Gross Weight")

    def _metadata_fields(self) -> set[str]:
        return {"record_id", "container_number"}

    def to_update_wrapper(self) -> UpdateWrapper:
        return super().to_update_wrapper().with_label(self.container_number)

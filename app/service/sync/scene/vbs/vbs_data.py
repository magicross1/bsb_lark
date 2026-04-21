from __future__ import annotations

from pydantic import Field

from app.common.update_wrapper import UpdateWrapper
from app.service.sync.workflow.sync_data import SyncData


class VbsData(SyncData):
    """VBS 集装箱可用性同步数据对象。"""

    container_number: str
    operation: str  # VBS operation 名称，不写回

    estimated_arrival: int | None = Field(None, alias="EstimatedArrival")  # 毫秒时间戳
    import_availability: int | None = Field(None, alias="ImportAvailability")  # 毫秒时间戳
    storage_start_date: int | None = Field(None, alias="StorageStartDate")  # 毫秒时间戳

    def _metadata_fields(self) -> set[str]:
        return {"record_id", "container_number", "operation"}

    def to_update_wrapper(self) -> UpdateWrapper:
        return super().to_update_wrapper().with_label(self.container_number)

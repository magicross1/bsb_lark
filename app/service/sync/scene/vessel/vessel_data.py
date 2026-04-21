from __future__ import annotations

from pydantic import Field

from app.service.sync.workflow.sync_data import SyncData


class VesselData(SyncData):
    """船期实时数据同步对象（来自 1-Stop）。

    datetime 字段已转为毫秒时间戳。
    terminal_name 已通过 LinkResolver 解析为 [record_id]。
    """

    vessel_key: str  # "vessel_name|voyage|base_node"，不写回

    eta: int | None = Field(None, alias="ETA")  # 毫秒时间戳
    etd: int | None = Field(None, alias="ETD")
    first_free: int | None = Field(None, alias="First Free")
    last_free: int | None = Field(None, alias="Last Free")
    export_start: int | None = Field(None, alias="Export Start")
    export_cutoff: int | None = Field(None, alias="Export Cutoff")
    actual_arrival: str | None = Field(None, alias="Actual Arrival")
    terminal_name: list[str] | None = Field(None, alias="Terminal Name")  # 已解析为 [record_id]

    def _metadata_fields(self) -> set[str]:
        return {"record_id", "vessel_key"}

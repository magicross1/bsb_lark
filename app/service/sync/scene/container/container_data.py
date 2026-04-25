from __future__ import annotations

from pydantic import Field

from app.common.update_wrapper import UpdateWrapper
from app.service.sync.workflow.sync_data import SyncData


class ContainerData(SyncData):
    """集装箱港口状态同步数据对象（来自 1-Stop）。"""

    container_number: str

    # 船舶信息
    vessel_in: str | None = Field(None, alias="VesselIn")
    in_voyage: str | None = Field(None, alias="InVoyage")
    port_of_discharge: list[str] | None = Field(None, alias="PortOfDischarge")  # link → MD-Base Node
    full_vessel_in: list[str] | None = Field(None, alias="Full Vessel In")  # link → Op-Vessel Schedule
    full_vessel_name: list[str] | None = Field(None, alias="FULL Vessel Name")  # link → Op-Vessel Schedule

    # 码头/ETA
    terminal_full_name: str | None = Field(None, alias="Terminal Full Name")
    terminal_name: list[str] | None = Field(None, alias="Terminal Name")  # link → MD-Terminal
    estimated_arrival: int | None = Field(None, alias="EstimatedArrival")  # 毫秒时间戳
    eta: int | None = Field(None, alias="ETA")  # 毫秒时间戳

    # 船期可用性
    import_availability: int | None = Field(None, alias="ImportAvailability")  # 毫秒时间戳
    first_free: int | None = Field(None, alias="First Free")  # = ImportAvailability
    storage_start_date: int | None = Field(None, alias="StorageStartDate")  # 毫秒时间戳
    last_free: int | None = Field(None, alias="Last Free")  # = StorageStartDate

    # 货物详情
    iso: str | None = Field(None, alias="ISO")
    commodity_in: str | None = Field(None, alias="CommodityIn")
    gross_weight: float | None = Field(None, alias="Gross Weight")
    container_type: list[str] | None = Field(None, alias="Container Type")  # link → DT-Container Type
    commodity: list[str] | None = Field(None, alias="Commodity")  # link → DT-Commodity
    container_weight: float | None = Field(None, alias="Container Weight")

    # 在船状态
    on_board_vessel: str | None = Field(None, alias="ON_BOARD_VESSEL")
    on_board_vessel_time: int | None = Field(None, alias="ON_BOARD_VESSEL_Time")

    # 卸船状态
    discharge: str | None = Field(None, alias="DISCHARGE")
    discharge_time: int | None = Field(None, alias="DISCHARGE_Time")

    # 提柜状态
    gateout: str | None = Field(None, alias="GATEOUT")
    gateout_time: int | None = Field(None, alias="GATEOUT_Time")

    def _metadata_fields(self) -> set[str]:
        return {"record_id", "container_number"}

    def to_update_wrapper(self) -> UpdateWrapper:
        return super().to_update_wrapper().with_label(self.container_number)

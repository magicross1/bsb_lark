from __future__ import annotations

import logging
from typing import Any

from app.common.assert_utils import assert_in
from app.common.collection_utils import filter_by, pluck, to_map
from app.component.OneStopProvider import OneStopProvider
from app.common.query_wrapper import QueryWrapper
from app.repository.import_ import ImportRepository
from app.service.sync.constants.container_constants import _CONDITIONS
from app.service.sync.workflow.batch_sync_result import BatchSyncResult
from app.service.sync.scene.container.container_data import ContainerData
from app.service.sync.utils.datetime_parser import safe_ts
from app.service.sync.workflow.sync_template import SyncTemplate

logger = logging.getLogger(__name__)


class ContainerSyncService(SyncTemplate):
    """集装箱港口数据同步服务（模板模式）。"""

    def __init__(
        self,
        import_repo: ImportRepository | None = None,
        onestop: OneStopProvider | None = None,
    ) -> None:
        self._repo = import_repo or ImportRepository()
        self._onestop = onestop or OneStopProvider.get_instance()

    @property
    def repository(self) -> ImportRepository:
        return self._repo

    @staticmethod
    def list_conditions() -> list[str]:
        return list(_CONDITIONS.keys())

    # ── Step 1 ──────────────────────────────────────────────

    async def fetch_records(self, condition: str) -> list[dict]:
        query = assert_in(condition, _CONDITIONS, f"未知条件 '{condition}'，可用: {', '.join(_CONDITIONS)}")
        all_records = await self._repo.list(query)
        logger.info("集装箱批量同步 [%s]: %d 条", condition, len(all_records))
        return all_records

    # ── Step 2 ──────────────────────────────────────────────

    async def fetch_provider_data(self, records: list[dict]) -> list[ContainerData]:
        cns = pluck(records, "Container Number")
        if not cns:
            return []

        cn_to_rid = to_map(records, "Container Number")
        raw_data = await self._onestop.match_containers_info_by_list(cns)

        result: list[ContainerData] = []
        for cn in cns:
            rid = cn_to_rid.get(cn)
            raw = raw_data.get(cn)
            if not rid or not raw:
                continue
            result.append(self._parse(rid, cn, raw))
        return result

    # ── 解析 ────────────────────────────────────────────────

    @staticmethod
    def _parse(record_id: str, container_number: str, raw: dict[str, Any]) -> ContainerData:
        def _str(key: str) -> str | None:
            v = raw.get(key)
            return str(v) if v else None

        def _float(key: str) -> float | None:
            v = raw.get(key)
            try:
                return float(v) if v else None
            except (ValueError, TypeError):
                return None

        return ContainerData(
            record_id=record_id,
            container_number=container_number,
            vessel_in=_str("VesselIn"),
            in_voyage=_str("InVoyage"),
            port_of_discharge=_str("PortOfDischarge"),
            terminal_full_name=_str("Terminal Full Name"),
            estimated_arrival=safe_ts(raw, "EstimatedArrival"),
            import_availability=safe_ts(raw, "ImportAvailability"),
            storage_start_date=safe_ts(raw, "StorageStartDate"),
            iso=_str("ISO"),
            commodity_in=_str("CommodityIn"),
            gross_weight=_float("Gross Weight"),
            on_board_vessel=_str("ON_BOARD_VESSEL"),
            on_board_vessel_time=_str("ON_BOARD_VESSEL_Time"),
            discharge=_str("DISCHARGE"),
            discharge_time=_str("DISCHARGE_Time"),
            gateout=_str("GATEOUT"),
            gateout_time=_str("GATEOUT_Time"),
        )

    # ── 对外接口 ─────────────────────────────────────────────

    async def sync(self, container_numbers: list[str]) -> BatchSyncResult:
        """手动触发：按柜号列表同步。"""
        if not container_numbers:
            return BatchSyncResult()

        all_records = await self._repo.list(QueryWrapper().select("Container Number"))
        records = filter_by(all_records, "Container Number", container_numbers)
        if not records:
            return BatchSyncResult(total=len(container_numbers))

        data_list = await self.fetch_provider_data(records)
        wrappers = self.build_update_wrappers(data_list)
        return await self._persist(wrappers)

    async def sync_batch(self, condition: str = "basic") -> BatchSyncResult:
        return await self.run_batch(condition)

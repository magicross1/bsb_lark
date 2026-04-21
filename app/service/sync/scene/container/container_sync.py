from __future__ import annotations

import logging
from typing import Any

from app.component.OneStopProvider import OneStopProvider
from app.common.query_wrapper import QueryWrapper
from app.repository.import_ import ImportRepository
from app.service.sync.constants.container_constants import _CONDITIONS
from app.service.sync.result.container_batch_sync_result import ContainerBatchSyncResult
from app.service.sync.scene.container.container_data import ContainerData
from app.service.sync.utils.datetime_parser import parse_datetime_to_timestamp
from app.service.sync.workflow.sync_template import SyncTemplate

logger = logging.getLogger(__name__)


class ContainerSyncService(SyncTemplate):
    """集装箱港口数据同步服务（模板模式）。

    Step 1: 按 condition 从 Op-Import 筛选记录
    Step 2: 调用 1-Stop，解析为 ContainerData（datetime 字段转时间戳）
    Step 3: 构建 UpdateWrapper，写回 Bitable
    """

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
        query = _CONDITIONS.get(condition)
        if query is None:
            available = ", ".join(_CONDITIONS.keys())
            raise ValueError(f"未知条件 '{condition}'，可用条件: {available}")
        all_records = await self._repo.list(query)
        logger.info("集装箱批量同步 [%s]: %d 条", condition, len(pending))
        return pending

    # ── Step 2 ──────────────────────────────────────────────

    async def fetch_provider_data(self, records: list[dict]) -> list[ContainerData]:
        container_numbers = [cn for r in records if (cn := r.get("Container Number"))]
        if not container_numbers:
            return []

        raw_data = await self._onestop.match_containers_info_by_list(container_numbers)
        cn_to_record_id = {
            cn: r["record_id"] for r in records if (cn := r.get("Container Number"))
        }

        result: list[ContainerData] = []
        for cn in container_numbers:
            record_id = cn_to_record_id.get(cn)
            raw = raw_data.get(cn)
            if not record_id or not raw:
                continue
            result.append(self._parse(record_id, cn, raw))
        return result

    # ── 解析 ────────────────────────────────────────────────

    @staticmethod
    def _parse(record_id: str, container_number: str, raw: dict[str, Any]) -> ContainerData:
        def _ts(key: str) -> int | None:
            v = raw.get(key)
            return parse_datetime_to_timestamp(str(v)) if v else None

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
            estimated_arrival=_ts("EstimatedArrival"),
            import_availability=_ts("ImportAvailability"),
            storage_start_date=_ts("StorageStartDate"),
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

    async def sync(self, container_numbers: list[str]) -> ContainerBatchSyncResult:
        """手动触发：按柜号列表同步。"""
        if not container_numbers:
            return ContainerBatchSyncResult()

        cn_set = set(container_numbers)
        all_records = await self._repo.list(QueryWrapper().select("Container Number"))
        records = [r for r in all_records if r.get("Container Number") in cn_set]
        if not records:
            return ContainerBatchSyncResult(total=len(container_numbers))

        data_list = await self.fetch_provider_data(records)
        wrappers = self.build_update_wrappers(data_list)
        batch_result = await self._persist(wrappers)
        return ContainerBatchSyncResult(
            total=batch_result.total,
            synced=batch_result.synced,
            errors=batch_result.errors,
        )

    async def sync_batch(self, condition: str = "basic") -> ContainerBatchSyncResult:
        result = await self.run_batch(condition)
        return ContainerBatchSyncResult(
            total=result.total,
            synced=result.synced,
            errors=result.errors,
        )

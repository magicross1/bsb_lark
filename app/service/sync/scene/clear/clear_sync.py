from __future__ import annotations

import logging

from app.common.assert_utils import assert_in
from app.common.collection_utils import filter_by, partition, pluck, to_map
from app.component.HutchisonPortsProvider import HutchisonPortsProvider
from app.component.OneStopProvider import OneStopProvider
from app.common.query_wrapper import QueryWrapper
from app.repository.import_ import ImportRepository
from app.service.sync.constants.clear_constants import _CONDITIONS, _HUTCHISON_TERMINAL
from app.service.sync.workflow.batch_sync_result import BatchSyncResult
from app.service.sync.scene.clear.clear_data import ClearData
from app.service.sync.workflow.sync_template import SyncTemplate

logger = logging.getLogger(__name__)


class ClearSyncService(SyncTemplate):
    """清关状态同步服务（模板模式）。"""

    def __init__(
        self,
        import_repo: ImportRepository | None = None,
        onestop: OneStopProvider | None = None,
        hutchison: HutchisonPortsProvider | None = None,
    ) -> None:
        self._repo = import_repo or ImportRepository()
        self._onestop = onestop or OneStopProvider.get_instance()
        self._hutchison = hutchison or HutchisonPortsProvider()

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
        logger.info("清关批量同步 [%s]: %d 条", condition, len(all_records))
        return all_records

    # ── Step 2 ──────────────────────────────────────────────

    async def fetch_provider_data(self, records: list[dict]) -> list[ClearData]:
        """按 Terminal Full Name 分组，路由到对应 Provider。"""
        hutchison_records, other_records = partition(
            records,
            lambda r: (r.get("Terminal Full Name") or "").strip().upper() == _HUTCHISON_TERMINAL,
        )

        result: list[ClearData] = []
        if other_records:
            result.extend(await self._fetch_from_onestop(other_records))
        if hutchison_records:
            result.extend(await self._fetch_from_hutchison(hutchison_records))
        return result

    # ── Provider 查询 ────────────────────────────────────────

    async def _fetch_from_onestop(self, records: list[dict]) -> list[ClearData]:
        cns = pluck(records, "Container Number")
        cn_to_rid = to_map(records, "Container Number")
        raw_data = await self._onestop.customs_cargo_status_search(cns)

        result: list[ClearData] = []
        for cn in cns:
            rid = cn_to_rid.get(cn)
            raw = raw_data.get(cn)
            if not rid or not raw:
                continue
            result.append(
                ClearData(
                    record_id=rid,
                    container_number=cn,
                    clear_status=raw.get("Clear Status") or None,
                    quarantine=raw.get("Quarantine") or None,
                )
            )
        return result

    async def _fetch_from_hutchison(self, records: list[dict]) -> list[ClearData]:
        cns = pluck(records, "Container Number")
        cn_to_rid = to_map(records, "Container Number")
        raw_data = await self._hutchison.container_enquiry_by_list(cns)

        result: list[ClearData] = []
        for cn in cns:
            rid = cn_to_rid.get(cn)
            raw = raw_data.get(cn)
            if not rid or not raw:
                continue

            gross_weight: float | None = None
            gw = raw.get("Gross Weight")
            if gw:
                try:
                    gross_weight = float(gw)
                except (ValueError, TypeError):
                    pass

            result.append(
                ClearData(
                    record_id=rid,
                    container_number=cn,
                    clear_status=raw.get("Clear Status") or None,
                    quarantine=raw.get("Quarantine") or None,
                    iso=raw.get("ISO") or None,
                    gross_weight=gross_weight,
                )
            )
        return result

    # ── 对外接口 ─────────────────────────────────────────────

    async def sync(
        self,
        container_numbers: list[str],
        terminal_full_name: str | None = None,
    ) -> BatchSyncResult:
        """手动触发：按柜号列表同步。"""
        if not container_numbers:
            return BatchSyncResult()

        all_records = await self._repo.list(QueryWrapper().select("Container Number", "Terminal Full Name"))
        records = filter_by(all_records, "Container Number", container_numbers)
        if terminal_full_name:
            for r in records:
                r["Terminal Full Name"] = terminal_full_name
        if not records:
            return BatchSyncResult(total=len(container_numbers))

        data_list = await self.fetch_provider_data(records)
        wrappers = self.build_update_wrappers(data_list)
        return await self._persist(wrappers)

    async def sync_batch(self, condition: str = "pending") -> BatchSyncResult:
        return await self.run_batch(condition)

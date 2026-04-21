from __future__ import annotations

import logging

from app.component.HutchisonPortsProvider import HutchisonPortsProvider
from app.component.OneStopProvider import OneStopProvider
from app.common.query_wrapper import QueryWrapper
from app.repository.import_ import ImportRepository
from app.service.sync.constants.clear_constants import _CONDITIONS, _HUTCHISON_TERMINAL
from app.service.sync.result.clear_batch_sync_result import ClearBatchSyncResult
from app.service.sync.scene.clear.clear_data import ClearData
from app.service.sync.workflow.sync_template import SyncTemplate

logger = logging.getLogger(__name__)


class ClearSyncService(SyncTemplate):
    """清关状态同步服务（模板模式）。

    Step 1: 按 condition 从 Op-Import 筛选记录
    Step 2: 按 Terminal Full Name 路由 Provider
        - HUTCHISON PORTS - PORT BOTANY → HutchisonPortsProvider
        - 其他 Terminal → OneStopProvider
    Step 3: 构建 UpdateWrapper，写回 Bitable
    """

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
        query = _CONDITIONS.get(condition)
        if query is None:
            available = ", ".join(_CONDITIONS.keys())
            raise ValueError(f"未知条件 '{condition}'，可用条件: {available}")
        all_records = await self._repo.list(query)
        logger.info("清关批量同步 [%s]: %d 条", condition, len(pending))
        return pending

    # ── Step 2 ──────────────────────────────────────────────

    async def fetch_provider_data(self, records: list[dict]) -> list[ClearData]:
        """按 Terminal Full Name 分组，路由到对应 Provider。"""
        hutchison_records: list[dict] = []
        other_records: list[dict] = []

        for r in records:
            tfn = r.get("Terminal Full Name")
            if (tfn or "").strip().upper() == _HUTCHISON_TERMINAL:
                hutchison_records.append(r)
            else:
                other_records.append(r)

        result: list[ClearData] = []
        if other_records:
            result.extend(await self._fetch_from_onestop(other_records))
        if hutchison_records:
            result.extend(await self._fetch_from_hutchison(hutchison_records))
        return result

    # ── Provider 查询 ────────────────────────────────────────

    async def _fetch_from_onestop(self, records: list[dict]) -> list[ClearData]:
        container_numbers = [cn for r in records if (cn := r.get("Container Number"))]
        cn_to_record_id = {cn: r["record_id"] for r in records if (cn := r.get("Container Number"))}
        raw_data = await self._onestop.customs_cargo_status_search(container_numbers)

        result: list[ClearData] = []
        for cn in container_numbers:
            record_id = cn_to_record_id.get(cn)
            raw = raw_data.get(cn)
            if not record_id or not raw:
                continue
            result.append(
                ClearData(
                    record_id=record_id,
                    container_number=cn,
                    clear_status=raw.get("Clear Status") or None,
                    quarantine=raw.get("Quarantine") or None,
                )
            )
        return result

    async def _fetch_from_hutchison(self, records: list[dict]) -> list[ClearData]:
        container_numbers = [cn for r in records if (cn := r.get("Container Number"))]
        cn_to_record_id = {cn: r["record_id"] for r in records if (cn := r.get("Container Number"))}
        raw_data = await self._hutchison.container_enquiry_by_list(container_numbers)

        result: list[ClearData] = []
        for cn in container_numbers:
            record_id = cn_to_record_id.get(cn)
            raw = raw_data.get(cn)
            if not record_id or not raw:
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
                    record_id=record_id,
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
    ) -> ClearBatchSyncResult:
        """手动触发：按柜号列表同步。"""
        if not container_numbers:
            return ClearBatchSyncResult()

        cn_set = set(container_numbers)
        all_records = await self._repo.list(QueryWrapper().select("Container Number", "Terminal Full Name"))
        records = [r for r in all_records if r.get("Container Number") in cn_set]
        if terminal_full_name:
            for r in records:
                r["Terminal Full Name"] = terminal_full_name
        if not records:
            return ClearBatchSyncResult(total=len(container_numbers))

        data_list = await self.fetch_provider_data(records)
        wrappers = self.build_update_wrappers(data_list)
        batch_result = await self._persist(wrappers)
        return ClearBatchSyncResult(
            total=batch_result.total,
            synced=batch_result.synced,
            errors=batch_result.errors,
        )

    async def sync_batch(self, condition: str = "pending") -> ClearBatchSyncResult:
        result = await self.run_batch(condition)
        return ClearBatchSyncResult(
            total=result.total,
            synced=result.synced,
            errors=result.errors,
        )

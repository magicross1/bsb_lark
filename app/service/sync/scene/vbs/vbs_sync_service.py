from __future__ import annotations

import logging

from app.common.query_wrapper import QueryWrapper
from app.service.sync.factory.vbs_sync_factory import VbsSyncFactory
from app.service.sync.result.vbs_batch_sync_result import VbsBatchSyncResult

logger = logging.getLogger(__name__)


class VbsSyncService:
    """VBS 同步服务 — 委托策略工厂选择码头同步器，协调批量与单次同步。"""

    def __init__(self, factory: VbsSyncFactory | None = None) -> None:
        self._factory = factory or VbsSyncFactory()

    @staticmethod
    def list_conditions() -> list[str]:
        return VbsSyncFactory.list_conditions()

    async def sync(
        self,
        container_numbers: list[str],
        terminal_full_name: str | None = None,
    ) -> VbsBatchSyncResult:
        """手动触发：按 Terminal 路由同步器，按柜号同步。"""
        if not container_numbers:
            return VbsBatchSyncResult()

        syncer = self._factory.get(terminal_full_name or "")
        if not syncer:
            return VbsBatchSyncResult(total=len(container_numbers))

        cn_set = set(container_numbers)
        all_records = await syncer.repository.list(QueryWrapper().select("Container Number"))
        records = [r for r in all_records if r.get("Container Number") in cn_set]

        data_list = await syncer.fetch_provider_data(records)
        wrappers = syncer.build_update_wrappers(data_list)
        batch_result = await syncer._persist(wrappers)
        return VbsBatchSyncResult(
            total=batch_result.total,
            synced=batch_result.synced,
            errors=batch_result.errors,
        )

    async def sync_batch(self, condition: str = "pending") -> VbsBatchSyncResult:
        """批量同步：依次运行全部码头，合并结果。"""
        total, synced, errors = 0, 0, 0
        for syncer in self._factory.all():
            result = await syncer.run_batch(condition)
            total += result.total
            synced += result.synced
            errors += result.errors
        return VbsBatchSyncResult(total=total, synced=synced, errors=errors)

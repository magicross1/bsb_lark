from __future__ import annotations

import logging

from app.common.collection_utils import filter_by
from app.common.query_wrapper import QueryWrapper
from app.service.sync.factory.vbs_sync_factory import VbsSyncFactory
from app.service.sync.workflow.batch_sync_result import BatchSyncResult

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
    ) -> BatchSyncResult:
        """手动触发：按 Terminal 路由同步器，按柜号同步。"""
        if not container_numbers:
            return BatchSyncResult()

        syncer = self._factory.get(terminal_full_name or "")
        if not syncer:
            return BatchSyncResult(total=len(container_numbers))

        all_records = await syncer.repository.list(QueryWrapper().select("Container Number"))
        records = filter_by(all_records, "Container Number", container_numbers)

        data_list = await syncer.fetch_provider_data(records)
        wrappers = syncer.build_update_wrappers(data_list)
        return await syncer._persist(wrappers)

    async def sync_batch(self, condition: str = "pending") -> BatchSyncResult:
        """批量同步：依次运行全部码头，合并结果。"""
        total, synced, errors = 0, 0, 0
        for syncer in self._factory.all():
            result = await syncer.run_batch(condition)
            total += result.total
            synced += result.synced
            errors += result.errors
        return BatchSyncResult(total=total, synced=synced, errors=errors)

from __future__ import annotations

import logging

from app.common.assert_utils import assert_in
from app.common.collection_utils import pluck, to_map, group_by
from app.common.query_wrapper import QueryWrapper
from app.component.VbsSearchProvider import VbsSearchProvider
from app.core.lark_bitable_value import extract_select_text
from app.repository.import_ import ImportRepository
from app.service.sync.constants.vbs_add_container_constants import _CONDITIONS, get_operation
from app.service.sync.scene.vbs_add_container.vbs_add_container_data import VbsAddContainerData
from app.service.sync.workflow.batch_sync_result import BatchSyncResult
from app.service.sync.workflow.sync_template import SyncTemplate

logger = logging.getLogger(__name__)


class VbsAddContainerSyncService(SyncTemplate):
    """VBS Add Container 同步 — 按 Terminal 路由 operation，add → check → 更新 Add Container。"""

    def __init__(
        self,
        import_repo: ImportRepository | None = None,
        vbs: VbsSearchProvider | None = None,
    ) -> None:
        self._repo = import_repo or ImportRepository()
        self._vbs = vbs or VbsSearchProvider()

    @property
    def repository(self) -> ImportRepository:
        return self._repo

    @staticmethod
    def list_conditions() -> list[str]:
        return list(_CONDITIONS.keys())

    async def fetch_records(self, condition: str, **kwargs) -> list[dict]:
        query = assert_in(condition, _CONDITIONS, f"未知条件 '{condition}'，可用: {', '.join(_CONDITIONS)}")
        all_records = await self._repo.list(query)
        records = [r for r in all_records if get_operation(r.get("Terminal Full Name"))]
        logger.info("VBS Add Container [%s]: %d 条", condition, len(records))
        return records

    async def fetch_provider_data(self, records: list[dict]) -> list[VbsAddContainerData]:
        cn_to_rid = to_map(records, "Container Number")
        grouped = group_by(records, lambda r: get_operation(r.get("Terminal Full Name")))

        result: list[VbsAddContainerData] = []
        for operation, group in grouped.items():
            cns = pluck(group, "Container Number")
            if not cns:
                continue

            await self._vbs.add_ctn_by_list(cns, operation)
            check_result = await self._vbs.check_add_ctn_by_list(cns, operation)

            for cn in cns:
                rid = cn_to_rid.get(cn)
                info = check_result.get(cn)
                add_ctn = info.get("Add Container") if info else None
                if not rid:
                    continue
                result.append(VbsAddContainerData(
                    record_id=rid,
                    container_number=cn,
                    operation=operation,
                    add_container=add_ctn,
                ))
        return result

    async def sync_single(self, container_number: str, terminal_full_name: str) -> BatchSyncResult:
        """手动触发：单条 add + check + 更新。"""
        operation = get_operation(terminal_full_name)
        if not operation:
            return BatchSyncResult(total=1)

        record = await self._repo.findOne(QueryWrapper().eq("Container Number", container_number))
        if not record:
            return BatchSyncResult(total=1)

        await self._vbs.add_ctn_by_list([container_number], operation)
        check_result = await self._vbs.check_add_ctn_by_list([container_number], operation)

        info = check_result.get(container_number)
        add_ctn = info.get("Add Container") if info else None

        data = VbsAddContainerData(
            record_id=record["record_id"],
            container_number=container_number,
            operation=operation,
            add_container=add_ctn,
        )

        if not data.has_fields():
            return BatchSyncResult(total=1)

        wrapper = data.to_update_wrapper()
        await self._repo.updateOne(wrapper)
        logger.info("VBS Add Container 单条 %s → %s", container_number, add_ctn)
        return BatchSyncResult(total=1, synced=1)

    async def sync_batch(self, condition: str = "pending") -> BatchSyncResult:
        records = await self.fetch_records(condition)
        if not records:
            return BatchSyncResult()
        data_list = await self.fetch_provider_data(records)
        wrappers = self.build_update_wrappers(data_list)
        return await self._persist(wrappers)

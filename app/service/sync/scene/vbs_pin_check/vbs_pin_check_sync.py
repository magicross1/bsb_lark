from __future__ import annotations

import logging

from app.common.assert_utils import assert_in
from app.common.collection_utils import pluck, to_map, group_by
from app.common.query_wrapper import QueryWrapper
from app.component.VbsSearchProvider import VbsSearchProvider
from app.core.lark_bitable_value import extract_cell_text, extract_select_text
from app.repository.import_ import ImportRepository
from app.service.sync.constants.vbs_constants import get_operation
from app.service.sync.constants.vbs_pin_check_constants import _CONDITIONS
from app.service.sync.scene.vbs_pin_check.vbs_pin_check_data import VbsPinCheckData
from app.service.sync.workflow.batch_sync_result import BatchSyncResult
from app.service.sync.workflow.sync_template import SyncTemplate

logger = logging.getLogger(__name__)


class VbsPinCheckSyncService(SyncTemplate):
    """VBS PIN Check 同步 — 按 Terminal 路由 operation，pin_check + check_add → 更新 EDO Pin Match。"""

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
        records = [
            r for r in all_records
            if get_operation(r.get("Terminal Full Name"))
            and extract_select_text(r.get("Add Container")).strip().upper() == "Y"
        ]
        logger.info("VBS PIN Check [%s]: %d 条", condition, len(records))
        return records

    async def fetch_provider_data(self, records: list[dict]) -> list[VbsPinCheckData]:
        cn_to_rid = to_map(records, "Container Number")
        grouped = group_by(records, lambda r: get_operation(r.get("Terminal Full Name")))

        result: list[VbsPinCheckData] = []
        for operation, group in grouped.items():
            cns = pluck(group, "Container Number")
            pins = [extract_cell_text(r.get("EDO PIN")) or "" for r in group]
            pins = [p.strip() for p in pins if p.strip()]
            if not cns:
                continue

            if pins:
                await self._vbs.pin_check_by_list(pins, operation)
            check_result = await self._vbs.check_add_ctn_by_list(cns, operation)

            for cn in cns:
                rid = cn_to_rid.get(cn)
                info = check_result.get(cn)
                edo_pin_match = info.get("EDO Pin Match") if info else None
                if not rid:
                    continue
                result.append(VbsPinCheckData(
                    record_id=rid,
                    container_number=cn,
                    operation=operation,
                    edo_pin_match=edo_pin_match,
                ))
        return result

    async def sync_single(self, container_number: str, terminal_full_name: str) -> BatchSyncResult:
        """手动触发：单条 pin_check + check_add + 更新。"""
        operation = get_operation(terminal_full_name)
        if not operation:
            return BatchSyncResult(total=1)

        record = await self._repo.findOne(QueryWrapper().eq("Container Number", container_number))
        if not record:
            return BatchSyncResult(total=1)

        edo_pin = (extract_cell_text(record.get("EDO PIN")) or "").strip()
        if edo_pin:
            await self._vbs.pin_check_by_list([edo_pin], operation)
        check_result = await self._vbs.check_add_ctn_by_list([container_number], operation)

        info = check_result.get(container_number)
        edo_pin_match = info.get("EDO Pin Match") if info else None

        data = VbsPinCheckData(
            record_id=record["record_id"],
            container_number=container_number,
            operation=operation,
            edo_pin_match=edo_pin_match,
        )

        if not data.has_fields():
            return BatchSyncResult(total=1)

        wrapper = data.to_update_wrapper()
        await self._repo.updateOne(wrapper)
        logger.info("VBS PIN Check 单条 %s → EDO Pin Match=%s", container_number, edo_pin_match)
        return BatchSyncResult(total=1, synced=1)

    async def sync_batch(self, condition: str = "pending") -> BatchSyncResult:
        records = await self.fetch_records(condition)
        if not records:
            return BatchSyncResult()
        data_list = await self.fetch_provider_data(records)
        wrappers = self.build_update_wrappers(data_list)
        return await self._persist(wrappers)

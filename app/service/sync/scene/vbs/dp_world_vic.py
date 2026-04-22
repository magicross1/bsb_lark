from __future__ import annotations

import logging

from app.common.assert_utils import assert_in
from app.common.collection_utils import pluck, to_map
from app.component.VbsSearchProvider import VbsSearchProvider
from app.repository.import_ import ImportRepository
from app.service.sync.constants.vbs_constants import _CONDITIONS
from app.service.sync.scene.vbs.vbs_data import VbsData
from app.service.sync.utils.datetime_parser import safe_ts
from app.service.sync.workflow.sync_template import SyncTemplate

logger = logging.getLogger(__name__)


class DpWorldVicVbsSync(SyncTemplate):
    """DP WORLD, VI, WEST SWANSON 的 VBS 同步。"""

    TERMINAL_FULL_NAME = "DP WORLD, VI, WEST SWANSON"
    OPERATION = "dpWorldVIC"

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

    async def fetch_records(self, condition: str) -> list[dict]:
        query = assert_in(condition, _CONDITIONS, f"未知条件 '{condition}'，可用: {', '.join(_CONDITIONS)}")

        all_records = await self._repo.list(query)
        records = [
            r for r in all_records
            if (r.get("Terminal Full Name") or "").strip().upper() == self.TERMINAL_FULL_NAME
        ]
        logger.info("VBS 批量同步 [%s/%s]: %d 条", self.OPERATION, condition, len(records))
        return records

    async def fetch_provider_data(self, records: list[dict]) -> list[VbsData]:
        cns = pluck(records, "Container Number")
        if not cns:
            return []

        cn_to_rid = to_map(records, "Container Number")
        raw_data = await self._vbs.get_ctn_info_by_list(cns, self.OPERATION)

        result: list[VbsData] = []
        for cn in cns:
            rid = cn_to_rid.get(cn)
            raw = raw_data.get(cn)
            if not rid or not raw:
                continue
            result.append(VbsData(
                record_id=rid,
                container_number=cn,
                operation=self.OPERATION,
                estimated_arrival=safe_ts(raw, "EstimatedArrival"),
                import_availability=safe_ts(raw, "ImportAvailability"),
                storage_start_date=safe_ts(raw, "StorageStartDate"),
            ))
        return result

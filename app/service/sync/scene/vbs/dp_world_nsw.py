from __future__ import annotations

import logging

from app.component.VbsSearchProvider import VbsSearchProvider
from app.repository.import_ import ImportRepository
from app.service.sync.constants.vbs_constants import _CONDITIONS
from app.service.sync.scene.vbs.vbs_data import VbsData
from app.service.sync.utils.datetime_parser import parse_datetime_to_timestamp
from app.service.sync.workflow.sync_template import SyncTemplate

logger = logging.getLogger(__name__)


class DpWorldNswVbsSync(SyncTemplate):
    """DP WORLD NS PORT BOTANY 的 VBS 同步。

    provider 负责 VBS 爬取；本类负责：
    - 筛选属于本码头的记录
    - 以 dpWorldNSW operation 查询 VBS
    - 将结果写回 Bitable
    """

    TERMINAL_FULL_NAME = "DP WORLD NS PORT BOTANY"
    OPERATION = "dpWorldNSW"

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
        query = _CONDITIONS.get(condition)
        if query is None:
            available = ", ".join(_CONDITIONS.keys())
            raise ValueError(f"未知条件 '{condition}'，可用条件: {available}")

        all_records = await self._repo.list(query)
        records = [
            r for r in pending
            if (r.get("Terminal Full Name") or "").strip().upper() == self.TERMINAL_FULL_NAME
        ]
        logger.info("VBS 批量同步 [%s/%s]: %d 条", self.OPERATION, condition, len(records))
        return records

    async def fetch_provider_data(self, records: list[dict]) -> list[VbsData]:
        container_numbers = [cn for r in records if (cn := r.get("Container Number"))]
        if not container_numbers:
            return []

        cn_to_record_id = {r.get("Container Number"): r["record_id"] for r in records if r.get("Container Number")}
        raw_data = await self._vbs.get_ctn_info_by_list(container_numbers, self.OPERATION)

        result: list[VbsData] = []
        for cn in container_numbers:
            record_id = cn_to_record_id.get(cn)
            raw = raw_data.get(cn)
            if not record_id or not raw:
                continue
            result.append(VbsData(
                record_id=record_id,
                container_number=cn,
                operation=self.OPERATION,
                estimated_arrival=_ts(raw, "EstimatedArrival"),
                import_availability=_ts(raw, "ImportAvailability"),
                storage_start_date=_ts(raw, "StorageStartDate"),
            ))
        return result


def _ts(raw: dict, key: str) -> int | None:
    v = raw.get(key)
    return parse_datetime_to_timestamp(str(v)) if v else None

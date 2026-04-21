from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from app.common.bitable_query import BitableQuery
from app.component.OneStopProvider import OneStopProvider
from app.core.lark_bitable_value import extract_cell_text
from app.repository.import_ import ImportRepository
from app.service.sync.base import (
    BatchCondition,
    FieldMapping,
    LinkResolver,
    batch_write_back,
    build_update_fields,
)
from app.service.sync.model.container_sync_schemas import ContainerBatchSyncResult, ContainerSyncResult

logger = logging.getLogger(__name__)


# ── 声明式配置 ─────────────────────────────────────────────────


# 船舶信息 (基础)
_VESSEL_INFO: list[FieldMapping] = [
    FieldMapping("VesselIn", "VesselIn"),
    FieldMapping("InVoyage", "InVoyage"),
    FieldMapping("PortOfDischarge", "PortOfDischarge"),
]

# 码头/ETA 信息
_TERMINAL_INFO: list[FieldMapping] = [
    FieldMapping("Terminal Full Name", "Terminal Full Name"),
    FieldMapping("EstimatedArrival", "EstimatedArrival"),
]

# 船期/可用性 (1-Stop ImportAvailability)
_SCHEDULE_INFO: list[FieldMapping] = [
    FieldMapping("ImportAvailability", "ImportAvailability"),
    FieldMapping("StorageStartDate", "StorageStartDate"),
]

# 货物详情
_CARGO_INFO: list[FieldMapping] = [
    FieldMapping("ISO", "ISO"),
    FieldMapping("CommodityIn", "CommodityIn"),
    FieldMapping("Gross Weight", "Gross Weight"),
]

# 在船状态
_ON_BOARD: list[FieldMapping] = [
    FieldMapping("ON_BOARD_VESSEL", "ON_BOARD_VESSEL"),
    FieldMapping("ON_BOARD_VESSEL_Time", "ON_BOARD_VESSEL_Time"),
]

# 卸船状态
_DISCHARGE: list[FieldMapping] = [
    FieldMapping("DISCHARGE", "DISCHARGE"),
    FieldMapping("DISCHARGE_Time", "DISCHARGE_Time"),
]

# 提柜状态
_GATEOUT: list[FieldMapping] = [
    FieldMapping("GATEOUT", "GATEOUT"),
    FieldMapping("GATEOUT_Time", "GATEOUT_Time"),
]


# ── 客户端筛选 ──────────────────────────────────────────────


def _parse_bitable_datetime(value: str) -> datetime | None:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(value, fmt)
            return dt.replace(tzinfo=UTC)
        except (ValueError, OSError):
            continue
    return None


def _eta_passed(record: dict[str, Any]) -> bool:
    """ETA 已过 (早于当前 UTC 时间) — Bitable filter_expr 无法表达。"""
    eta_str = extract_cell_text(record.get("EstimatedArrival"))
    if not eta_str:
        return False
    eta = _parse_bitable_datetime(eta_str)
    return eta is not None and eta < datetime.now(UTC)


# ── 条件定义 ──────────────────────────────────────────────────

CONTAINER_BATCH_CONDITIONS: dict[str, BatchCondition] = {
    # ─ basic ───────────────────────────────────────────────
    # 筛选: VesselIn/InVoyage/PortOfDischarge 任一为空
    # 写回: 船舶信息 + 码头/ETA + 船期 + 货物 + 在船/卸船/提柜 (全量)
    "basic": BatchCondition(
        name="basic",
        description="VesselIn/InVoyage/PortOfDischarge 任一为空",
        query=BitableQuery().any_empty(["VesselIn", "InVoyage", "PortOfDischarge"]),
        write_fields=[
            *_VESSEL_INFO,
            *_TERMINAL_INFO,
            *_SCHEDULE_INFO,
            *_CARGO_INFO,
            *_ON_BOARD,
            *_DISCHARGE,
            *_GATEOUT,
        ],
    ),
    # ─ terminal ────────────────────────────────────────────
    # 筛选: 船舶信息完整，但 Terminal/ETA 为空
    # 写回: 码头/ETA + 船期 + 货物 + 在船/卸船/提柜
    "terminal": BatchCondition(
        name="terminal",
        description="船舶信息完整，Terminal/ETA 为空",
        query=BitableQuery()
        .not_empty("VesselIn")
        .not_empty("InVoyage")
        .not_empty("PortOfDischarge")
        .any_empty(["Terminal Full Name", "EstimatedArrival"]),
        write_fields=[*_TERMINAL_INFO, *_SCHEDULE_INFO, *_CARGO_INFO, *_ON_BOARD, *_DISCHARGE, *_GATEOUT],
    ),
    # ─ vessel_schedule ─────────────────────────────────────
    # 筛选: 码头/ETA 已有，但 ImportAvailability/StorageStartDate 为空
    # 写回: 船期 + 在船/卸船/提柜
    "vessel_schedule": BatchCondition(
        name="vessel_schedule",
        description="码头/ETA 已有，ImportAvailability/StorageStartDate 为空",
        query=BitableQuery()
        .not_empty("VesselIn")
        .not_empty("InVoyage")
        .not_empty("PortOfDischarge")
        .not_empty("Terminal Full Name")
        .not_empty("EstimatedArrival")
        .any_empty(["ImportAvailability", "StorageStartDate"]),
        write_fields=[*_SCHEDULE_INFO, *_ON_BOARD, *_DISCHARGE, *_GATEOUT],
    ),
    # ─ discharge ───────────────────────────────────────────
    # 筛选: ETA 已过，DISCHARGE_Time 为空
    # 写回: 卸船状态 + 提柜状态
    "discharge": BatchCondition(
        name="discharge",
        description="ETA 已过，DISCHARGE_Time 为空",
        query=BitableQuery()
        .not_empty("VesselIn")
        .not_empty("InVoyage")
        .not_empty("PortOfDischarge")
        .not_empty("Terminal Full Name")
        .not_empty("EstimatedArrival")
        .is_empty("DISCHARGE_Time")
        .client_filter(_eta_passed),
        write_fields=[*_DISCHARGE, *_GATEOUT],
    ),
    # ─ gateout ─────────────────────────────────────────────
    # 筛选: 已卸船，GATEOUT_Time 为空
    # 写回: 提柜状态
    "gateout": BatchCondition(
        name="gateout",
        description="已卸船，GATEOUT_Time 为空",
        query=BitableQuery()
        .not_empty("VesselIn")
        .not_empty("InVoyage")
        .not_empty("PortOfDischarge")
        .not_empty("Terminal Full Name")
        .not_empty("EstimatedArrival")
        .not_empty("DISCHARGE_Time")
        .is_empty("GATEOUT_Time")
        .client_filter(_eta_passed),
        write_fields=[*_GATEOUT],
    ),
    # ─ all ─────────────────────────────────────────────────
    # 筛选: 全部记录
    # 写回: 全量
    "all": BatchCondition(
        name="all",
        description="全部记录",
        query=BitableQuery(),
        write_fields=[
            *_VESSEL_INFO,
            *_TERMINAL_INFO,
            *_SCHEDULE_INFO,
            *_CARGO_INFO,
            *_ON_BOARD,
            *_DISCHARGE,
            *_GATEOUT,
        ],
    ),
}


# ── Service ────────────────────────────────────────────────────


class ContainerSyncService:
    """集装箱港口数据同步服务。

    流程: Bitable 筛选 → 1-Stop 查询 → 写回 Bitable
    """

    def __init__(
        self,
        import_repo: ImportRepository | None = None,
        onestop: OneStopProvider | None = None,
    ) -> None:
        self._repo = import_repo or ImportRepository()
        self._onestop = onestop or OneStopProvider.get_instance()
        self._link_resolver = LinkResolver()

    @staticmethod
    def list_conditions() -> list[dict[str, str]]:
        return [{"name": c.name, "description": c.description} for c in CONTAINER_BATCH_CONDITIONS.values()]

    async def sync(self, container_numbers: list[str]) -> ContainerBatchSyncResult:
        """按柜号列表同步（手动触发）。"""
        if not container_numbers:
            return ContainerBatchSyncResult()

        container_data = await self._fetch_from_onestop(container_numbers)
        cn_to_record_id = await self._find_import_record_ids(container_numbers)

        cond = CONTAINER_BATCH_CONDITIONS["all"]
        return await self._write_back(container_data, cn_to_record_id, container_numbers, cond.write_fields)

    async def sync_batch(self, condition: str = "basic") -> ContainerBatchSyncResult:
        """按条件筛选 Op-Import 记录 → 查 1-Stop → 写回。"""
        cond = CONTAINER_BATCH_CONDITIONS.get(condition)
        if cond is None:
            available = ", ".join(CONTAINER_BATCH_CONDITIONS.keys())
            raise ValueError(f"未知条件 '{condition}'，可用条件: {available}")

        filter_expr = cond.query.build()
        all_records = await self._repo.list_all_records(filter_expr=filter_expr)
        pending = cond.query.filter(all_records)

        logger.info("集装箱批量同步 [%s]: %d 条", condition, len(pending))

        container_numbers = [cn for r in pending if (cn := extract_cell_text(r.get("Container Number")))]

        if not container_numbers:
            return ContainerBatchSyncResult()

        container_data = await self._fetch_from_onestop(container_numbers)
        cn_to_record_id = {cn: r["record_id"] for r in pending if (cn := extract_cell_text(r.get("Container Number")))}

        return await self._write_back(container_data, cn_to_record_id, container_numbers, cond.write_fields)

    # ── 写回 ──────────────────────────────────────────────────

    async def _write_back(
        self,
        container_data: dict,
        cn_to_record_id: dict[str, str],
        container_numbers: list[str],
        write_fields: list[FieldMapping],
    ) -> ContainerBatchSyncResult:
        updates: list[dict[str, Any]] = []
        results: list[ContainerSyncResult] = []

        for cn in container_numbers:
            data = container_data.get(cn)
            if not data:
                results.append(ContainerSyncResult(container_number=cn, error="1-Stop 无数据"))
                continue

            fields = await build_update_fields(data, write_fields, self._link_resolver)
            if not fields:
                results.append(ContainerSyncResult(container_number=cn, raw=data))
                continue

            record_id = cn_to_record_id.get(cn)
            if not record_id:
                results.append(ContainerSyncResult(container_number=cn, error="Op-Import 中未找到该柜号", raw=data))
                continue

            updates.append({"record_id": record_id, "fields": fields})
            results.append(ContainerSyncResult(container_number=cn, updated_fields=list(fields.keys())))

        synced, errors = await batch_write_back(self._repo, updates)
        logger.info("集装箱同步完成: %d 成功 / %d 失败", synced, errors)
        return ContainerBatchSyncResult(total=len(container_numbers), synced=synced, errors=errors, details=results)

    # ── 数据获取 ──────────────────────────────────────────────

    async def _fetch_from_onestop(self, container_numbers: list[str]) -> dict:
        return await self._onestop.match_containers_info_by_list(container_numbers)

    # ── 工具方法 ──────────────────────────────────────────────

    async def _find_import_record_ids(self, container_numbers: list[str]) -> dict[str, str]:
        result: dict[str, str] = {}
        cn_set = set(container_numbers)
        all_records = await self._repo.list_all_records(field_names=["Container Number"])
        for r in all_records:
            cn = extract_cell_text(r.get("Container Number"))
            if cn and cn in cn_set:
                result[cn] = r["record_id"]
        return result

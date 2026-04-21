from __future__ import annotations

import logging
from typing import Any

from app.common.bitable_query import BitableQuery
from app.common.lark_tables import T
from app.component.OneStopProvider import OneStopProvider
from app.core.lark_bitable_value import extract_cell_text
from app.repository.vessel_schedule import VesselScheduleRepository
from app.service.sync.base import (
    BatchCondition,
    FieldMapping,
    LinkConfig,
    LinkResolver,
    batch_write_back,
    build_update_fields,
)
from app.service.sync.model.vessel_sync_schemas import VesselBatchSyncResult, VesselSyncResult

logger = logging.getLogger(__name__)


# ── 声明式配置 ─────────────────────────────────────────────────


# 船期时间类 (1-Stop → Bitable, 全部 datetime)
_DATETIME_FIELDS: list[FieldMapping] = [
    FieldMapping("ETA", "ETA"),
    FieldMapping("ETD", "ETD"),
    FieldMapping("First Free", "First Free"),
    FieldMapping("Last Free", "Last Free"),
    FieldMapping("Export Start", "Export Start"),
    FieldMapping("Export Cutoff", "Export Cutoff"),
]

# Actual Arrival 是 text/select
_ACTUAL_ARRIVAL = FieldMapping("Actual Arrival", "Actual Arrival")

# Terminal Name → 关联 MD-Terminal, 按 Terminal Full Name 查找
_TERMINAL_NAME = FieldMapping(
    "Terminal Full Name",
    "Terminal Name",
    link=LinkConfig(table=T.md_terminal, search_field="Terminal Full Name"),
)

# 所有条件的默认写回字段集
_ALL_WRITE_FIELDS = [*_DATETIME_FIELDS, _ACTUAL_ARRIVAL, _TERMINAL_NAME]


# ── 条件定义 ──────────────────────────────────────────────────

BATCH_CONDITIONS: dict[str, BatchCondition] = {
    # ─ pending_arrival ─────────────────────────────────────
    # 筛选: Actual Arrival 不为 Y 或 SP (含空值)
    # 写回: 全部船期字段 + Actual Arrival + Terminal
    "pending_arrival": BatchCondition(
        name="pending_arrival",
        description="Actual Arrival 不为 Y 或 SP (含空值)",
        query=BitableQuery().not_in_or_empty("Actual Arrival", ["Y", "SP"]),
        write_fields=_ALL_WRITE_FIELDS,
    ),
    # ─ missing_eta ─────────────────────────────────────────
    # 筛选: ETA 为空
    # 写回: 全部船期字段 + Actual Arrival + Terminal
    "missing_eta": BatchCondition(
        name="missing_eta",
        description="ETA 为空",
        query=BitableQuery().is_empty("ETA"),
        write_fields=_ALL_WRITE_FIELDS,
    ),
    # ─ all ─────────────────────────────────────────────────
    # 筛选: 全部记录
    # 写回: 全部船期字段 + Actual Arrival + Terminal
    "all": BatchCondition(
        name="all",
        description="全部记录",
        query=BitableQuery(),
        write_fields=_ALL_WRITE_FIELDS,
    ),
}


# ── Service ────────────────────────────────────────────────────


class VesselSyncService:
    """船期实时数据同步服务。

    流程: Bitable 筛选 → 1-Stop 查询 → 写回 Bitable
    """

    def __init__(
        self,
        vessel_schedule_repo: VesselScheduleRepository | None = None,
        onestop: OneStopProvider | None = None,
    ) -> None:
        self._repo = vessel_schedule_repo or VesselScheduleRepository()
        self._onestop = onestop or OneStopProvider.get_instance()
        self._link_resolver = LinkResolver()

    @staticmethod
    def list_conditions() -> list[dict[str, str]]:
        return [{"name": c.name, "description": c.description} for c in BATCH_CONDITIONS.values()]

    async def sync_single(self, record_id: str) -> VesselSyncResult:
        record = await self._repo.get_record(record_id)
        vessel_name, voyage, base_node = self._parse_record(record)

        if not vessel_name:
            raise ValueError(f"记录 {record_id} 缺少 Vessel Name")
        if not base_node:
            raise ValueError(f"记录 {record_id} 缺少 Base Node")

        vessel_data = await self._fetch_from_onestop(vessel_name, voyage, base_node)
        if not self._has_valid_data(vessel_data):
            return VesselSyncResult(record_id=record_id, raw=vessel_data)

        cond = BATCH_CONDITIONS["all"]
        fields = await build_update_fields(vessel_data, cond.write_fields, self._link_resolver)
        if not fields:
            return VesselSyncResult(record_id=record_id, raw=vessel_data)

        await self._repo.update_record(record_id, fields)
        logger.info("记录 %s 已更新: %s", record_id, list(fields.keys()))
        return VesselSyncResult(record_id=record_id, updated_fields=list(fields.keys()), raw=vessel_data)

    async def sync_batch(
        self,
        condition: str = "pending_arrival",
        base_node: str | None = None,
    ) -> VesselBatchSyncResult:
        cond = BATCH_CONDITIONS.get(condition)
        if cond is None:
            available = ", ".join(BATCH_CONDITIONS.keys())
            raise ValueError(f"未知条件 '{condition}'，可用条件: {available}")

        filter_expr = cond.query.build()
        all_records = await self._repo.list_all_records(filter_expr=filter_expr)
        pending = cond.query.filter(all_records)

        if base_node:
            pending = [r for r in pending if self._extract_base_node(r.get("Base Node")) == base_node]

        logger.info("批量同步 [%s]: %d 条", condition, len(pending))

        grouped = self._group_by_vessel_key(pending)

        vessel_data_map: dict[tuple[str, str | None, str], dict | None] = {}
        for key in grouped:
            vn, vy, bn = key
            try:
                vessel_data_map[key] = await self._fetch_from_onestop(vn, vy, bn)
            except Exception as e:
                logger.error("查询 1-Stop 失败 %s: %s", vn, e)
                vessel_data_map[key] = None

        updates: list[dict[str, Any]] = []
        results: list[VesselSyncResult] = []

        for (vn, vy, bn), records in grouped.items():
            vessel_data = vessel_data_map.get((vn, vy, bn))
            if not vessel_data or not self._has_valid_data(vessel_data):
                for r in records:
                    results.append(VesselSyncResult(record_id=r["record_id"], error="1-Stop 无有效数据"))
                continue

            fields = await build_update_fields(vessel_data, cond.write_fields, self._link_resolver)
            if not fields:
                for r in records:
                    results.append(VesselSyncResult(record_id=r["record_id"]))
                continue

            for r in records:
                updates.append({"record_id": r["record_id"], "fields": fields})
                results.append(VesselSyncResult(record_id=r["record_id"], updated_fields=list(fields.keys())))

        synced, errors = await batch_write_back(self._repo, updates)

        logger.info("批量同步完成: %d 成功 / %d 失败", synced, errors)
        return VesselBatchSyncResult(total=len(pending), synced=synced, errors=errors, details=results)

    # ── 数据获取 ──────────────────────────────────────────────

    async def _fetch_from_onestop(self, vessel_name: str, voyage: str | None, base_node: str) -> dict | None:
        onestop_result = await self._onestop.vessel_search_by_name_list(
            vessel_map_dict={vessel_name: (vessel_name, voyage)},
            base_node=base_node,
        )
        return onestop_result.get(vessel_name)

    # ── 工具方法 ──────────────────────────────────────────────

    @staticmethod
    def _parse_record(record: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
        vessel_name = extract_cell_text(record.get("Vessel Name"))
        voyage = extract_cell_text(record.get("Voyage"))
        base_node = VesselSyncService._extract_base_node(record.get("Base Node"))
        return vessel_name, voyage, base_node

    @staticmethod
    def _extract_base_node(base_node_field: object) -> str | None:
        text = extract_cell_text(base_node_field)
        if not text:
            return None
        mapping = {
            "SYDNEY": "PORT OF SYDNEY",
            "MELBOURNE": "PORT OF MELBOURNE",
        }
        upper = text.upper().strip()
        return mapping.get(upper, upper)

    @staticmethod
    def _group_by_vessel_key(
        records: list[dict[str, Any]],
    ) -> dict[tuple[str, str | None, str], list[dict[str, Any]]]:
        grouped: dict[tuple[str, str | None, str], list[dict[str, Any]]] = {}
        for r in records:
            vessel_name, voyage, base_node = VesselSyncService._parse_record(r)
            if not vessel_name or not base_node:
                continue
            key = (vessel_name, voyage, base_node)
            grouped.setdefault(key, []).append(r)
        return grouped

    @staticmethod
    def _has_valid_data(vessel_data: dict | None) -> bool:
        if not vessel_data:
            return False
        return bool(vessel_data.get("ETA") or vessel_data.get("ETD"))

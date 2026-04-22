from __future__ import annotations

import logging
from typing import Any

from app.common.assert_utils import assert_in, assert_not_blank
from app.common.query_wrapper import QueryWrapper
from app.component.OneStopProvider import OneStopProvider
from app.repository.vessel_schedule import VesselScheduleRepository
from app.service.sync.constants.vessel_constants import (
    _BASE_NODE_MAP,
    _CONDITIONS,
    _KEY_SEP,
    _TERMINAL_LINK,
)
from app.service.sync.workflow.batch_sync_result import BatchSyncResult
from app.service.sync.scene.vessel.vessel_data import VesselData
from app.service.sync.utils.datetime_parser import safe_ts
from app.service.sync.utils.link_resolver import LinkResolver
from app.service.sync.workflow.sync_template import SyncTemplate

logger = logging.getLogger(__name__)


class VesselSyncService(SyncTemplate):
    """船期实时数据同步服务（模板模式）。

    Step 1: 按 condition 从 Op-Vessel Schedule 筛选记录
    Step 2: 按 (Vessel Name, Voyage, Base Node) 聚合，每组只查一次 1-Stop
            Terminal Name 通过 LinkResolver 解析为 record_id
            datetime 字段转为毫秒时间戳
    Step 3: 构建 UpdateWrapper，写回 Bitable
    """

    def __init__(
        self,
        vessel_schedule_repo: VesselScheduleRepository | None = None,
        onestop: OneStopProvider | None = None,
    ) -> None:
        self._repo = vessel_schedule_repo or VesselScheduleRepository()
        self._onestop = onestop or OneStopProvider.get_instance()
        self._link_resolver = LinkResolver()

    @property
    def repository(self) -> VesselScheduleRepository:
        return self._repo

    @staticmethod
    def list_conditions() -> list[str]:
        return list(_CONDITIONS.keys())

    # ── Step 1 ──────────────────────────────────────────────

    async def fetch_records(self, condition: str, base_node: str | None = None) -> list[dict]:
        query = assert_in(condition, _CONDITIONS, f"未知条件 '{condition}'，可用: {', '.join(_CONDITIONS)}")

        all_records = await self._repo.list(query)

        if base_node:
            all_records = [r for r in all_records if _extract_base_node(r.get("Base Node")) == base_node]

        logger.info("船期批量同步 [%s]: %d 条", condition, len(all_records))
        return all_records

    # ── Step 2 ──────────────────────────────────────────────

    async def fetch_provider_data(self, records: list[dict]) -> list[VesselData]:
        """按 vessel key 聚合查询，每组共享一次 1-Stop 结果。"""
        grouped = _group_by_vessel_key(records)

        vessel_data_map: dict[str, dict | None] = {}
        for key, group_records in grouped.items():
            vessel_name, voyage, base_node = _split_key(key)
            try:
                raw = await self._onestop.vessel_search_by_name_list(
                    vessel_map_dict={vessel_name: (vessel_name, voyage)},
                    base_node=base_node,
                )
                vessel_data_map[key] = raw.get(vessel_name)
            except Exception as e:
                logger.error("1-Stop 查询失败 [%s]: %s", vessel_name, e)
                vessel_data_map[key] = None

        result: list[VesselData] = []
        for key, group_records in grouped.items():
            raw = vessel_data_map.get(key)
            if not raw or not (raw.get("ETA") or raw.get("ETD")):
                continue

            terminal_name_id = await self._resolve_terminal_link(raw)

            for r in group_records:
                result.append(
                    VesselData(
                        record_id=r["record_id"],
                        vessel_key=key,
                        eta=safe_ts(raw, "ETA"),
                        etd=safe_ts(raw, "ETD"),
                        first_free=safe_ts(raw, "First Free"),
                        last_free=safe_ts(raw, "Last Free"),
                        export_start=safe_ts(raw, "Export Start"),
                        export_cutoff=safe_ts(raw, "Export Cutoff"),
                        actual_arrival=raw.get("Actual Arrival") or None,
                        terminal_name=terminal_name_id,
                    )
                )
        return result

    async def _resolve_terminal_link(self, raw: dict[str, Any]) -> list[str] | None:
        tfn = raw.get("Terminal Full Name")
        if not tfn:
            return None
        record_id = await self._link_resolver.resolve(_TERMINAL_LINK, str(tfn))
        return [record_id] if record_id else None

    # ── 对外接口 ─────────────────────────────────────────────

    async def sync_single(self, record_id: str) -> BatchSyncResult:
        """手动触发：同步单条船期记录。"""
        record = await self._repo.findOne(QueryWrapper().eq("record_id", record_id))
        vessel_name = record.get("Vessel Name")
        voyage = record.get("Voyage")
        base_node = _extract_base_node(record.get("Base Node"))

        assert_not_blank(vessel_name, f"记录 {record_id} 缺少 Vessel Name")
        assert_not_blank(base_node, f"记录 {record_id} 缺少 Base Node")

        try:
            raw_map = await self._onestop.vessel_search_by_name_list(
                vessel_map_dict={vessel_name: (vessel_name, voyage)},
                base_node=base_node,
            )
            raw = raw_map.get(vessel_name)
        except Exception as e:
            logger.error("船期单条同步失败 %s: %s", record_id, e)
            return BatchSyncResult(total=1, errors=1)

        if not raw or not (raw.get("ETA") or raw.get("ETD")):
            return BatchSyncResult(total=1)

        terminal_name_id = await self._resolve_terminal_link(raw)
        vessel_data = VesselData(
            record_id=record_id,
            vessel_key=vessel_name,
            eta=safe_ts(raw, "ETA"),
            etd=safe_ts(raw, "ETD"),
            first_free=safe_ts(raw, "First Free"),
            last_free=safe_ts(raw, "Last Free"),
            export_start=safe_ts(raw, "Export Start"),
            export_cutoff=safe_ts(raw, "Export Cutoff"),
            actual_arrival=raw.get("Actual Arrival") or None,
            terminal_name=terminal_name_id,
        )

        if not vessel_data.has_fields():
            return BatchSyncResult(total=1)

        wrapper = vessel_data.to_update_wrapper()
        await self._repo.updateOne(wrapper)
        logger.info("船期单条同步 %s", record_id)
        return BatchSyncResult(total=1, synced=1)

    async def sync_batch(
        self,
        condition: str = "pending_arrival",
        base_node: str | None = None,
    ) -> BatchSyncResult:
        records = await self.fetch_records(condition, base_node=base_node)
        if not records:
            return BatchSyncResult()
        data_list = await self.fetch_provider_data(records)
        wrappers = self.build_update_wrappers(data_list)
        return await self._persist(wrappers)


# ── 工具函数 ──────────────────────────────────────────────────


def _extract_base_node(base_node_field: object) -> str | None:
    if not base_node_field:
        return None
    upper = str(base_node_field).upper().strip()
    return _BASE_NODE_MAP.get(upper, upper)


def _make_key(vessel_name: str, voyage: str | None, base_node: str) -> str:
    return f"{vessel_name}{_KEY_SEP}{voyage or ''}{_KEY_SEP}{base_node}"


def _split_key(key: str) -> tuple[str, str | None, str]:
    parts = key.split(_KEY_SEP, 2)
    return parts[0], parts[1] or None, parts[2]


def _group_by_vessel_key(records: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for r in records:
        vessel_name = r.get("Vessel Name")
        voyage = r.get("Voyage")
        base_node = _extract_base_node(r.get("Base Node"))
        if not vessel_name or not base_node:
            continue
        key = _make_key(vessel_name, voyage, base_node)
        grouped.setdefault(key, []).append(r)
    return grouped

from __future__ import annotations

import logging
from typing import Any

from app.common.assert_utils import assert_in
from app.common.collection_utils import filter_by, pluck, to_map
from app.core.lark_bitable_value import extract_link_record_ids
from app.component.OneStopProvider import OneStopProvider
from app.common.query_wrapper import QueryWrapper
from app.common.lark_tables import T
from app.repository.base_node import BaseNodeRepository
from app.repository.dt_commodity import DTCommodityRepository
from app.repository.dt_container_type import DTContainerTypeRepository
from app.repository.import_ import ImportRepository
from app.repository.terminal import TerminalRepository
from app.repository.vessel_schedule import VesselScheduleRepository
from app.service.sync.constants.container_constants import _CONDITIONS
from app.service.sync.utils.link_config import LinkConfig
from app.service.sync.utils.link_resolver import LinkResolver, build_select_field_map
from app.service.sync.workflow.batch_sync_result import BatchSyncResult
from app.service.sync.scene.container.container_data import ContainerData
from app.service.sync.utils.datetime_parser import safe_ts
from app.service.sync.workflow.sync_template import SyncTemplate

logger = logging.getLogger(__name__)

_BASE_NODE_LINK = LinkConfig(table=T.md_base_node, search_field="Base Node")


class ContainerSyncService(SyncTemplate):
    """集装箱港口数据同步服务（模板模式）。"""

    def __init__(
        self,
        import_repo: ImportRepository | None = None,
        onestop: OneStopProvider | None = None,
        vessel_schedule_repo: VesselScheduleRepository | None = None,
        base_node_repo: BaseNodeRepository | None = None,
        dt_container_type_repo: DTContainerTypeRepository | None = None,
        dt_commodity_repo: DTCommodityRepository | None = None,
        terminal_repo: TerminalRepository | None = None,
    ) -> None:
        self._repo = import_repo or ImportRepository()
        self._onestop = onestop or OneStopProvider.get_instance()
        self._vessel_schedule_repo = vessel_schedule_repo or VesselScheduleRepository()
        self._base_node_repo = base_node_repo or BaseNodeRepository()
        self._dt_ct_repo = dt_container_type_repo or DTContainerTypeRepository()
        self._dt_comm_repo = dt_commodity_repo or DTCommodityRepository()
        self._terminal_repo = terminal_repo or TerminalRepository()
        self._link_resolver = LinkResolver()

    @property
    def repository(self) -> ImportRepository:
        return self._repo

    @staticmethod
    def list_conditions() -> list[str]:
        return list(_CONDITIONS.keys())

    # ── Step 1 ──────────────────────────────────────────────

    async def fetch_records(self, condition: str) -> list[dict]:
        query = assert_in(condition, _CONDITIONS, f"未知条件 '{condition}'，可用: {', '.join(_CONDITIONS)}")
        all_records = await self._repo.list(query)
        logger.info("集装箱批量同步 [%s]: %d 条", condition, len(all_records))
        return all_records

    # ── Step 2 ──────────────────────────────────────────────

    async def fetch_provider_data(self, records: list[dict]) -> list[ContainerData]:
        cns = pluck(records, "Container Number")
        if not cns:
            return []

        cn_to_rid = to_map(records, "Container Number")
        raw_data = await self._onestop.match_containers_info_by_list(cns)

        vessel_schedule_map = await self._build_vessel_schedule_map()
        iso_to_ct = await build_select_field_map(self._dt_ct_repo, "ISO")
        comm_in_to_commodity = await build_select_field_map(self._dt_comm_repo, "CommodityIn")
        tfn_to_terminal = await build_select_field_map(self._terminal_repo, "Terminal Full Name")

        result: list[ContainerData] = []
        for cn in cns:
            rid = cn_to_rid.get(cn)
            raw = raw_data.get(cn)
            if not rid or not raw:
                continue
            result.append(await self._parse(
                rid, cn, raw, vessel_schedule_map, iso_to_ct, comm_in_to_commodity, tfn_to_terminal,
            ))
        return result

    async def _build_vessel_schedule_map(self) -> dict[str, str]:
        """构建 (Vessel Name|Voyage|Base Node) → record_id 映射。"""
        vs_records = await self._vessel_schedule_repo.list(QueryWrapper())

        all_bn_ids: set[str] = set()
        for r in vs_records:
            all_bn_ids.update(extract_link_record_ids(r.get("Base Node")))

        if all_bn_ids:
            bn_records = await self._base_node_repo.list(
                QueryWrapper().in_list("record_id", list(all_bn_ids)).select("Base Node")
            )
            bn_id_to_name = to_map(bn_records, "record_id", "Base Node")
        else:
            bn_id_to_name = {}

        result: dict[str, str] = {}
        for r in vs_records:
            vessel_name = (r.get("Vessel Name") or "").strip().upper()
            voyage = (r.get("Voyage") or "").strip().upper()
            bn_ids = extract_link_record_ids(r.get("Base Node"))
            base_node = bn_id_to_name.get(bn_ids[0], "") if bn_ids else ""
            base_node = base_node.strip().upper()
            if vessel_name and base_node:
                key = f"{vessel_name}|{voyage}|{base_node}"
                result[key] = r["record_id"]
        return result

    async def _parse(
        self, record_id: str, container_number: str, raw: dict[str, Any],
        vessel_schedule_map: dict[str, str], iso_to_ct: dict[str, str],
        comm_in_to_commodity: dict[str, str], tfn_to_terminal: dict[str, str],
    ) -> ContainerData:
        def _str(key: str) -> str | None:
            v = raw.get(key)
            return str(v) if v else None

        def _float(key: str) -> float | None:
            v = raw.get(key)
            try:
                return float(v) if v else None
            except (ValueError, TypeError):
                return None

        pod_text = _str("PortOfDischarge")
        vessel_in = _str("VesselIn")
        in_voyage = _str("InVoyage")
        iso_val = _str("ISO")
        tfn_val = _str("Terminal Full Name")

        pod_record_id = await self._link_resolver.resolve(_BASE_NODE_LINK, pod_text) if pod_text else None
        port_of_discharge = [pod_record_id] if pod_record_id else None

        full_vessel_in: list[str] | None = None
        if vessel_in and pod_text:
            key = f"{vessel_in.strip().upper()}|{(in_voyage or '').strip().upper()}|{pod_text.strip().upper()}"
            vs_rid = vessel_schedule_map.get(key)
            if vs_rid:
                full_vessel_in = [vs_rid]

        terminal_name: list[str] | None = None
        if tfn_val:
            t_rid = tfn_to_terminal.get(tfn_val.strip().upper())
            if t_rid:
                terminal_name = [t_rid]

        container_type: list[str] | None = None
        if iso_val:
            ct_rid = iso_to_ct.get(iso_val.strip().upper())
            if ct_rid:
                container_type = [ct_rid]

        commodity_in_val = _str("CommodityIn")
        commodity: list[str] | None = None
        if commodity_in_val:
            comm_rid = comm_in_to_commodity.get(commodity_in_val.strip().upper())
            if comm_rid:
                commodity = [comm_rid]

        gross_weight = _float("Gross Weight")
        estimated_arrival = safe_ts(raw, "EstimatedArrival")
        import_availability = safe_ts(raw, "ImportAvailability")
        storage_start_date = safe_ts(raw, "StorageStartDate")

        return ContainerData(
            record_id=record_id,
            container_number=container_number,
            vessel_in=vessel_in,
            in_voyage=in_voyage,
            port_of_discharge=port_of_discharge,
            full_vessel_in=full_vessel_in,
            full_vessel_name=full_vessel_in,
            terminal_full_name=tfn_val,
            terminal_name=terminal_name,
            estimated_arrival=estimated_arrival,
            eta=estimated_arrival,
            import_availability=import_availability,
            first_free=import_availability,
            storage_start_date=storage_start_date,
            last_free=storage_start_date,
            iso=iso_val,
            commodity_in=commodity_in_val,
            gross_weight=gross_weight,
            container_type=container_type,
            commodity=commodity,
            container_weight=gross_weight,
            on_board_vessel=_str("ON_BOARD_VESSEL"),
            on_board_vessel_time=safe_ts(raw, "ON_BOARD_VESSEL_Time"),
            discharge=_str("DISCHARGE"),
            discharge_time=safe_ts(raw, "DISCHARGE_Time"),
            gateout=_str("GATEOUT"),
            gateout_time=safe_ts(raw, "GATEOUT_Time"),
        )

    # ── 对外接口 ─────────────────────────────────────────────

    async def sync(self, container_numbers: list[str]) -> BatchSyncResult:
        """手动触发：按柜号列表同步。"""
        if not container_numbers:
            return BatchSyncResult()

        all_records = await self._repo.list(QueryWrapper().select("Container Number"))
        records = filter_by(all_records, "Container Number", container_numbers)
        if not records:
            return BatchSyncResult(total=len(container_numbers))

        data_list = await self.fetch_provider_data(records)
        wrappers = self.build_update_wrappers(data_list)
        return await self._persist(wrappers)

    async def sync_batch(self, condition: str = "basic") -> BatchSyncResult:
        return await self.run_batch(condition)

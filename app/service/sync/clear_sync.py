from __future__ import annotations

import logging
from typing import Any

from app.common.bitable_query import BitableQuery
from app.component.HutchisonPortsProvider import HutchisonPortsProvider
from app.component.OneStopProvider import OneStopProvider
from app.core.lark_bitable_value import extract_cell_text
from app.repository.import_ import ImportRepository
from app.service.sync.base import (
    FieldMapping,
    LinkResolver,
    MultiProviderBatchCondition,
    batch_write_back,
    build_update_fields,
)
from app.service.sync.model.clear_sync_schemas import ClearBatchSyncResult, ClearSyncResult

logger = logging.getLogger(__name__)

_HUTCHISON_TERMINAL = "HUTCHISON PORTS - PORT BOTANY"

_CLEAR_FINAL_STATUSES = ["CLEAR", "UNDERBOND APPROVAL", "RELEASED"]


# ── 声明式配置 ─────────────────────────────────────────────────


# 1-Stop customs 返回: Clear Status + Quarantine
_ONESTOP_CUSTOMS_FIELDS: list[FieldMapping] = [
    FieldMapping("Clear Status", "Clear Status"),
    FieldMapping("Quarantine", "Quarantine"),
]

# Hutchison 返回: Clear Status + Quarantine + ISO + Gross Weight
_HUTCHISON_FIELDS: list[FieldMapping] = [
    FieldMapping("Clear Status", "Clear Status"),
    FieldMapping("Quarantine", "Quarantine"),
    FieldMapping("ISO", "ISO"),
    FieldMapping("Gross Weight", "Gross Weight"),
]


# ── 条件定义 ──────────────────────────────────────────────────

CLEAR_BATCH_CONDITIONS: dict[str, MultiProviderBatchCondition] = {
    # ─ pending ──────────────────────────────────────────────
    # 筛选: Terminal Full Name 非空, 且 Clear Status 未完结 (非 CLEAR/UNDERBOND APPROVAL/RELEASED, 含空值)
    # 写回: 1-Stop → Clear Status + Quarantine; Hutchison → Clear Status + Quarantine + ISO + Gross Weight
    "pending": MultiProviderBatchCondition(
        name="pending",
        description="Terminal 不为空且 Clear Status 未完结（非 CLEAR/UNDERBOND APPROVAL/RELEASED，含空值）",
        query=BitableQuery().not_empty("Terminal Full Name").not_in_or_empty("Clear Status", _CLEAR_FINAL_STATUSES),
        write_fields={
            "1-Stop customs": _ONESTOP_CUSTOMS_FIELDS,
            "Hutchison": _HUTCHISON_FIELDS,
        },
    ),
    # ─ all ──────────────────────────────────────────────────
    # 筛选: 全部记录
    # 写回: 同 pending, 按 Provider 分组
    "all": MultiProviderBatchCondition(
        name="all",
        description="全部记录",
        query=BitableQuery(),
        write_fields={
            "1-Stop customs": _ONESTOP_CUSTOMS_FIELDS,
            "Hutchison": _HUTCHISON_FIELDS,
        },
    ),
}


class ClearSyncService:
    """清关状态同步服务。

    根据 Terminal Full Name 选择 Provider:
    - 为空 → 先调 1-Stop customs，无数据则调 Hutchison
    - 非 HUTCHISON PORTS - PORT BOTANY → 只调 1-Stop customs
    - HUTCHISON PORTS - PORT BOTANY → 只调 Hutchison
    """

    def __init__(
        self,
        import_repo: ImportRepository | None = None,
        onestop: OneStopProvider | None = None,
        hutchison: HutchisonPortsProvider | None = None,
    ) -> None:
        self._repo = import_repo or ImportRepository()
        self._onestop = onestop or OneStopProvider.get_instance()
        self._hutchison = hutchison or HutchisonPortsProvider()
        self._link_resolver = LinkResolver()

    @staticmethod
    def list_conditions() -> list[dict[str, str]]:
        return [{"name": c.name, "description": c.description} for c in CLEAR_BATCH_CONDITIONS.values()]

    async def sync(
        self,
        container_numbers: list[str],
        terminal_full_name: str | None = None,
    ) -> ClearBatchSyncResult:
        """手动触发：按柜号 + Terminal 路由 Provider → 写回。"""
        if not container_numbers:
            return ClearBatchSyncResult()

        provider_data, provider_name = await self._fetch_by_terminal(
            container_numbers,
            terminal_full_name,
        )

        write_fields_map = CLEAR_BATCH_CONDITIONS["all"].write_fields
        field_mappings = write_fields_map.get(provider_name, _ONESTOP_CUSTOMS_FIELDS)

        cn_to_record_id = await self._find_import_record_ids(container_numbers)

        updates: list[dict[str, Any]] = []
        results: list[ClearSyncResult] = []

        for cn in container_numbers:
            data = provider_data.get(cn)
            if not data:
                results.append(
                    ClearSyncResult(container_number=cn, provider=provider_name, error=f"{provider_name} 无数据")
                )
                continue

            fields = await build_update_fields(data, field_mappings, self._link_resolver)
            if not fields:
                results.append(ClearSyncResult(container_number=cn, provider=provider_name, raw=data))
                continue

            record_id = cn_to_record_id.get(cn)
            if not record_id:
                results.append(
                    ClearSyncResult(
                        container_number=cn, provider=provider_name, error="Op-Import 中未找到该柜号", raw=data
                    )
                )
                continue

            updates.append({"record_id": record_id, "fields": fields})
            results.append(
                ClearSyncResult(container_number=cn, provider=provider_name, updated_fields=list(fields.keys()))
            )

        synced, errors = await batch_write_back(self._repo, updates)
        logger.info("清关同步 [%s]: %d 成功 / %d 失败", provider_name, synced, errors)
        return ClearBatchSyncResult(total=len(container_numbers), synced=synced, errors=errors, details=results)

    async def sync_batch(self, condition: str = "pending") -> ClearBatchSyncResult:
        """按条件筛选 Op-Import → 按 Terminal 路由 Provider → 写回。"""
        cond = CLEAR_BATCH_CONDITIONS.get(condition)
        if cond is None:
            available = ", ".join(CLEAR_BATCH_CONDITIONS.keys())
            raise ValueError(f"未知条件 '{condition}'，可用条件: {available}")

        filter_expr = cond.query.build()
        all_records = await self._repo.list_all_records(filter_expr=filter_expr)
        pending = cond.query.filter(all_records)

        logger.info("清关批量同步 [%s]: %d 条", condition, len(pending))

        hutchison_records: list[dict[str, Any]] = []
        other_records: list[dict[str, Any]] = []
        hutchison_key = _HUTCHISON_TERMINAL

        for r in pending:
            tfn = extract_cell_text(r.get("Terminal Full Name"))
            if tfn:
                tfn = tfn.strip().upper()
            if tfn == hutchison_key:
                hutchison_records.append(r)
            else:
                other_records.append(r)

        all_results: list[ClearSyncResult] = []
        total_synced = 0
        total_errors = 0

        if other_records:
            onestop_fields = cond.write_fields.get("1-Stop customs", _ONESTOP_CUSTOMS_FIELDS)
            synced, errors, results = await self._sync_record_group(other_records, "1-Stop customs", onestop_fields)
            total_synced += synced
            total_errors += errors
            all_results.extend(results)

        if hutchison_records:
            hutchison_fields = cond.write_fields.get("Hutchison", _HUTCHISON_FIELDS)
            synced, errors, results = await self._sync_record_group(hutchison_records, "Hutchison", hutchison_fields)
            total_synced += synced
            total_errors += errors
            all_results.extend(results)

        logger.info("清关批量同步完成: %d 成功 / %d 失败", total_synced, total_errors)
        return ClearBatchSyncResult(total=len(pending), synced=total_synced, errors=total_errors, details=all_results)

    async def _sync_record_group(
        self,
        records: list[dict[str, Any]],
        provider_name: str,
        field_mappings: list[FieldMapping],
    ) -> tuple[int, int, list[ClearSyncResult]]:
        """按一组 Op-Import 记录查同一个 Provider 并写回。"""
        container_numbers = [cn for r in records if (cn := extract_cell_text(r.get("Container Number")))]

        if provider_name == "1-Stop customs":
            provider_data = await self._onestop.customs_cargo_status_search(container_numbers)
        else:
            provider_data = await self._hutchison.container_enquiry_by_list(container_numbers)

        cn_to_record_id = {cn: r["record_id"] for r in records if (cn := extract_cell_text(r.get("Container Number")))}

        updates: list[dict[str, Any]] = []
        results: list[ClearSyncResult] = []

        for cn in container_numbers:
            data = provider_data.get(cn)
            if not data:
                results.append(
                    ClearSyncResult(container_number=cn, provider=provider_name, error=f"{provider_name} 无数据")
                )
                continue

            fields = await build_update_fields(data, field_mappings, self._link_resolver)
            if not fields:
                results.append(ClearSyncResult(container_number=cn, provider=provider_name, raw=data))
                continue

            record_id = cn_to_record_id.get(cn)
            if not record_id:
                results.append(
                    ClearSyncResult(
                        container_number=cn, provider=provider_name, error="Op-Import 中未找到该柜号", raw=data
                    )
                )
                continue

            updates.append({"record_id": record_id, "fields": fields})
            results.append(
                ClearSyncResult(container_number=cn, provider=provider_name, updated_fields=list(fields.keys()))
            )

        synced, errors = await batch_write_back(self._repo, updates)
        return synced, errors, results

    async def _fetch_by_terminal(
        self,
        container_numbers: list[str],
        terminal_full_name: str | None,
    ) -> tuple[dict[str, dict[str, Any]], str]:
        """根据 Terminal Full Name 选择 Provider 查询。"""
        tfn = (terminal_full_name or "").strip().upper()

        if not tfn:
            data = await self._onestop.customs_cargo_status_search(container_numbers)
            if data:
                return data, "1-Stop customs"
            data = await self._hutchison.container_enquiry_by_list(container_numbers)
            return data, "Hutchison"

        if tfn == _HUTCHISON_TERMINAL:
            data = await self._hutchison.container_enquiry_by_list(container_numbers)
            return data, "Hutchison"

        data = await self._onestop.customs_cargo_status_search(container_numbers)
        return data, "1-Stop customs"

    async def _find_import_record_ids(self, container_numbers: list[str]) -> dict[str, str]:
        result: dict[str, str] = {}
        cn_set = set(container_numbers)
        all_records = await self._repo.list_all_records(field_names=["Container Number"])
        for r in all_records:
            cn = extract_cell_text(r.get("Container Number"))
            if cn and cn in cn_set:
                result[cn] = r["record_id"]
        return result

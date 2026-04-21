from __future__ import annotations

import logging
from typing import Any

from app.common.bitable_query import BitableQuery
from app.component.VbsSearchProvider import VbsSearchProvider
from app.core.lark_bitable_value import extract_cell_text
from app.repository.import_ import ImportRepository
from app.service.sync.base import (
    FieldMapping,
    LinkResolver,
    MultiProviderBatchCondition,
    batch_write_back,
    build_update_fields,
)
from app.service.sync.model.vbs_sync_schemas import VbsBatchSyncResult, VbsSyncResult

logger = logging.getLogger(__name__)

# Terminal Full Name → VBS operation
_TERMINAL_TO_OPERATION: dict[str, str] = {
    "DP WORLD NS PORT BOTANY": "dpWorldNSW",
    "PATRICK NS PORT BOTANY": "patrickNSW",
    "DP WORLD, VI, WEST SWANSON": "dpWorldVIC",
    "PATRICK, VI, EAST SWANSON": "patrickVIC",
    "VICTORIA INTERNATIONAL CONTAINER TERMINAL": "victVIC",
}


def _get_operation(terminal_full_name: str | None) -> str | None:
    if not terminal_full_name:
        return None
    return _TERMINAL_TO_OPERATION.get(terminal_full_name.strip().upper())


# ── 声明式配置 ─────────────────────────────────────────────────

# VBS 返回: EstimatedArrival / ImportAvailability / StorageStartDate
_VBS_FIELDS: list[FieldMapping] = [
    FieldMapping("EstimatedArrival", "EstimatedArrival"),
    FieldMapping("ImportAvailability", "ImportAvailability"),
    FieldMapping("StorageStartDate", "StorageStartDate"),
]


# ── 条件定义 ──────────────────────────────────────────────────

# 每个 VBS operation 一组写回字段（结构相同，按 operation 分组是为了支持多 Provider 扩展）
_WRITE_FIELDS_BY_OP: dict[str, list[FieldMapping]] = {op: _VBS_FIELDS for op in _TERMINAL_TO_OPERATION.values()}

VBS_BATCH_CONDITIONS: dict[str, MultiProviderBatchCondition] = {
    # ─ pending ──────────────────────────────────────────────
    # 筛选: GATEOUT_Time 为空 (尚未提柜)
    # 写回: EstimatedArrival + ImportAvailability + StorageStartDate
    "pending": MultiProviderBatchCondition(
        name="pending",
        description="GATEOUT_Time 为空且 Terminal 可路由到 VBS",
        query=BitableQuery().is_empty("GATEOUT_Time"),
        write_fields=_WRITE_FIELDS_BY_OP,
    ),
    # ─ all ──────────────────────────────────────────────────
    # 筛选: 全部可路由记录
    # 写回: 同 pending
    "all": MultiProviderBatchCondition(
        name="all",
        description="全部可路由到 VBS 的记录",
        query=BitableQuery(),
        write_fields=_WRITE_FIELDS_BY_OP,
    ),
}


class VbsSyncService:
    """VBS 集装箱可用性同步服务。

    根据 Terminal Full Name 路由到不同 VBS operation:
    - DP WORLD NS PORT BOTANY → dpWorldNSW
    - PATRICK NS PORT BOTANY → patrickNSW
    - DP WORLD, VI, WEST SWANSON → dpWorldVIC
    - PATRICK, VI, EAST SWANSON → patrickVIC
    - VICTORIA INTERNATIONAL CONTAINER TERMINAL LIMITED → victVIC
    - 其他 Terminal → 不查（VBS 无对应站点）
    """

    def __init__(
        self,
        import_repo: ImportRepository | None = None,
        vbs: VbsSearchProvider | None = None,
    ) -> None:
        self._repo = import_repo or ImportRepository()
        self._vbs = vbs or VbsSearchProvider()
        self._link_resolver = LinkResolver()

    @staticmethod
    def list_conditions() -> list[dict[str, str]]:
        return [{"name": c.name, "description": c.description} for c in VBS_BATCH_CONDITIONS.values()]

    async def sync(
        self,
        container_numbers: list[str],
        terminal_full_name: str | None = None,
    ) -> VbsBatchSyncResult:
        """手动触发：按柜号 + Terminal 路由 VBS → 写回。"""
        if not container_numbers:
            return VbsBatchSyncResult()

        operation = _get_operation(terminal_full_name)
        if not operation:
            return VbsBatchSyncResult(
                total=len(container_numbers),
                details=[
                    VbsSyncResult(container_number=cn, error="Terminal 无法路由到 VBS") for cn in container_numbers
                ],
            )

        provider_data = await self._vbs.get_ctn_info_by_list(container_numbers, operation)
        cn_to_record_id = await self._find_import_record_ids(container_numbers)

        write_fields = VBS_BATCH_CONDITIONS["all"].write_fields.get(operation, _VBS_FIELDS)
        updates: list[dict[str, Any]] = []
        results: list[VbsSyncResult] = []

        for cn in container_numbers:
            data = provider_data.get(cn)
            if not data:
                results.append(VbsSyncResult(container_number=cn, operation=operation, error="VBS 无数据"))
                continue

            fields = await build_update_fields(data, write_fields, self._link_resolver)
            if not fields:
                results.append(VbsSyncResult(container_number=cn, operation=operation, raw=data))
                continue

            record_id = cn_to_record_id.get(cn)
            if not record_id:
                results.append(
                    VbsSyncResult(container_number=cn, operation=operation, error="Op-Import 中未找到该柜号", raw=data)
                )
                continue

            updates.append({"record_id": record_id, "fields": fields})
            results.append(VbsSyncResult(container_number=cn, operation=operation, updated_fields=list(fields.keys())))

        synced, errors = await batch_write_back(self._repo, updates)
        logger.info("VBS 同步 [%s]: %d 成功 / %d 失败", operation, synced, errors)
        return VbsBatchSyncResult(total=len(container_numbers), synced=synced, errors=errors, details=results)

    async def sync_batch(self, condition: str = "pending") -> VbsBatchSyncResult:
        """按条件筛选 Op-Import → 按 Terminal 路由 VBS operation → 写回。"""
        cond = VBS_BATCH_CONDITIONS.get(condition)
        if cond is None:
            available = ", ".join(VBS_BATCH_CONDITIONS.keys())
            raise ValueError(f"未知条件 '{condition}'，可用条件: {available}")

        filter_expr = cond.query.build()
        all_records = await self._repo.list_all_records(filter_expr=filter_expr)
        pending = cond.query.filter(all_records)

        logger.info("VBS 批量同步 [%s]: %d 条", condition, len(pending))

        # 按 operation 分组
        groups: dict[str, list[dict[str, Any]]] = {}
        skipped: list[dict[str, Any]] = []
        for r in pending:
            tfn = extract_cell_text(r.get("Terminal Full Name"))
            op = _get_operation(tfn)
            if op:
                groups.setdefault(op, []).append(r)
            else:
                skipped.append(r)

        all_results: list[VbsSyncResult] = []
        total_synced = 0
        total_errors = 0

        for op, records in groups.items():
            write_fields = cond.write_fields.get(op, _VBS_FIELDS)
            synced, errors, results = await self._sync_record_group(records, op, write_fields)
            total_synced += synced
            total_errors += errors
            all_results.extend(results)

        if skipped:
            for r in skipped:
                cn = extract_cell_text(r.get("Container Number")) or ""
                all_results.append(VbsSyncResult(container_number=cn, error="Terminal 无法路由到 VBS"))

        logger.info("VBS 批量同步完成: %d 成功 / %d 失败", total_synced, total_errors)
        return VbsBatchSyncResult(total=len(pending), synced=total_synced, errors=total_errors, details=all_results)

    async def _sync_record_group(
        self,
        records: list[dict[str, Any]],
        operation: str,
        write_fields: list[FieldMapping],
    ) -> tuple[int, int, list[VbsSyncResult]]:
        """按一组 Op-Import 记录查同一个 VBS operation 并写回。"""
        container_numbers = [cn for r in records if (cn := extract_cell_text(r.get("Container Number")))]

        provider_data = await self._vbs.get_ctn_info_by_list(container_numbers, operation)

        cn_to_record_id = {cn: r["record_id"] for r in records if (cn := extract_cell_text(r.get("Container Number")))}

        updates: list[dict[str, Any]] = []
        results: list[VbsSyncResult] = []

        for cn in container_numbers:
            data = provider_data.get(cn)
            if not data:
                results.append(VbsSyncResult(container_number=cn, operation=operation, error="VBS 无数据"))
                continue

            fields = await build_update_fields(data, write_fields, self._link_resolver)
            if not fields:
                results.append(VbsSyncResult(container_number=cn, operation=operation, raw=data))
                continue

            record_id = cn_to_record_id.get(cn)
            if not record_id:
                results.append(
                    VbsSyncResult(container_number=cn, operation=operation, error="Op-Import 中未找到该柜号", raw=data)
                )
                continue

            updates.append({"record_id": record_id, "fields": fields})
            results.append(VbsSyncResult(container_number=cn, operation=operation, updated_fields=list(fields.keys())))

        synced, errors = await batch_write_back(self._repo, updates)
        return synced, errors, results

    async def _find_import_record_ids(self, container_numbers: list[str]) -> dict[str, str]:
        result: dict[str, str] = {}
        cn_set = set(container_numbers)
        all_records = await self._repo.list_all_records(field_names=["Container Number"])
        for r in all_records:
            cn = extract_cell_text(r.get("Container Number"))
            if cn and cn in cn_set:
                result[cn] = r["record_id"]
        return result

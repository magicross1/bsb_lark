from __future__ import annotations

from app.common.query_wrapper import QueryWrapper
from app.common.update_wrapper import UpdateWrapper

import logging
from typing import TYPE_CHECKING, Any

from app.cache.constants import CartageMatchingCacheKey
from app.cache.factory import CacheFactory
from app.entity.link_resolver import LinkFieldResolver
from app.repository.cartage import CartageRepository
from app.repository.consingee import ConsingeeRepository
from app.repository.export_ import ExportRepository
from app.repository.import_ import ImportRepository
from app.repository.warehouse_address import WarehouseAddressRepository
from app.repository.warehouse_deliver_config import WarehouseDeliverConfigRepository
from app.service.cartage.model.cartage_writeback_config import (
    OP_CARTAGE_EXPORT_RULES,
    OP_CARTAGE_IMPORT_RULES,
    OP_EXPORT_RULES,
    OP_IMPORT_RULES,
    WritebackFieldRule,
)
from app.service.cartage.model.cartage_writeback_schemas import (
    CartageWritebackResult,
    SkippedContainer,
    WritebackRecordRef,
)

if TYPE_CHECKING:
    from app.service.llm_service.cartage.process_schemas import CartageProcessResult

logger = logging.getLogger(__name__)

RECORD_STATUS_SUCCESS = "Entry Successful"
RECORD_STATUS_DUPLICATE = "Duplicate Entry Failed"


class CartageService:
    """Cartage 领域 Service：Cartage 所有业务能力的统一入口。

    职责：
    - Op-Cartage / Op-Import / Op-Export：业务表 CRUD 与重复检查
    - MD-Warehouse Address / Deliver Config / Consingee：主数据批量读（带缓存，供 enrichment 使用）
    - Writeback：将 LLM 解析结果写回 Lark 表，含重复检测与状态标注
    """

    def __init__(
        self,
        cache_factory: CacheFactory | None = None,
        op_cartage_repo: CartageRepository | None = None,
        import_repo: ImportRepository | None = None,
        export_repo: ExportRepository | None = None,
        warehouse_address_repo: WarehouseAddressRepository | None = None,
        warehouse_deliver_config_repo: WarehouseDeliverConfigRepository | None = None,
        consingee_repo: ConsingeeRepository | None = None,
        link_resolver: LinkFieldResolver | None = None,
    ) -> None:
        self._cache_factory = cache_factory if cache_factory is not None else CacheFactory()
        self._op_cartage_repo = op_cartage_repo or CartageRepository()
        self._import_repo = import_repo or ImportRepository()
        self._export_repo = export_repo or ExportRepository()
        self._warehouse_address_repo = warehouse_address_repo or WarehouseAddressRepository()
        self._warehouse_deliver_config_repo = warehouse_deliver_config_repo or WarehouseDeliverConfigRepository()
        self._consingee_repo = consingee_repo or ConsingeeRepository()
        self._link_resolver = link_resolver or LinkFieldResolver()

    @property
    def cache_factory(self) -> CacheFactory:
        return self._cache_factory

    # ── 主数据批量读（带缓存） ─────────────────────────────────

    async def list_addresses_for_matching(self) -> list[dict[str, Any]]:
        c = self._cache_factory
        key = CartageMatchingCacheKey.ADDRESSES
        cached = c.get(key)
        if cached is None:
            records = await self._warehouse_address_repo.list(
                QueryWrapper().select("Address"),
            )
            c.set(key, records)
            return records
        return cached

    async def list_deliver_configs_for_matching(self) -> list[dict[str, Any]]:
        c = self._cache_factory
        key = CartageMatchingCacheKey.DELIVER_CONFIGS
        cached = c.get(key)
        if cached is None:
            records = await self._warehouse_deliver_config_repo.list(
                QueryWrapper().select("Deliver Config", "Deliver Type", "Warehouse Address"),
            )
            c.set(key, records)
            return records
        return cached

    async def list_consingees_for_matching(self) -> list[dict[str, Any]]:
        c = self._cache_factory
        key = CartageMatchingCacheKey.CONSINGEES
        cached = c.get(key)
        if cached is None:
            records = await self._consingee_repo.list(
                QueryWrapper().select("Name", "MD-Warehouse Address"),
            )
            c.set(key, records)
            return records
        return cached

    def clear_cache(self) -> None:
        self._cache_factory.clear()

    # ── Writeback 公开入口 ────────────────────────────────────

    async def writeback(self, result: CartageProcessResult) -> CartageWritebackResult:
        """将 LLM 处理结果写回 Lark（新建模式，不依赖已有记录）。"""
        if result.direction and result.direction.upper() == "IMPORT":
            return await self._writeback_import(result)
        return await self._writeback_export(result)

    async def writeback_from_record(
        self,
        result: CartageProcessResult,
        source_record_id: str,
    ) -> CartageWritebackResult:
        """将 LLM 处理结果写回 Lark（从已有 Op-Cartage 记录触发）。

        第一条非重复记录更新源记录，后续超额记录新建并关联 Source Cartage。
        """
        if result.direction and result.direction.upper() == "IMPORT":
            return await self._writeback_import_from_record(result, source_record_id)
        return await self._writeback_export_from_record(result, source_record_id)

    # ── Import 写回（新建模式） ────────────────────────────────

    async def _writeback_import(self, result: CartageProcessResult) -> CartageWritebackResult:
        skipped: list[SkippedContainer] = []
        to_create = []

        for container in result.import_containers:
            if not container.container_number:
                skipped.append(SkippedContainer(container_number="", reason="missing container_number"))
                continue
            existing = await self._import_repo.findOne(QueryWrapper().eq("Container Number", container.container_number))
            if existing:
                skipped.append(
                    SkippedContainer(
                        container_number=container.container_number,
                        reason="duplicate",
                        existing_record_id=existing["record_id"],
                    )
                )
                logger.warning("跳过重复箱号 %s（已存在 %s）", container.container_number, existing["record_id"])
                continue
            to_create.append(container)

        if not to_create:
            return CartageWritebackResult(skipped=skipped)

        cartage_refs: list[WritebackRecordRef] = []
        import_refs: list[WritebackRecordRef] = []

        for container in to_create:
            cartage_fields = await self._build_cartage_fields(result, OP_CARTAGE_IMPORT_RULES)
            cartage_created = await self._op_cartage_repo.createOne(cartage_fields)
            cartage_ref = WritebackRecordRef(record_id=cartage_created["record_id"], table_name="Op-Cartage")
            cartage_refs.append(cartage_ref)

            import_fields = await self._build_import_fields(container, cartage_ref.record_id)
            import_created = await self._import_repo.createOne(import_fields)
            import_refs.append(WritebackRecordRef(record_id=import_created["record_id"], table_name="Op-Import"))
            logger.info("创建 Op-Import %s → Op-Cartage %s", import_created["record_id"], cartage_ref.record_id)

        return CartageWritebackResult(cartage_refs=cartage_refs, imports=import_refs, skipped=skipped)

    # ── Import 写回（源记录模式） ─────────────────────────────

    async def _writeback_import_from_record(
        self,
        result: CartageProcessResult,
        source_record_id: str,
    ) -> CartageWritebackResult:
        cartage_refs: list[WritebackRecordRef] = []
        import_refs: list[WritebackRecordRef] = []
        skipped: list[SkippedContainer] = []
        first_used = False

        for container in result.import_containers:
            is_dup = False
            if container.container_number:
                existing = await self._import_repo.findOne(QueryWrapper().eq("Container Number", container.container_number))
                if existing:
                    is_dup = True
                    skipped.append(
                        SkippedContainer(
                            container_number=container.container_number,
                            reason="duplicate",
                            existing_record_id=existing["record_id"],
                        )
                    )
                    logger.warning("重复箱号 %s（已存在 %s）", container.container_number, existing["record_id"])

            cartage_fields = await self._build_cartage_fields(result, OP_CARTAGE_IMPORT_RULES)

            if is_dup:
                cartage_fields["Record Status"] = RECORD_STATUS_DUPLICATE
                cartage_fields["Source Cartage"] = [source_record_id]
                cartage_created = await self._op_cartage_repo.createOne(cartage_fields)
                cartage_refs.append(
                    WritebackRecordRef(record_id=cartage_created["record_id"], table_name="Op-Cartage")
                )
                continue

            if not first_used:
                cartage_fields["Record Status"] = RECORD_STATUS_SUCCESS
                cartage_fields["Source Cartage"] = [source_record_id]
                await self._op_cartage_repo.updateOne(UpdateWrapper().eq("record_id", source_record_id).set_all(cartage_fields))
                cartage_ref = WritebackRecordRef(record_id=source_record_id, table_name="Op-Cartage")
                first_used = True
                logger.info("更新 Op-Cartage %s 对应箱号 %s", source_record_id, container.container_number)
            else:
                cartage_fields["Record Status"] = RECORD_STATUS_SUCCESS
                cartage_fields["Source Cartage"] = [source_record_id]
                cartage_created = await self._op_cartage_repo.createOne(cartage_fields)
                cartage_ref = WritebackRecordRef(record_id=cartage_created["record_id"], table_name="Op-Cartage")
                logger.info("创建 Op-Cartage %s 对应箱号 %s", cartage_created["record_id"], container.container_number)
            cartage_refs.append(cartage_ref)

            import_fields = await self._build_import_fields(container, cartage_ref.record_id)
            import_created = await self._import_repo.createOne(import_fields)
            import_refs.append(WritebackRecordRef(record_id=import_created["record_id"], table_name="Op-Import"))

        if not first_used and skipped:
            await self._op_cartage_repo.updateOne(UpdateWrapper().eq("record_id", source_record_id)
                .set("Record Status", RECORD_STATUS_DUPLICATE,)
                .set("Source Cartage", [source_record_id]))

        return CartageWritebackResult(cartage_refs=cartage_refs, imports=import_refs, skipped=skipped)

    # ── Export 写回（新建模式） ────────────────────────────────

    async def _writeback_export(self, result: CartageProcessResult) -> CartageWritebackResult:
        from app.service.llm_service.cartage.export_bookings import expand_export_bookings

        expanded = expand_export_bookings(result.export_bookings)
        skipped: list[SkippedContainer] = []
        to_create = []

        for booking in expanded:
            cn = booking.container_number
            if cn:
                existing = await self._export_repo.findOne(QueryWrapper().eq("Container Number", cn))
                if existing:
                    skipped.append(
                        SkippedContainer(
                            container_number=cn, reason="duplicate", existing_record_id=existing["record_id"]
                        )
                    )
                    logger.warning("跳过重复出口箱号 %s（已存在 %s）", cn, existing["record_id"])
                    continue
            to_create.append(booking)

        if not to_create:
            return CartageWritebackResult(skipped=skipped)

        cartage_refs: list[WritebackRecordRef] = []
        export_refs: list[WritebackRecordRef] = []

        for booking in to_create:
            cartage_fields = await self._build_cartage_fields(result, OP_CARTAGE_EXPORT_RULES)
            cartage_created = await self._op_cartage_repo.createOne(cartage_fields)
            cartage_ref = WritebackRecordRef(record_id=cartage_created["record_id"], table_name="Op-Cartage")
            cartage_refs.append(cartage_ref)

            export_fields = await self._build_export_fields(booking, cartage_ref.record_id)
            export_created = await self._export_repo.createOne(export_fields)
            export_refs.append(WritebackRecordRef(record_id=export_created["record_id"], table_name="Op-Export"))

        return CartageWritebackResult(cartage_refs=cartage_refs, exports=export_refs, skipped=skipped)

    # ── Export 写回（源记录模式） ─────────────────────────────

    async def _writeback_export_from_record(
        self,
        result: CartageProcessResult,
        source_record_id: str,
    ) -> CartageWritebackResult:
        from app.service.llm_service.cartage.export_bookings import expand_export_bookings

        expanded = expand_export_bookings(result.export_bookings)
        cartage_refs: list[WritebackRecordRef] = []
        export_refs: list[WritebackRecordRef] = []
        skipped: list[SkippedContainer] = []
        first_used = False

        for booking in expanded:
            is_dup = False
            cn = booking.container_number
            if cn:
                existing = await self._export_repo.findOne(QueryWrapper().eq("Container Number", cn))
                if existing:
                    is_dup = True
                    skipped.append(
                        SkippedContainer(
                            container_number=cn, reason="duplicate", existing_record_id=existing["record_id"]
                        )
                    )
                    logger.warning("重复出口箱号 %s（已存在 %s）", cn, existing["record_id"])

            cartage_fields = await self._build_cartage_fields(result, OP_CARTAGE_EXPORT_RULES)

            if is_dup:
                cartage_fields["Record Status"] = RECORD_STATUS_DUPLICATE
                cartage_fields["Source Cartage"] = [source_record_id]
                cartage_created = await self._op_cartage_repo.createOne(cartage_fields)
                cartage_refs.append(
                    WritebackRecordRef(record_id=cartage_created["record_id"], table_name="Op-Cartage")
                )
                continue

            if not first_used:
                cartage_fields["Record Status"] = RECORD_STATUS_SUCCESS
                cartage_fields["Source Cartage"] = [source_record_id]
                await self._op_cartage_repo.updateOne(UpdateWrapper().eq("record_id", source_record_id).set_all(cartage_fields))
                cartage_ref = WritebackRecordRef(record_id=source_record_id, table_name="Op-Cartage")
                first_used = True
                logger.info("更新 Op-Cartage %s 对应出口订舱 %s", source_record_id, booking.booking_reference)
            else:
                cartage_fields["Record Status"] = RECORD_STATUS_SUCCESS
                cartage_fields["Source Cartage"] = [source_record_id]
                cartage_created = await self._op_cartage_repo.createOne(cartage_fields)
                cartage_ref = WritebackRecordRef(record_id=cartage_created["record_id"], table_name="Op-Cartage")
                logger.info(
                    "创建 Op-Cartage %s 对应出口订舱 %s", cartage_created["record_id"], booking.booking_reference
                )
            cartage_refs.append(cartage_ref)

            export_fields = await self._build_export_fields(booking, cartage_ref.record_id)
            export_created = await self._export_repo.createOne(export_fields)
            export_refs.append(WritebackRecordRef(record_id=export_created["record_id"], table_name="Op-Export"))

        if not first_used and skipped:
            await self._op_cartage_repo.updateOne(UpdateWrapper().eq("record_id", source_record_id)
                .set("Record Status", RECORD_STATUS_DUPLICATE,)
                .set("Source Cartage", [source_record_id]))

        return CartageWritebackResult(cartage_refs=cartage_refs, exports=export_refs, skipped=skipped)

    # ── 字段构建辅助 ──────────────────────────────────────────

    async def _build_cartage_fields(
        self,
        result: CartageProcessResult,
        rules: list[WritebackFieldRule],
    ) -> dict:
        """从 CartageProcessResult 构造 Op-Cartage 字段字典。"""
        source = {
            "booking_reference": result.booking_reference,
            "consingee_id": result.address_match.consingee_id if result.address_match else None,
            "deliver_config_id": result.address_match.deliver_config_id if result.address_match else None,
        }
        return await self._build_fields(rules, source)

    async def _build_import_fields(self, container: Any, cartage_record_id: str) -> dict:
        """从进口箱信息构造 Op-Import 字段字典。"""
        source = {
            "container_number": container.container_number,
            "container_type": container.container_type,
            "container_weight": container.container_weight,
            "commodity": container.commodity,
            "vessel_name": container.vessel_name,
            "voyage": container.voyage,
            "base_node": container.base_node,
        }
        fields = await self._build_fields(OP_IMPORT_RULES, source)
        fields["Op-Cartage"] = [cartage_record_id]
        return fields

    async def _build_export_fields(self, booking: Any, cartage_record_id: str) -> dict:
        """从出口订舱信息构造 Op-Export 字段字典。"""
        source = {
            "booking_reference": booking.booking_reference,
            "container_number": booking.container_number,
            "release_qty": booking.release_qty,
            "container_type": booking.container_type,
            "commodity": booking.commodity,
            "vessel_name": booking.vessel_name,
            "voyage": booking.voyage,
            "base_node": booking.base_node,
        }
        fields = await self._build_fields(OP_EXPORT_RULES, source)
        fields["Op-Cartage"] = [cartage_record_id]
        return fields

    async def _build_fields(
        self,
        rules: list[WritebackFieldRule],
        source: dict,
    ) -> dict:
        """按规则列表把 source 字典转换为 Bitable 字段字典。"""
        fields: dict = {}
        for rule in rules:
            value = source.get(rule.source_key)

            if rule.is_direct_link:
                if value:
                    fields[rule.bitable_field] = [str(value)]
                continue

            if rule.link_lookup:
                if value:
                    link_ids = await self._link_resolver.resolve(
                        lookup=rule.link_lookup,
                        value=str(value),
                        context=source,
                    )
                    if link_ids:
                        fields[rule.bitable_field] = link_ids
                continue

            if value is not None and value != "":
                fields[rule.bitable_field] = value
            elif rule.required:
                fields[rule.bitable_field] = rule.default_value or "TBC"

        logger.debug("_build_fields result: %s", {k: type(v).__name__ + '=' + str(v)[:50] for k, v in fields.items()})
        return fields

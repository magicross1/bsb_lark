from __future__ import annotations

import logging

from app.entity.link_resolver import LinkFieldResolver
from app.repository.cartage import CartageRepository
from app.repository.export_ import ExportRepository
from app.repository.import_ import ImportRepository
from app.service.llm_service.cartage.export_bookings import expand_export_bookings
from app.service.llm_service.cartage.process_schemas import (
    CartageProcessResult,
    ExportBookingMatch,
    ImportContainerMatch,
)
from app.service.llm_service.cartage.schemas import ExportBookingEntry, ImportContainerEntry
from app.service.llm_service.cartage.writeback_config import (
    OP_CARTAGE_EXPORT_RULES,
    OP_CARTAGE_IMPORT_RULES,
    OP_EXPORT_RULES,
    OP_IMPORT_RULES,
    WritebackFieldRule,
)
from app.service.llm_service.cartage.writeback_schemas import (
    CartageWritebackResult,
    SkippedContainer,
    WritebackRecordRef,
)

logger = logging.getLogger(__name__)

RECORD_STATUS_SUCCESS = "Entry Successful"
RECORD_STATUS_DUPLICATE = "Duplicate Entry Failed"


class CartageWritebackService:
    def __init__(
        self,
        cartage_repo: CartageRepository | None = None,
        import_repo: ImportRepository | None = None,
        export_repo: ExportRepository | None = None,
        link_resolver: LinkFieldResolver | None = None,
    ) -> None:
        self._cartage_repo = cartage_repo or CartageRepository()
        self._import_repo = import_repo or ImportRepository()
        self._export_repo = export_repo or ExportRepository()
        self._link_resolver = link_resolver or LinkFieldResolver()

    async def writeback(self, result: CartageProcessResult) -> CartageWritebackResult:
        if result.direction and result.direction.upper() == "IMPORT":
            return await self._writeback_import(result)
        return await self._writeback_export(result)

    async def writeback_from_record(
        self,
        result: CartageProcessResult,
        source_record_id: str,
    ) -> CartageWritebackResult:
        """Writeback triggered from an existing Op-Cartage record.

        First non-duplicate item updates the source record.
        Remaining items create new Op-Cartage rows with Source Cartage pointing to source.
        Each row gets Record Status: Entry Successful or Duplicate Entry Failed.
        """
        if result.direction and result.direction.upper() == "IMPORT":
            return await self._writeback_import_from_record(result, source_record_id)
        return await self._writeback_export_from_record(result, source_record_id)

    # ── Import (standalone, no source record) ────────────────

    async def _writeback_import(self, result: CartageProcessResult) -> CartageWritebackResult:
        skipped: list[SkippedContainer] = []
        to_create = []

        for container in result.import_containers:
            if not container.container_number:
                skipped.append(SkippedContainer(container_number="", reason="missing container_number"))
                continue
            existing = await self._import_repo.find_record("Container Number", container.container_number)
            if existing:
                skipped.append(
                    SkippedContainer(
                        container_number=container.container_number,
                        reason="duplicate",
                        existing_record_id=existing["record_id"],
                    )
                )
                logger.warning(
                    "Skipping duplicate container %s (existing %s)", container.container_number, existing["record_id"]
                )
                continue
            to_create.append(container)

        if not to_create:
            return CartageWritebackResult(skipped=skipped)

        cartage_refs: list[WritebackRecordRef] = []
        import_refs: list[WritebackRecordRef] = []

        for container in to_create:
            cartage_source = {
                "booking_reference": result.booking_reference,
                "consingee_id": result.address_match.consingee_id if result.address_match else None,
                "deliver_config_id": result.address_match.deliver_config_id if result.address_match else None,
            }
            cartage_fields = await self._build_fields(OP_CARTAGE_IMPORT_RULES, cartage_source)
            cartage_created = await self._cartage_repo.create_record(cartage_fields)
            cartage_ref = WritebackRecordRef(record_id=cartage_created["record_id"], table_name="Op-Cartage")
            cartage_refs.append(cartage_ref)

            import_fields = await self._build_import_fields(container, cartage_ref.record_id)
            import_created = await self._import_repo.create_record(import_fields)
            import_refs.append(WritebackRecordRef(record_id=import_created["record_id"], table_name="Op-Import"))
            logger.info("Created Op-Import %s → Op-Cartage %s", import_created["record_id"], cartage_ref.record_id)

        return CartageWritebackResult(cartage_refs=cartage_refs, imports=import_refs, skipped=skipped)

    # ── Import (from existing Op-Cartage record) ─────────────

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
                existing = await self._import_repo.find_record("Container Number", container.container_number)
                if existing:
                    is_dup = True
                    skipped.append(
                        SkippedContainer(
                            container_number=container.container_number,
                            reason="duplicate",
                            existing_record_id=existing["record_id"],
                        )
                    )
                    logger.warning(
                        "Duplicate container %s (existing %s)", container.container_number, existing["record_id"]
                    )

            cartage_source = {
                "booking_reference": result.booking_reference,
                "consingee_id": result.address_match.consingee_id if result.address_match else None,
                "deliver_config_id": result.address_match.deliver_config_id if result.address_match else None,
            }
            cartage_fields = await self._build_fields(OP_CARTAGE_IMPORT_RULES, cartage_source)

            if is_dup:
                cartage_fields["Record Status"] = RECORD_STATUS_DUPLICATE
                cartage_fields["Source Cartage"] = [source_record_id]
                if not first_used:
                    cartage_fields["Source Cartage"] = [source_record_id]
                cartage_created = await self._cartage_repo.create_record(cartage_fields)
                cartage_refs.append(WritebackRecordRef(record_id=cartage_created["record_id"], table_name="Op-Cartage"))
                continue

            if not first_used:
                cartage_fields["Record Status"] = RECORD_STATUS_SUCCESS
                cartage_fields["Source Cartage"] = [source_record_id]
                await self._cartage_repo.update_record(source_record_id, cartage_fields)
                cartage_ref = WritebackRecordRef(record_id=source_record_id, table_name="Op-Cartage")
                first_used = True
                logger.info("Updated Op-Cartage %s for container %s", source_record_id, container.container_number)
            else:
                cartage_fields["Record Status"] = RECORD_STATUS_SUCCESS
                cartage_fields["Source Cartage"] = [source_record_id]
                cartage_created = await self._cartage_repo.create_record(cartage_fields)
                cartage_ref = WritebackRecordRef(record_id=cartage_created["record_id"], table_name="Op-Cartage")
                logger.info(
                    "Created Op-Cartage %s for container %s", cartage_created["record_id"], container.container_number
                )
            cartage_refs.append(cartage_ref)

            import_fields = await self._build_import_fields(container, cartage_ref.record_id)
            import_created = await self._import_repo.create_record(import_fields)
            import_refs.append(WritebackRecordRef(record_id=import_created["record_id"], table_name="Op-Import"))

        if not first_used and skipped:
            await self._cartage_repo.update_record(
                source_record_id,
                {
                    "Record Status": RECORD_STATUS_DUPLICATE,
                    "Source Cartage": [source_record_id],
                },
            )

        return CartageWritebackResult(cartage_refs=cartage_refs, imports=import_refs, skipped=skipped)

    # ── Export (standalone, no source record) ─────────────────

    async def _writeback_export(self, result: CartageProcessResult) -> CartageWritebackResult:
        expanded = expand_export_bookings(result.export_bookings)
        skipped: list[SkippedContainer] = []
        to_create: list[ExportBookingEntry] = []

        for booking in expanded:
            cn = booking.container_number
            if cn:
                existing = await self._export_repo.find_record("Container Number", cn)
                if existing:
                    skipped.append(
                        SkippedContainer(
                            container_number=cn, reason="duplicate", existing_record_id=existing["record_id"]
                        )
                    )
                    logger.warning("Skipping duplicate export container %s (existing %s)", cn, existing["record_id"])
                    continue
            to_create.append(booking)

        if not to_create:
            return CartageWritebackResult(skipped=skipped)

        cartage_refs: list[WritebackRecordRef] = []
        export_refs: list[WritebackRecordRef] = []

        for booking in to_create:
            cartage_source = {
                "booking_reference": result.booking_reference,
                "consingee_id": result.address_match.consingee_id if result.address_match else None,
                "deliver_config_id": result.address_match.deliver_config_id if result.address_match else None,
            }
            cartage_fields = await self._build_fields(OP_CARTAGE_EXPORT_RULES, cartage_source)
            cartage_created = await self._cartage_repo.create_record(cartage_fields)
            cartage_ref = WritebackRecordRef(record_id=cartage_created["record_id"], table_name="Op-Cartage")
            cartage_refs.append(cartage_ref)

            export_fields = await self._build_export_fields(booking, cartage_ref.record_id)
            export_created = await self._export_repo.create_record(export_fields)
            export_refs.append(WritebackRecordRef(record_id=export_created["record_id"], table_name="Op-Export"))

        return CartageWritebackResult(cartage_refs=cartage_refs, exports=export_refs, skipped=skipped)

    # ── Export (from existing Op-Cartage record) ──────────────

    async def _writeback_export_from_record(
        self,
        result: CartageProcessResult,
        source_record_id: str,
    ) -> CartageWritebackResult:
        expanded = expand_export_bookings(result.export_bookings)
        cartage_refs: list[WritebackRecordRef] = []
        export_refs: list[WritebackRecordRef] = []
        skipped: list[SkippedContainer] = []
        first_used = False

        for booking in expanded:
            is_dup = False
            cn = booking.container_number
            if cn:
                existing = await self._export_repo.find_record("Container Number", cn)
                if existing:
                    is_dup = True
                    skipped.append(
                        SkippedContainer(
                            container_number=cn, reason="duplicate", existing_record_id=existing["record_id"]
                        )
                    )
                    logger.warning("Duplicate export container %s (existing %s)", cn, existing["record_id"])

            cartage_source = {
                "booking_reference": result.booking_reference,
                "consingee_id": result.address_match.consingee_id if result.address_match else None,
                "deliver_config_id": result.address_match.deliver_config_id if result.address_match else None,
            }
            cartage_fields = await self._build_fields(OP_CARTAGE_EXPORT_RULES, cartage_source)

            if is_dup:
                cartage_fields["Record Status"] = RECORD_STATUS_DUPLICATE
                cartage_fields["Source Cartage"] = [source_record_id]
                cartage_created = await self._cartage_repo.create_record(cartage_fields)
                cartage_refs.append(WritebackRecordRef(record_id=cartage_created["record_id"], table_name="Op-Cartage"))
                continue

            if not first_used:
                cartage_fields["Record Status"] = RECORD_STATUS_SUCCESS
                cartage_fields["Source Cartage"] = [source_record_id]
                await self._cartage_repo.update_record(source_record_id, cartage_fields)
                cartage_ref = WritebackRecordRef(record_id=source_record_id, table_name="Op-Cartage")
                first_used = True
                logger.info("Updated Op-Cartage %s for export booking %s", source_record_id, booking.booking_reference)
            else:
                cartage_fields["Record Status"] = RECORD_STATUS_SUCCESS
                cartage_fields["Source Cartage"] = [source_record_id]
                cartage_created = await self._cartage_repo.create_record(cartage_fields)
                cartage_ref = WritebackRecordRef(record_id=cartage_created["record_id"], table_name="Op-Cartage")
                logger.info(
                    "Created Op-Cartage %s for export booking %s",
                    cartage_created["record_id"],
                    booking.booking_reference,
                )
            cartage_refs.append(cartage_ref)

            export_fields = await self._build_export_fields(booking, cartage_ref.record_id)
            export_created = await self._export_repo.create_record(export_fields)
            export_refs.append(WritebackRecordRef(record_id=export_created["record_id"], table_name="Op-Export"))

        if not first_used and skipped:
            await self._cartage_repo.update_record(
                source_record_id,
                {
                    "Record Status": RECORD_STATUS_DUPLICATE,
                    "Source Cartage": [source_record_id],
                },
            )

        return CartageWritebackResult(cartage_refs=cartage_refs, exports=export_refs, skipped=skipped)

    # ── Shared helpers ────────────────────────────────────────

    async def _build_import_fields(
        self, container: ImportContainerEntry | ImportContainerMatch, cartage_record_id: str
    ) -> dict:
        import_source = {
            "container_number": container.container_number,
            "container_type": container.container_type,
            "container_weight": container.container_weight,
            "commodity": container.commodity,
            "vessel_name": container.vessel_name,
            "voyage": container.voyage,
            "base_node": container.base_node,
        }
        import_fields = await self._build_fields(OP_IMPORT_RULES, import_source)
        import_fields["Op-Cartage"] = [cartage_record_id]
        return import_fields

    async def _build_export_fields(
        self, booking: ExportBookingEntry | ExportBookingMatch, cartage_record_id: str
    ) -> dict:
        export_source = {
            "booking_reference": booking.booking_reference,
            "container_number": booking.container_number,
            "release_qty": booking.release_qty,
            "container_type": booking.container_type,
            "commodity": booking.commodity,
            "vessel_name": booking.vessel_name,
            "voyage": booking.voyage,
            "base_node": booking.base_node,
        }
        export_fields = await self._build_fields(OP_EXPORT_RULES, export_source)
        export_fields["Op-Cartage"] = [cartage_record_id]
        return export_fields

    async def _build_fields(
        self,
        rules: list[WritebackFieldRule],
        source: dict,
    ) -> dict:
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
                    elif rule.required and rule.default_value:
                        fields[rule.bitable_field] = rule.default_value
                continue

            if value is not None and value != "":
                fields[rule.bitable_field] = value
            elif rule.required:
                fields[rule.bitable_field] = rule.default_value or "TBC"

        return fields

from __future__ import annotations

import logging

from app.common.query_wrapper import QueryWrapper
from app.common.update_wrapper import UpdateWrapper
from app.repository.import_ import ImportRepository
from app.service.llm_service.edo.schemas import EdoEntryMatch, EdoProcessResult
from app.service.llm_service.edo.writeback_schemas import EdoWritebackEntryRef, EdoWritebackResult

logger = logging.getLogger(__name__)

RECORD_STATUS_SUCCESS = "Entry Successful"
RECORD_STATUS_DUPLICATE = "Duplicate Entry Failed"


class EdoWritebackService:
    def __init__(self, import_repo: ImportRepository | None = None) -> None:
        self._import_repo = import_repo or ImportRepository()

    async def writeback_from_record(
        self,
        result: EdoProcessResult,
        source_record_id: str,
    ) -> EdoWritebackResult:
        updated: list[EdoWritebackEntryRef] = []
        skipped: list[EdoWritebackEntryRef] = []
        first_used = False

        for entry in result.entries:
            if not entry.container_number:
                skipped.append(
                    EdoWritebackEntryRef(
                        record_id="",
                        container_number="",
                        status="missing container_number",
                    )
                )
                continue

            import_record = await self._import_repo.findOne(QueryWrapper().eq("Container Number", entry.container_number))

            if not import_record:
                skipped.append(
                    EdoWritebackEntryRef(
                        record_id="",
                        container_number=entry.container_number,
                        status="container not found in Op-Import",
                    )
                )
                logger.warning(
                    "EDO container %s not found in Op-Import",
                    entry.container_number,
                )
                continue

            import_record_id = import_record["record_id"]

            if import_record_id == source_record_id:
                first_used = True

            fields = self._build_edo_fields(entry, source_record_id)

            if import_record_id == source_record_id:
                await self._import_repo.updateOne(UpdateWrapper().eq("record_id", source_record_id).set_all(fields))
                logger.info(
                    "Updated source Op-Import %s for container %s",
                    source_record_id,
                    entry.container_number,
                )
            else:
                await self._import_repo.updateOne(UpdateWrapper().eq("record_id", import_record_id).set_all(fields))
                logger.info(
                    "Updated Op-Import %s for container %s (from source %s)",
                    import_record_id,
                    entry.container_number,
                    source_record_id,
                )

            updated.append(
                EdoWritebackEntryRef(
                    record_id=import_record_id,
                    container_number=entry.container_number,
                    status=RECORD_STATUS_SUCCESS,
                )
            )

        if not first_used and updated:
            if not any(e.record_id == source_record_id for e in updated):
                source_record = await self._import_repo.findOne(QueryWrapper().eq("record_id", source_record_id))
                source_cn = source_record.get("Container Number", "")
                skipped.append(
                    EdoWritebackEntryRef(
                        record_id=source_record_id,
                        container_number=str(source_cn),
                        status="source container not in EDO",
                    )
                )

        if not updated:
            await self._import_repo.updateOne(
                UpdateWrapper()
                .eq("record_id", source_record_id)
                .set("Record Status", RECORD_STATUS_DUPLICATE)
                .set("Source EDO", [source_record_id])
            )
            skipped.append(
                EdoWritebackEntryRef(
                    record_id=source_record_id,
                    container_number="",
                    status=RECORD_STATUS_DUPLICATE,
                )
            )

        return EdoWritebackResult(updated=updated, skipped=skipped)

    @staticmethod
    def _build_edo_fields(entry: EdoEntryMatch, source_record_id: str) -> dict:
        fields: dict = {
            "Record Status": RECORD_STATUS_SUCCESS,
            "Source EDO": [source_record_id],
        }

        if entry.edo_pin:
            fields["EDO PIN"] = entry.edo_pin

        if entry.shipping_line_match:
            fields["Shipping Line"] = [entry.shipping_line_match.record_id]

        if entry.empty_park_match:
            fields["Empty Park"] = [entry.empty_park_match.record_id]

        return fields

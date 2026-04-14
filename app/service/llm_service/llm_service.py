from __future__ import annotations

import logging
from pathlib import Path

from app.cache.factory import CacheFactory
from app.service.cartage import CartageService
from app.service.llm_service.cartage.cartage_llm import CartageLlmService
from app.service.llm_service.cartage.enrichment import CartageEnrichmentService
from app.service.llm_service.cartage.process_schemas import CartageProcessResult
from app.service.llm_service.cartage.schemas import CartageDictValues, CartageParseResult
from app.service.llm_service.cartage.writeback import CartageWritebackService
from app.service.llm_service.cartage.writeback_schemas import CartageWritebackResult
from app.service.llm_service.edo.edo_llm import EdoLlmService
from app.service.llm_service.edo.schemas import EdoParseResult


class LLMService:
    """LLM 能力入口：组合 Cartage 解析、:class:`CartageService`（主数据）与富化、EDO 解析。"""

    def __init__(
        self,
        cache_factory: CacheFactory | None = None,
        cartage: CartageService | None = None,
        cartage_llm: CartageLlmService | None = None,
        cartage_enrichment: CartageEnrichmentService | None = None,
        cartage_writeback: CartageWritebackService | None = None,
        edo_llm: EdoLlmService | None = None,
    ) -> None:
        self._cartage = cartage or CartageService(cache_factory=cache_factory or CacheFactory())
        self._cartage_llm = cartage_llm or CartageLlmService()
        self._cartage_enrichment = cartage_enrichment or CartageEnrichmentService(self._cartage)
        self._cartage_writeback = cartage_writeback or CartageWritebackService()
        self._edo = edo_llm or EdoLlmService()

    async def parse_edo(self, source: str | Path, *, model: str | None = None) -> EdoParseResult:
        return await self._edo.parse(source, model=model)

    async def parse_edo_text(self, text: str, *, model: str | None = None) -> EdoParseResult:
        return await self._edo.parse_text(text, model=model)

    async def parse_cartage_document(
        self,
        source: str | Path,
        *,
        model: str = "glm-5v-turbo",
        dict_values: CartageDictValues | None = None,
    ) -> CartageParseResult:
        return await self._cartage_llm.parse_document(source, model=model, dict_values=dict_values)

    async def parse_cartage_text(
        self,
        text: str,
        *,
        model: str = "glm-5v-turbo",
        dict_values: CartageDictValues | None = None,
    ) -> CartageParseResult:
        return await self._cartage_llm.parse_text(text, model=model, dict_values=dict_values)

    async def process_cartage_document(
        self,
        source: str | Path,
        *,
        model: str = "glm-5v-turbo",
        dict_values: CartageDictValues | None = None,
    ) -> CartageProcessResult:
        parsed = await self._cartage_llm.parse_document(source, model=model, dict_values=dict_values)
        return await self._cartage_enrichment.enrich(parsed)

    async def process_cartage_text(
        self,
        text: str,
        *,
        model: str = "glm-5v-turbo",
        dict_values: CartageDictValues | None = None,
    ) -> CartageProcessResult:
        parsed = await self._cartage_llm.parse_text(text, model=model, dict_values=dict_values)
        return await self._cartage_enrichment.enrich(parsed)

    async def process_and_writeback_cartage_document(
        self,
        source: str | Path,
        *,
        model: str = "glm-5v-turbo",
        dict_values: CartageDictValues | None = None,
    ) -> tuple[CartageProcessResult, CartageWritebackResult]:
        parsed = await self._cartage_llm.parse_document(source, model=model, dict_values=dict_values)
        enriched = await self._cartage_enrichment.enrich(parsed)
        writeback = await self._cartage_writeback.writeback(enriched)
        return enriched, writeback

    async def process_and_writeback_cartage_text(
        self,
        text: str,
        *,
        model: str = "glm-5v-turbo",
        dict_values: CartageDictValues | None = None,
    ) -> tuple[CartageProcessResult, CartageWritebackResult]:
        parsed = await self._cartage_llm.parse_text(text, model=model, dict_values=dict_values)
        enriched = await self._cartage_enrichment.enrich(parsed)
        writeback = await self._cartage_writeback.writeback(enriched)
        return enriched, writeback

    async def trigger_cartage_from_record(
        self,
        record_id: str,
        *,
        model: str = "glm-5v-turbo",
        dict_values: CartageDictValues | None = None,
    ) -> tuple[CartageProcessResult, CartageWritebackResult]:
        """Trigger Cartage processing from an existing Op-Cartage record.

        Downloads the Cartage Advise attachment, parses, enriches,
        and writes back with Record Status + Source Cartage fields.
        """
        from app.core.lark_bitable_value import extract_attachment_file_tokens, extract_cell_text
        from app.repository.cartage import CartageRepository

        cartage_repo = CartageRepository()
        record = await cartage_repo.get_record(record_id)

        existing_status = extract_cell_text(record.get("Record Status"))
        if existing_status:
            raise ValueError(f"Record {record_id} already processed (Record Status={existing_status})")

        advise_field = record.get("Cartage Advise")
        file_tokens = extract_attachment_file_tokens(advise_field)
        if not file_tokens:
            raise ValueError(f"No Cartage Advise attachment found in record {record_id}")

        tmp_path = await cartage_repo.download_attachment(file_tokens[0])
        try:
            parsed = await self._cartage_llm.parse_document(str(tmp_path), model=model, dict_values=dict_values)
            enriched = await self._cartage_enrichment.enrich(parsed)
            writeback = await self._cartage_writeback.writeback_from_record(enriched, source_record_id=record_id)
            return enriched, writeback
        finally:
            tmp_path.unlink(missing_ok=True)

    async def trigger_pending_cartage_records(
        self,
        *,
        model: str = "glm-5v-turbo",
        dict_values: CartageDictValues | None = None,
    ) -> list[CartageWritebackResult]:
        """Auto-discover and process all pending Op-Cartage records.

        Pending = Cartage Advise is not empty AND Record Status is empty.
        """
        from app.core.lark_bitable_value import extract_attachment_file_tokens, extract_cell_text
        from app.repository.cartage import CartageRepository

        cartage_repo = CartageRepository()
        records, _ = await cartage_repo.list_records(
            field_names=["Cartage Advise", "Record Status"],
            page_size=100,
        )

        pending = [r for r in records if r.get("Cartage Advise") and not extract_cell_text(r.get("Record Status"))]

        logger = logging.getLogger(__name__)
        results: list[CartageWritebackResult] = []
        for r in pending:
            rid = r["record_id"]
            advise_field = r.get("Cartage Advise")
            file_tokens = extract_attachment_file_tokens(advise_field)
            if not file_tokens:
                continue

            tmp_path = await cartage_repo.download_attachment(file_tokens[0])
            try:
                parsed = await self._cartage_llm.parse_document(str(tmp_path), model=model, dict_values=dict_values)
                enriched = await self._cartage_enrichment.enrich(parsed)
                writeback = await self._cartage_writeback.writeback_from_record(enriched, source_record_id=rid)
                results.append(writeback)
            except Exception as e:
                logger.error("Failed to process record %s: %s", rid, e)
            finally:
                tmp_path.unlink(missing_ok=True)

        return results

    def clear_cartage_cache(self) -> None:
        self._cartage.clear_cache()


llm_service = LLMService()

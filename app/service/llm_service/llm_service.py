from __future__ import annotations

from pathlib import Path

from app.cache.factory import CacheFactory
from app.service.cartage import CartageService
from app.service.llm_service.cartage.cartage_llm import CartageLlmService
from app.service.llm_service.cartage.enrichment import CartageEnrichmentService
from app.service.llm_service.cartage.process_schemas import CartageProcessResult
from app.service.llm_service.cartage.schemas import CartageDictValues, CartageParseResult
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
        edo_llm: EdoLlmService | None = None,
    ) -> None:
        self._cartage = cartage or CartageService(cache_factory=cache_factory or CacheFactory())
        self._cartage_llm = cartage_llm or CartageLlmService()
        self._cartage_enrichment = cartage_enrichment or CartageEnrichmentService(self._cartage)
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

    def clear_cartage_cache(self) -> None:
        self._cartage.clear_cache()


llm_service = LLMService()

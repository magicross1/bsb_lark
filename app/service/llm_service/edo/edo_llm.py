from __future__ import annotations

import asyncio
from pathlib import Path

from app.service.llm_service.edo.schemas import EdoParseResult


class EdoLlmService:
    """仅负责 EDO 的大模型解析。"""

    async def parse(self, source: str | Path, *, model: str | None = None) -> EdoParseResult:
        from app.service.llm_service.edo.parser import EdoParser

        parser = EdoParser(model=model)
        return await asyncio.to_thread(parser.parse, source)

    async def parse_text(self, text: str, *, model: str | None = None) -> EdoParseResult:
        from app.service.llm_service.edo.parser import EdoParser

        parser = EdoParser(model=model)
        return await asyncio.to_thread(parser.parse_text, text)

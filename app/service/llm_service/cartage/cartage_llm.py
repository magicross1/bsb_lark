from __future__ import annotations

import asyncio
from pathlib import Path

from app.service.llm_service.cartage.schemas import CartageDictValues, CartageParseResult

# 文档入口：按扩展名区分多模态文件与纯文本
_CARTAGE_IMAGE_EXTENSIONS = frozenset({".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tiff"})
_CARTAGE_TEXT_FILE_EXTENSIONS = frozenset({".txt", ".text"})


class CartageLlmService:
    """Cartage 解析编排：选择输入形态（文件路径 / 纯文本），不直接包含提示词或 JSON 映射逻辑。"""

    async def parse_document(
        self,
        source: str | Path,
        *,
        model: str = "glm-5v-turbo",
        dict_values: CartageDictValues | None = None,
    ) -> CartageParseResult:
        from app.service.llm_service.cartage.parser import CartageParser

        parser = CartageParser(model=model, dict_values=dict_values)
        path = Path(source) if not isinstance(source, Path) else source
        suffix = path.suffix.lower()

        if suffix in _CARTAGE_IMAGE_EXTENSIONS:
            return await asyncio.to_thread(parser.parse, path)
        if suffix in _CARTAGE_TEXT_FILE_EXTENSIONS:
            return await asyncio.to_thread(parser.parse_text_file, path)
        raise ValueError(f"Unsupported file type: {suffix}")

    async def parse_text(
        self,
        text: str,
        *,
        model: str = "glm-5v-turbo",
        dict_values: CartageDictValues | None = None,
    ) -> CartageParseResult:
        from app.service.llm_service.cartage.parser import CartageParser

        parser = CartageParser(model=model, dict_values=dict_values)
        return await asyncio.to_thread(parser.parse_text, text)

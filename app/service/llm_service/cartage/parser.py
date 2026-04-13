from __future__ import annotations

from zhipuai import ZhipuAI

from app.core.base_parser import BaseParser
from app.service.llm_service.cartage.prompts import CARTAGE_SYSTEM_PROMPT, CARTAGE_USER_HINT
from app.service.llm_service.cartage.result_builder import build_cartage_parse_result
from app.service.llm_service.cartage.schemas import CartageDictValues, CartageParseResult


class CartageParser(BaseParser):
    """智谱多模态调用 +提示词；结构化结果委托 :func:`build_cartage_parse_result`。"""

    system_prompt = CARTAGE_SYSTEM_PROMPT
    user_hint = CARTAGE_USER_HINT

    def __init__(
        self,
        client: ZhipuAI | None = None,
        *,
        model: str | None = None,
        dict_values: CartageDictValues | None = None,
    ) -> None:
        super().__init__(client, model=model)
        self._dict_values = dict_values

    def build_result(self, raw: str) -> CartageParseResult:
        return build_cartage_parse_result(raw, dict_values=self._dict_values)

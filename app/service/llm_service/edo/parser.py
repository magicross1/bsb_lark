from __future__ import annotations

from app.core.base_parser import BaseParser, extract_json_from_response
from app.service.llm_service.edo.prompts import EDO_USER_HINT, build_edo_system_prompt
from app.service.llm_service.edo.schemas import EdoDictValues, EdoEntry, EdoParseResult


class EdoParser(BaseParser):
    user_hint = EDO_USER_HINT

    def __init__(self, *, model: str | None = None, dict_values: EdoDictValues | None = None) -> None:
        super().__init__(model=model)
        self._dict_values = dict_values

    @property
    def system_prompt(self) -> str:
        return build_edo_system_prompt(self._dict_values)

    def build_result(self, raw: str) -> EdoParseResult:
        data = extract_json_from_response(raw)
        if data is None:
            return EdoParseResult(entries=[], raw_response=raw)

        entries: list[EdoEntry] = []
        for item in data.get("entries", []):
            cn = item.get("container_number", "")
            if cn:
                entries.append(
                    EdoEntry(
                        container_number=cn,
                        edo_pin=item.get("edo_pin"),
                        shipping_line=item.get("shipping_line"),
                        empty_park=item.get("empty_park"),
                        empty_park_address=item.get("empty_park_address"),
                    )
                )

        return EdoParseResult(entries=entries, raw_response=raw)

from __future__ import annotations

from app.core.base_parser import BaseParser
from app.service.llm_service.edo.prompts import EDO_SYSTEM_PROMPT, EDO_USER_HINT
from app.service.llm_service.edo.schemas import EdoEntry, EdoParseResult


class EdoParser(BaseParser):
    system_prompt = EDO_SYSTEM_PROMPT
    user_hint = EDO_USER_HINT

    def build_result(self, raw: str) -> EdoParseResult:
        from app.core.base_parser import extract_json_from_response

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
                    )
                )

        return EdoParseResult(entries=entries, raw_response=raw)

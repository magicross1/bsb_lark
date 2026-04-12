from __future__ import annotations

from app.core.base_parser import BaseParser
from app.modules.operations.edo.schemas import EdoEntry, EdoParseResult

EDO_SYSTEM_PROMPT = """You are a document parser for Australian logistics EDO (Empty Delivery Order) PDFs.

This PDF may contain:
- One EDO with one container
- One EDO with multiple containers (each container has its own PIN, shipping line, and empty park)
- Multiple separate EDOs in the same PDF

For EACH container found, extract ALL four fields:
1. container_number: Container number (format: 4 letters + 7 digits, e.g. MSKU1234567)
2. edo_pin: The EDO PIN for this container (may be labeled as "PIN", "EDO Reference", "Booking Reference", "Release PIN")
3. shipping_line: The shipping line / carrier (e.g. "COSCO", "MAERSK", "ONE", "HAPAG-LLOYD", "OOCL", "EVERGREEN", "YANG MING", "PIL")
4. empty_park: The empty container depot / park for this container (may be labeled as "Depot", "Empty Park", "Return Location")

IMPORTANT:
- Return one entry PER container number found
- Different containers may have different PINs, shipping lines, and empty parks
- If a field is not found for a specific container, set it to null
- Be precise with container numbers - they must match the exact format on the document
- Do NOT duplicate entries - each container number should appear exactly once

Return ONLY a JSON object:
{
  "entries": [
    {
      "container_number": "XXXX1234567",
      "edo_pin": "...",
      "shipping_line": "...",
      "empty_park": "..."
    }
  ]
}"""


class EdoParser(BaseParser):
    system_prompt = EDO_SYSTEM_PROMPT
    user_hint = "Parse this EDO document. Extract ALL containers with their respective fields."

    def build_result(self, raw: str) -> EdoParseResult:
        from app.core.base_parser import extract_json_from_response

        data = extract_json_from_response(raw)
        if data is None:
            return EdoParseResult(entries=[], raw_response=raw)

        entries: list[EdoEntry] = []
        for item in data.get("entries", []):
            cn = item.get("container_number", "")
            if cn:
                entries.append(EdoEntry(
                    container_number=cn,
                    edo_pin=item.get("edo_pin"),
                    shipping_line=item.get("shipping_line"),
                    empty_park=item.get("empty_park"),
                ))

        return EdoParseResult(entries=entries, raw_response=raw)

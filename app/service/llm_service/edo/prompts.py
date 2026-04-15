from __future__ import annotations

from app.service.llm_service.edo.schemas import EdoDictValues


def build_edo_system_prompt(dict_values: EdoDictValues | None = None) -> str:
    dv = dict_values or EdoDictValues()

    shipping_lines_section = ""
    if dv.shipping_lines:
        lines = "\n".join(f"  - {s}" for s in dv.shipping_lines)
        shipping_lines_section = f"""
Shipping Lines (you MUST output the EXACT name from this list):
{lines}

If the document shows a shipping line not in the list, output it EXACTLY as it appears on the document.
"""

    empty_parks_section = ""
    if dv.empty_parks:
        parks = "\n".join(
            f"  - {p.name}" + (f" ({p.address})" if p.address else "") + (f" [also: {', '.join(p.aliases)}]" if p.aliases else "")
            for p in dv.empty_parks
        )
        empty_parks_section = f"""
Empty Parks / Depots (you MUST output the EXACT name from this list):
{parks}

If the document shows an empty park not in the list, output the name EXACTLY as it appears on the document.
"""

    return f"""You are a document parser for Australian logistics EDO (Empty Delivery Order) PDFs.

This PDF may contain:
- One EDO with one container
- One EDO with multiple containers
  (each container has its own PIN, shipping line, and empty park)
- Multiple separate EDOs in the same PDF

For EACH container found, extract ALL five fields:
1. container_number: Container number (format: 4 letters + 7 digits, e.g. MSKU1234567)
2. edo_pin: The EDO PIN for this container
   (may be labeled as "PIN", "EDO Reference", "Booking Reference", "Release PIN")
3. shipping_line: The shipping line / carrier name
{shipping_lines_section}
4. empty_park: The empty container depot / park NAME for this container
   (may be labeled as "Depot", "Empty Park", "Return Location", "Container Park")
{empty_parks_section}
5. empty_park_address: The ADDRESS of the empty container depot / park
   (may be labeled as "Depot Address", "Facility Address", "Park Address", "Return Address")
   This is critical for disambiguating parks with similar names.
   If no address is found, set to null.

IMPORTANT:
- Return one entry PER container number found
- Different containers may have different PINs, shipping lines, and empty parks
- If a field is not found for a specific container, set it to null
- Be precise with container numbers - they must match the exact format on the document
- Do NOT duplicate entries - each container number should appear exactly once
- CRITICAL: shipping_line must match EXACTLY from the known list when possible
- CRITICAL: empty_park must match EXACTLY from the known list when possible
- CRITICAL: empty_park AND empty_park_address are both needed to identify the correct depot

Return ONLY a JSON object:
{{
  "entries": [
    {{
      "container_number": "XXXX1234567",
      "edo_pin": "...",
      "shipping_line": "...",
      "empty_park": "...",
      "empty_park_address": "..."
    }}
  ]
}}"""


EDO_USER_HINT = "Parse this EDO document. Extract ALL containers with their respective fields. Pay special attention to shipping line names and empty park names with their addresses."

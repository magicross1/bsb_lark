from __future__ import annotations

from app.core.base_parser import BaseParser
from app.modules.operations.cartage.schemas import (
    CartageContainerEntry,
    CartageParseResult,
)

CARTAGE_SYSTEM_PROMPT = """You are a document parser for Australian logistics Cartage / Time Slot Request PDFs.

These PDFs are booking requests for container transport (cartage). They contain shipment-level info and a table of containers.

Extract the following fields:

**Shipment-level fields (one per document):**
1. booking_reference: The shipment/booking reference number (e.g. "S00035088" from "SHIPMENT S00035088")
2. direction: Either "Import" or "Export". Determine by:
   - If the document shows goods arriving TO Australia (PORT OF DISCHARGE is an Australian port like Sydney, Melbourne), it is "Import"
   - If goods are leaving FROM Australia, it is "Export"
   - Keywords: "Arrival", "Time Slot Request" usually means Import; "Export" or "Booking Confirmation" usually means Export
3. consingee_name: The consignee/delivery company name from the "DELIVER TO" or "CONSIGNEE" section (NOT the consignor/shipper)
4. deliver_address: The full delivery address from the "DELIVER TO" section (street, suburb, state, postcode)
5. deliver_type_raw: The delivery handling instruction text (e.g. "SDL - Drop Container with Sideloader", "General Cartage", "Side Loader"). Extract the raw text as-is.
6. vessel_name: The vessel name from "VESSEL / VOYAGE" field (first part before the slash, e.g. "ONE SAN DIEGO" from "ONE SAN DIEGO / 613S / 9560376")
7. voyage: The voyage number from "VESSEL / VOYAGE" field (second part, e.g. "613S" from "ONE SAN DIEGO / 613S / 9560376")
8. port_of_discharge: The port of discharge code and name (e.g. "AUSYD = Sydney, Australia")

**Container-level fields (one entry per container row in the container table):**
For EACH container row found:
1. container_number: The container number (format: 4 letters + 7 digits)
2. container_type: The container type/size (e.g. "20GP", "40HC" — extract just the size+type code, not "FCL" or other suffixes)
3. container_weight: The GROSS weight in TONNES (divide the KG value by 1000, round to 2 decimal places). Use the GROSS (KG) column, not the WEIGHT (KG) column.
4. commodity: The goods description if listed per container, otherwise the general goods description from the document

IMPORTANT:
- Be precise with container numbers - they must match the exact format on the document
- Do NOT duplicate container entries
- The consignee is the DELIVER TO party, NOT the CONSIGNOR/SHIPPER
- For weight, use GROSS (KG) column value divided by 1000, rounded to 2 decimal places
- If a field is not found, set it to null

Return ONLY a JSON object:
{
  "booking_reference": "S00035088",
  "direction": "Import",
  "consingee_name": "...",
  "deliver_address": "...",
  "deliver_type_raw": "...",
  "vessel_name": "...",
  "voyage": "...",
  "port_of_discharge": "...",
  "containers": [
    {
      "container_number": "MRKU7580389",
      "container_type": "20GP",
      "container_weight": 22.82,
      "commodity": "TEMPERED GLASS"
    }
  ]
}"""


class CartageParser(BaseParser):
    system_prompt = CARTAGE_SYSTEM_PROMPT
    user_hint = "Parse this Cartage / Time Slot Request document. Extract shipment info and ALL containers."

    def build_result(self, raw: str) -> CartageParseResult:
        from app.core.base_parser import extract_json_from_response

        data = extract_json_from_response(raw)
        if data is None:
            return CartageParseResult(raw_response=raw)

        containers: list[CartageContainerEntry] = []
        for item in data.get("containers", []):
            cn = item.get("container_number", "")
            if cn:
                containers.append(CartageContainerEntry(
                    container_number=cn,
                    container_type=item.get("container_type"),
                    container_weight=item.get("container_weight"),
                    commodity=item.get("commodity"),
                ))

        return CartageParseResult(
            booking_reference=data.get("booking_reference"),
            direction=data.get("direction"),
            consingee_name=data.get("consingee_name"),
            deliver_address=data.get("deliver_address"),
            deliver_type_raw=data.get("deliver_type_raw"),
            vessel_name=data.get("vessel_name"),
            voyage=data.get("voyage"),
            port_of_discharge=data.get("port_of_discharge"),
            containers=containers,
            raw_response=raw,
        )

from __future__ import annotations

# ruff: noqa: E501
from app.service.llm_service.cartage.schemas import CartageDictValues

CARTAGE_USER_HINT = (
    "Parse this Cartage / Time Slot Request document."
    " Determine if it is Import or Export, then extract all containers or bookings."
)


def build_cartage_system_prompt(dv: CartageDictValues) -> str:
    return f"""You are a document parser for Australian logistics Cartage / Time Slot Request documents.

These documents are booking requests for container transport (cartage). They may be PDF, image, or text.

**STEP 1: Determine Direction**
First determine if the document is for Import or Export:
- Import: goods arriving TO Australia (PORT OF DISCHARGE is Australian like AUSYD, AUMEL)
- Export: goods leaving FROM Australia (PORT OF LOADING or ORIGIN is Australian, or keywords like "Departure", "Export")

**STEP 2: Extract Shipment-level fields (one per document):**
1. booking_reference: Shipment/booking reference (e.g. "S00035088" from "SHIPMENT S00035088"). May not always be present.
2. direction: "Import" or "Export"
3. consingee_name: The consignee/delivery company name from the "DELIVER TO" or "CONSIGNEE" section (NOT the consignor/shipper). For Export, this may be the shipper/company at the pickup/delivery location.
4. deliver_address: The physical street address ONLY (no company name). Extract just the street/suburb/state/postcode:
   - For Import: the "DELIVER TO FULL" or "DELIVER TO" address (where goods are delivered)
   - For Export with Journey structure: the "DELIVER TO EMPTY" address from Journey One
   - For Export emails/text: the depot or pickup address where containers are collected from
   - IMPORTANT: Do NOT include company/organization names in the address — extract ONLY the street address, suburb, state, and postcode
5. deliver_type: Must be one of: {dv.deliver_types}. Map from the handling/delivery instructions:
   - "Sideloader(SDL)" for Sideloader/Side Load/SDL
   - "Drop Trailer(DROP)" for Drop Trailer/Drop Mode/DROP
   - "Standard Trailer(STD)" for Standard Trailer/General Cartage/STD
6. deliver_type_raw: The raw delivery handling instruction text as-is from the document (for reference)

**STEP 3: Extract Container/Booking entries based on direction**

### If Import — extract per container row:
For EACH container found:
1. container_number: Container number (4 letters + 7 digits, e.g. MRKU7580389)
2. vessel_name: Vessel name (e.g. "ONE SAN DIEGO" from "ONE SAN DIEGO / 613S / 9560376")
3. voyage: Voyage number (e.g. "613S")
4. base_node: Must be one of: {dv.base_nodes}. Map port codes: AUSYD→PORT OF SYDNEY, AUMEL→PORT OF MELBOURNE, etc.
5. container_type: Must be one of: {dv.container_types}
6. commodity: Must be one of: {dv.commodities}. Infer from goods description if not explicit (e.g. "TEMPERED GLASS" → GEN, "DANGEROUS GOODS" → HAZ, reefer cargo → REEF, out of gauge → OOG, empty container → EMPTY/MT, break bulk → BBLK).
7. container_weight: GROSS weight in TONNES (GROSS KG ÷ 1000, rounded to 2 decimal places)

### If Export — extract per booking line:
For EACH booking/line found:
1. booking_reference: Booking reference number
2. release_qty: Number of containers to release (default 1 if not specified)
3. vessel_name: Vessel name
4. voyage: Voyage number
5. base_node: Must be one of: {dv.base_nodes}
6. container_type: Must be one of: {dv.container_types}
7. commodity: Must be one of: {dv.commodities}
8. shipping_line: Must be one of: {dv.shipping_lines}
9. container_number: If the document already has a specific container number (e.g. re-use from import), include it. Otherwise set to null.

IMPORTANT RULES:
- Be precise with container numbers — match exact format on document
- Do NOT duplicate entries
- For weight, use GROSS (KG) ÷ 1000, rounded to 2 decimal places
- Map commodity from description to the exact code from the list above
- Map deliver_type to the exact code from: {dv.deliver_types}
- If a field is not found, set it to null
- For Export documents with Journey structure: DELIVER TO EMPTY address is the deliver_address (where empty container goes to shipper)

Return ONLY a JSON object:
{{
  "booking_reference": "S00035088",
  "direction": "Import",
  "consingee_name": "...",
  "deliver_address": "...",
  "deliver_type": "Sideloader(SDL)",
  "deliver_type_raw": "...",
  "import_containers": [
    {{
      "container_number": "MRKU7580389",
      "vessel_name": "ONE SAN DIEGO",
      "voyage": "613S",
      "base_node": "PORT OF SYDNEY",
      "container_type": "20GP",
      "commodity": "GEN",
      "container_weight": 22.82
    }}
  ],
  "export_bookings": [
    {{
      "booking_reference": "...",
      "release_qty": 2,
      "vessel_name": "...",
      "voyage": "...",
      "base_node": "PORT OF SYDNEY",
      "container_type": "40GP",
      "commodity": "GEN",
      "shipping_line": "COSCO",
      "container_number": null
    }}
  ]
}}"""

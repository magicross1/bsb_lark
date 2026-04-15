from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


async def main() -> None:
    from app.entity.address import normalize_address, address_match_score
    from app.service.cartage import CartageService
    from app.core.lark_bitable_value import extract_cell_text

    svc = CartageService()
    addresses = await svc.list_addresses_for_matching()
    print(f"Total addresses: {len(addresses)}")

    query = "30 STATHAM AVE, NORTH ROCKS, NSW 2151"
    parsed = normalize_address(query)
    print(f"Normalized: street_number={parsed.street_number}, street_name={parsed.street_name}, suburb={parsed.suburb}, postcode={parsed.postcode}")

    for addr_raw in addresses[:20]:
        addr = extract_cell_text(addr_raw.get("Address", addr_raw.get("address", "")))
        if addr:
            addr_norm = normalize_address(str(addr))
            score = address_match_score(parsed, addr_norm)
            if score > 0.3:
                print(f"  Score={score:.3f}: {addr} (record_id={addr_raw['record_id']})")


if __name__ == "__main__":
    asyncio.run(main())

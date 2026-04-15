"""Find Op-Cartage records with Cartage Advise attachments."""
from __future__ import annotations

import asyncio

from app.repository.cartage import CartageRepository


async def main() -> None:
    cr = CartageRepository()
    records, _ = await cr.list_records(
        field_names=["Cartage Advise", "Record Status", "Booking Reference"],
        page_size=20,
    )
    for r in records:
        rid = r["record_id"]
        br = r.get("Booking Reference", "N/A")
        advise = r.get("Cartage Advise")
        status = r.get("Record Status", "")
        has_advise = bool(advise)
        print(f"  {rid}: BR={br}, has_advise={has_advise}, status={status}")

    pending = [
        r for r in records
        if r.get("Cartage Advise") and not r.get("Record Status")
    ]
    print(f"\nTotal: {len(records)}, with advise: {sum(1 for r in records if r.get('Cartage Advise'))}, pending (advise+no status): {len(pending)}")
    for r in pending:
        print(f"  >>> {r['record_id']}")


if __name__ == "__main__":
    asyncio.run(main())

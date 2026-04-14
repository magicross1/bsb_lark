"""Delete export test records from Bitable."""
from __future__ import annotations

import asyncio

from app.repository.cartage import CartageRepository
from app.repository.export_ import ExportRepository


async def main() -> None:
    cr = CartageRepository()
    er = ExportRepository()
    filt = 'CurrentValue.[Booking Reference]="RSG20811"'

    c, _ = await cr.list_records(filter_expr=filt, page_size=50)
    for r in c:
        await cr.delete_record(r["record_id"])
        print(f"Deleted Cartage {r['record_id']}")

    e, _ = await er.list_records(filter_expr=filt, page_size=50)
    for r in e:
        await er.delete_record(r["record_id"])
        print(f"Deleted Export {r['record_id']}")


if __name__ == "__main__":
    asyncio.run(main())

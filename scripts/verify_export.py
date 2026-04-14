"""Verify Export writeback records in Bitable."""
from __future__ import annotations

import asyncio

from app.repository.cartage import CartageRepository
from app.repository.export_ import ExportRepository


async def main() -> None:
    cr = CartageRepository()
    er = ExportRepository()

    cartage_records, _ = await cr.list_records(
        filter_expr='OR(CurrentValue.[Booking Reference]="RSG20811-1", CurrentValue.[Booking Reference]="RSG20811-2")',
        page_size=50,
    )
    print(f"Op-Cartage records: {len(cartage_records)}")
    for r in cartage_records:
        f = r.get("fields", r)
        print(f"  {r['record_id']}: BR={f.get('Booking Reference')}, "
              f"Consingee={f.get('Consingnee Name', [])}, "
              f"DC={f.get('Deliver Config', [])}, "
              f"Export={f.get('Export Booking', [])}")

    export_records, _ = await er.list_records(
        filter_expr='OR(CurrentValue.[Booking Reference]="RSG20811-1", CurrentValue.[Booking Reference]="RSG20811-2")',
        page_size=50,
    )
    print(f"\nOp-Export records: {len(export_records)}")
    for r in export_records:
        f = r.get("fields", r)
        print(f"  {r['record_id']}: BR={f.get('Booking Reference')}, "
              f"ReleaseQty={f.get('Release Qty')}, "
              f"CN={f.get('Container Number')}, "
              f"CT={f.get('Container Type')}, "
              f"Commodity={f.get('Commodity')}, "
              f"Vessel={f.get('FULL Vessel Name', [])}, "
              f"Cartage={f.get('Op-Cartage', [])}")


if __name__ == "__main__":
    asyncio.run(main())

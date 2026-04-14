"""Cleanup test records from failed writeback runs."""
from __future__ import annotations

import asyncio

from app.repository.cartage import CartageRepository
from app.repository.import_ import ImportRepository
from app.repository.export_ import ExportRepository
from app.common.lark_tables import T


async def main() -> None:
    cr = CartageRepository()
    ir = ImportRepository()
    er = ExportRepository()

    cartage_records, _ = await cr.list_records(
        filter_expr='CurrentValue.[Booking Reference]="SHEXP26030118"',
        page_size=50,
    )
    print(f"Op-Cartage records: {len(cartage_records)}")
    for r in cartage_records:
        print(f"  {r['record_id']}: {r.get('fields', r)}")

    import_containers = ["CSNU1805247", "OOLU0262610", "CSNU1053242", "CSLU2258086", "FTAU2370616"]
    for cn in import_containers:
        records, _ = await ir.list_records(
            filter_expr=f'CurrentValue.[Container Number]="{cn}"',
            page_size=5,
        )
        if records:
            print(f"Op-Import {cn}: {records[0]['record_id']} fields={records[0].get('fields', records[0])}")

    export_records, _ = await er.list_records(
        filter_expr='CurrentValue.[Booking Reference]="SHEXP26030118"',
        page_size=50,
    )
    print(f"Op-Export records: {len(export_records)}")

    vessel_repo = __import__("app.common.lark_repository", fromlist=["LarkRepository"]).LarkRepository()
    vessel_repo.__class__.table_id = T.op_vessel_schedule.id
    vs_records, _ = await vessel_repo.list_records(
        filter_expr='CurrentValue.[Vessel Name]="FENG NIAN 361"',
        page_size=10,
    )
    print(f"\nVessel Schedule records: {len(vs_records)}")
    for r in vs_records:
        print(f"  {r['record_id']}: {r.get('fields', r)}")


if __name__ == "__main__":
    asyncio.run(main())

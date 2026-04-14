"""Delete test records from Bitable."""
from __future__ import annotations

import asyncio

from app.repository.cartage import CartageRepository
from app.repository.import_ import ImportRepository
from app.common.lark_tables import T
from app.common.lark_repository import LarkRepository


async def main() -> None:
    cr = CartageRepository()
    ir = ImportRepository()

    cartage_records, _ = await cr.list_records(
        filter_expr='CurrentValue.[Booking Reference]="SHEXP26030118"',
        page_size=50,
    )
    for r in cartage_records:
        await cr.delete_record(r["record_id"])
        print(f"Deleted Op-Cartage {r['record_id']}")

    import_containers = ["CSNU1805247", "OOLU0262610", "CSNU1053242", "CSLU2258086", "FTAU2370616"]
    for cn in import_containers:
        records, _ = await ir.list_records(
            filter_expr=f'CurrentValue.[Container Number]="{cn}"',
            page_size=5,
        )
        for r in records:
            await ir.delete_record(r["record_id"])
            print(f"Deleted Op-Import {r['record_id']} ({cn})")

    vs_class = type("VSRepo", (LarkRepository,), {"table_id": T.op_vessel_schedule.id})
    vs_repo = vs_class()
    vs_records, _ = await vs_repo.list_records(
        filter_expr='CurrentValue.[Vessel Name]="FENG NIAN 361"',
        page_size=10,
    )
    for r in vs_records:
        existing = await vs_repo.list_records(
            filter_expr=f'CurrentValue.[Voyage]="{r.get("fields", r).get("Voyage", "")}"',
            page_size=5,
        )
        if len(existing[0]) > 1 or (existing[0] and existing[0][0]["record_id"] == r["record_id"]):
            voyage = r.get("fields", r).get("Voyage", "")
            base_node_text = ""
            bn = r.get("fields", r).get("Base Node", [])
            if bn and isinstance(bn, list) and bn:
                base_node_text = bn[0].get("text", "")
            print(f"Keeping Vessel Schedule {r['record_id']} voyage={voyage} base_node={base_node_text}")


if __name__ == "__main__":
    asyncio.run(main())

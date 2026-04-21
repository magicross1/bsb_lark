from __future__ import annotations

import asyncio
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

from app.core.lark_bitable_value import extract_cell_text
from app.repository.vessel_schedule import VesselScheduleRepository
from app.service.sync.vessel_sync import VesselSyncService, BATCH_CONDITIONS


async def main():
    repo = VesselScheduleRepository()
    cond = BATCH_CONDITIONS["pending_arrival"]

    all_records = await repo.list_all_records(field_names=cond.required_fields)
    pending = [r for r in all_records if cond.filter_fn(r)]

    print(f"Total records: {len(all_records)}, Pending: {len(pending)}\n")

    for r in pending:
        vn = extract_cell_text(r.get("Vessel Name"))
        vy = extract_cell_text(r.get("Voyage"))
        bn = extract_cell_text(r.get("Base Node"))
        print(f"  record_id={r['record_id']}, vessel={vn}, voyage={vy}, base_node={bn}")

    svc = VesselSyncService()
    grouped = svc._group_by_vessel_key(pending)
    print(f"\nGrouped into {len(grouped)} vessel keys:")
    for (vn, vy, bn), records in grouped.items():
        print(f"  ({vn}, {vy}, {bn}) → {len(records)} records")

    result = await svc.sync_batch(condition="pending_arrival")
    print(f"\nResult: {json.dumps(result.model_dump(), indent=2, default=str)}")


if __name__ == "__main__":
    asyncio.run(main())

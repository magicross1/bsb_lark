from __future__ import annotations

import asyncio
import json

from app.repository.vessel_schedule import VesselScheduleRepository
from app.service.vessel_sync import VesselSyncService


async def main():
    repo = VesselScheduleRepository()

    filter_expr = 'AND(CurrentValue.[Vessel Name]="COSCO HONG KONG", CurrentValue.[Voyage]="205S")'
    records, _ = await repo.list_records(
        filter_expr=filter_expr,
        field_names=["Vessel Name", "Voyage", "Base Node", "ETA", "ETD", "Last Free", "Terminal Name", "Actual Arrival"],
        page_size=5,
    )

    if not records:
        print("No records found")
        return

    for r in records:
        print(f'record_id={r["record_id"]}')
        for k, v in r.items():
            if k != "record_id":
                print(f"  {k}: {v}")

    record_id = records[0]["record_id"]
    print(f"\n--- Syncing {record_id} ---\n")

    svc = VesselSyncService()
    result = await svc.sync_single(record_id)
    print(json.dumps(result.model_dump(), indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())

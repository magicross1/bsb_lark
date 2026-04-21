from __future__ import annotations

import asyncio
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

from app.core.lark_bitable_value import extract_cell_text
from app.repository.vessel_schedule import VesselScheduleRepository
from app.service.sync.vessel_sync import VesselSyncService, BATCH_CONDITIONS


async def main():
    svc = VesselSyncService()
    cond = BATCH_CONDITIONS["pending_arrival"]

    all_records = await svc._repo.list_all_records(field_names=cond.required_fields)
    pending = [r for r in all_records if cond.filter_fn(r)]

    grouped = svc._group_by_vessel_key(pending)
    print(f"Groups: {list(grouped.keys())}")

    vessel_data_map = await svc._fetch_vessels_concurrent(grouped)
    for key, data in vessel_data_map.items():
        if data:
            print(f"  {key}: ETA={data.get('ETA')}, valid={svc._has_valid_data(data)}")
        else:
            print(f"  {key}: None")


if __name__ == "__main__":
    asyncio.run(main())

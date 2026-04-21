from __future__ import annotations

import asyncio
import json

from app.service.vessel_sync import VesselSyncService


async def main():
    svc = VesselSyncService()
    result = await svc.sync_batch(condition="pending_arrival", base_node="PORT OF SYDNEY", limit=10)
    print(json.dumps(result.model_dump(), indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())

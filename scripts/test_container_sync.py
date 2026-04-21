from __future__ import annotations

import asyncio
import json

from app.service.sync.container_sync import ContainerSyncService


async def main():
    svc = ContainerSyncService()
    result = await svc.sync(["OOCU9024853"])
    print(json.dumps(result.model_dump(), indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())

from __future__ import annotations

import asyncio
import json

from app.component.OneStopProvider import OneStopProvider


async def main():
    onestop = OneStopProvider.get_instance()
    containers = ["BMOU5326901", "CSLU1872886", "TGBU4369245"]
    result = await onestop.match_containers_info_by_list(containers)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())

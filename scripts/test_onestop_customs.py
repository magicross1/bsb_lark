from __future__ import annotations

import asyncio
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

from app.component.OneStopProvider import OneStopProvider


async def main():
    onestop = OneStopProvider.get_instance()
    containers = ["TGBU8802097", "ONEU3058065", "BSIU8024808", "OOCU8890410"]
    result = await onestop.customs_cargo_status_search(containers)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())

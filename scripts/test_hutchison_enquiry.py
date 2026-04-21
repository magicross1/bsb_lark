from __future__ import annotations

import asyncio
import json
import sys

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding='utf-8')

from app.component.HutchisonPortsProvider import HutchisonPortsProvider


async def main():
    provider = HutchisonPortsProvider()
    containers = ["OOCU9024853", "TGBU4369245", "UETU6934280", "OOLU9589239", "TGBU8802097"]
    result = await provider.container_enquiry_by_list(containers)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())

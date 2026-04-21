from __future__ import annotations

import asyncio
import json
import sys

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

from app.component.OneStopProvider import OneStopProvider
from app.component.HutchisonPortsProvider import HutchisonPortsProvider

CONTAINERS = ["OOCU9024853", "TGBU4369245", "UETU6934280", "OOLU9589239", "TGBU8802097"]


async def main():
    print("=" * 60)
    print("1-Stop match_containers_info_by_list")
    print("=" * 60)
    onestop = OneStopProvider.get_instance()
    r1 = await onestop.match_containers_info_by_list(CONTAINERS)
    print(json.dumps(r1, indent=2, default=str))

    print()
    print("=" * 60)
    print("1-Stop customs_cargo_status_search")
    print("=" * 60)
    r2 = await onestop.customs_cargo_status_search(CONTAINERS)
    print(json.dumps(r2, indent=2, default=str))

    print()
    print("=" * 60)
    print("Hutchison container_enquiry_by_list")
    print("=" * 60)
    hutchison = HutchisonPortsProvider()
    r3 = await hutchison.container_enquiry_by_list(CONTAINERS)
    print(json.dumps(r3, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())

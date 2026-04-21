from __future__ import annotations

import asyncio
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

from app.component.OneStopProvider import OneStopProvider


async def main():
    onestop = OneStopProvider.get_instance()
    vessels = {
        "COSCO ROTTERDAM": ("COSCO ROTTERDAM", "209S"),
        "MAERSK FUKUOKA": ("MAERSK FUKUOKA", "612S"),
        "TS CHENNAI": ("TS CHENNAI", "2602S"),
        "COSCO SINGAPORE": ("COSCO SINGAPORE", "198S"),
    }

    for base_node in ["PORT OF SYDNEY", "PORT OF MELBOURNE"]:
        print(f"\n=== {base_node} ===")
        relevant = {k: v for k, v in vessels.items()
                    if (base_node == "PORT OF SYDNEY" and k in ["COSCO ROTTERDAM", "MAERSK FUKUOKA"])
                    or (base_node == "PORT OF MELBOURNE" and k in ["TS CHENNAI", "COSCO SINGAPORE"])}
        if not relevant:
            continue
        result = await onestop.vessel_search_by_name_list(relevant, base_node)
        for name, data in result.items():
            print(f"  {name}: ETA={data.get('ETA')}, ETD={data.get('ETD')}, Terminal={data.get('Terminal Full Name')}")


if __name__ == "__main__":
    asyncio.run(main())

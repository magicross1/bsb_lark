from __future__ import annotations

import asyncio
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

from app.component.OneStopProvider import OneStopProvider


async def main():
    onestop = OneStopProvider.get_instance()

    # TS CHENNAI
    result1 = await onestop.vessel_search_by_name_list(
        {"TS CHENNAI": ("TS CHENNAI", "2602S")},
        base_node="PORT OF MELBOURNE",
    )
    print(f"TS CHENNAI (MEL): {json.dumps(result1, indent=2)}")

    # COSCO SINGAPORE
    result2 = await onestop.vessel_search_by_name_list(
        {"COSCO SINGAPORE": ("COSCO SINGAPORE", "198S")},
        base_node="PORT OF MELBOURNE",
    )
    print(f"COSCO SINGAPORE (MEL): {json.dumps(result2, indent=2)}")


if __name__ == "__main__":
    asyncio.run(main())

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


async def main() -> None:
    from app.component.OneStopProvider import OneStopProvider

    provider = OneStopProvider.get_instance()

    result = await provider.vessel_search_by_name_list(
        vessel_map_dict={
            "COSCO HONG KONG": ("COSCO HONG KONG", "205S"),
        },
        base_node="PORT OF SYDNEY",
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))

    await provider.session.close()


if __name__ == "__main__":
    asyncio.run(main())

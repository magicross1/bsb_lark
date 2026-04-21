from __future__ import annotations

import asyncio
import json
import sys

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

from app.repository.import_ import ImportRepository


async def main():
    repo = ImportRepository()
    records, _ = await repo.list_records(
        filter_expr='CurrentValue.[Container Number]="OOCU9024853"',
        field_names=["Container Number", "Gross Weight"],
        page_size=1,
    )
    for r in records:
        gw = r.get("Gross Weight")
        print(f"Gross Weight value: {gw!r}, type: {type(gw).__name__}")


if __name__ == "__main__":
    asyncio.run(main())

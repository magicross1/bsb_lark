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
        field_names=["Container Number", "Clear Status", "ISO", "Gross Weight", "Quarantine"],
        page_size=1,
    )
    for r in records:
        print(json.dumps(r, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())

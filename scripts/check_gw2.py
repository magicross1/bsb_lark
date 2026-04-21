from __future__ import annotations

import asyncio
import sys

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

from app.common.lark_repository import LarkRepository
from app.common.lark_tables import T


async def main():
    repo = LarkRepository()
    repo.table_id = T.op_import.id
    records = await repo.list_all_records(field_names=["Container Number", "Gross Weight"])
    for r in records[:5]:
        cn = r.get("Container Number")
        gw = r.get("Gross Weight")
        if gw and cn:
            print(f"  {cn}: Gross Weight = {gw!r} (type: {type(gw).__name__})")


if __name__ == "__main__":
    asyncio.run(main())

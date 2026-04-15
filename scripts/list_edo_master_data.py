from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.lark_bitable_value import extract_cell_text
from app.repository.empty_park import EmptyParkRepository
from app.repository.shipping_line import ShippingLineRepository


async def main() -> None:
    print("=== MD-Shipping Line ===")
    sl_repo = ShippingLineRepository()
    sl_records = await sl_repo.list_all_records(field_names=["Shipping Line", "Shiiping Line Short Name"])
    for rec in sl_records:
        name = extract_cell_text(rec.get("Shipping Line"))
        short = extract_cell_text(rec.get("Shiiping Line Short Name"))
        print(f"  {name:30} | short: {short}")

    print(f"\n=== MD-Empty Park ({len(sl_records)} lines above) ===")
    ep_repo = EmptyParkRepository()
    ep_records = await ep_repo.list_all_records(field_names=["Empty Park", "Facility Address"])
    for rec in ep_records:
        name = extract_cell_text(rec.get("Empty Park"))
        addr = extract_cell_text(rec.get("Facility Address"))
        print(f"  {name:40} | {addr}")

    print(f"\nTotal Shipping Lines: {len(sl_records)}")
    print(f"Total Empty Parks: {len(ep_records)}")


if __name__ == "__main__":
    asyncio.run(main())

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.lark_bitable_value import extract_cell_text
from app.repository.import_ import ImportRepository


async def main() -> None:
    repo = ImportRepository()
    recs, _ = await repo.list_records(
        field_names=["Container Number", "EDO File", "Record Status"],
        page_size=50,
    )
    print(f"Total records: {len(recs)}\n")
    for rec in recs:
        rid = rec["record_id"]
        cn = extract_cell_text(rec.get("Container Number")) or ""
        has_edo = bool(rec.get("EDO File"))
        status = extract_cell_text(rec.get("Record Status")) or ""
        flag = " <<<" if has_edo and not status else ""
        print(f"{rid:20} CTN={cn:20} EDO={has_edo}  Status={status}{flag}")


if __name__ == "__main__":
    asyncio.run(main())

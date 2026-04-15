from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.repository.import_ import ImportRepository


async def main() -> None:
    repo = ImportRepository()
    record_id = sys.argv[1] if len(sys.argv) > 1 else "recvghPS83A1Ii"
    await repo.update_record(record_id, {"Record Status": "", "Source EDO": []})
    print(f"Cleared Record Status + Source EDO for {record_id}")


if __name__ == "__main__":
    asyncio.run(main())

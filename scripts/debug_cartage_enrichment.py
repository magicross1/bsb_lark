from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


async def main() -> None:
    from app.service.llm_service.llm_service import LLMService

    record_id = sys.argv[1] if len(sys.argv) > 1 else "recvgMkopfDD5n"
    svc = LLMService()

    enriched, writeback = await svc.trigger_cartage_from_record(record_id)

    print(f"deliver_address: {enriched.deliver_address}")
    print(f"deliver_type: {enriched.deliver_type}")
    print(f"consingee_name: {enriched.consingee_name}")
    print(f"address_match: {enriched.address_match}")
    print(f"address_needs_review: {enriched.address_needs_review}")
    print(f"direction: {enriched.direction}")
    print(f"booking_reference: {enriched.booking_reference}")
    print(f"import_containers: {len(enriched.import_containers)}")


if __name__ == "__main__":
    asyncio.run(main())

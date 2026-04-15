from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


async def main() -> None:
    from app.repository.cartage import CartageRepository
    from app.core.lark_bitable_value import extract_attachment_file_tokens, extract_cell_text
    from app.service.llm_service.llm_service import LLMService

    record_id = sys.argv[1] if len(sys.argv) > 1 else "recvgMkopfDD5n"

    cartage_repo = CartageRepository()
    record = await cartage_repo.get_record(record_id)

    existing_status = extract_cell_text(record.get("Record Status"))
    if existing_status:
        await cartage_repo.update_record(record_id, {"Record Status": "", "Source Cartage": []})

    advise_field = record.get("Cartage Advise")
    file_tokens = extract_attachment_file_tokens(advise_field)
    tmp_path = await cartage_repo.download_attachment(file_tokens[0])

    try:
        svc = LLMService()
        parsed = await svc._cartage_llm.parse_document(str(tmp_path))
        print("=== PARSE RESULT ===")
        print(f"deliver_address: {parsed.deliver_address!r}")
        print(f"consingee_name: {parsed.consingee_name!r}")
        print(f"deliver_type: {parsed.deliver_type!r}")
        print(f"direction: {parsed.direction!r}")
        print(f"booking_reference: {parsed.booking_reference!r}")
        print(f"import_containers: {len(parsed.import_containers)}")
    finally:
        tmp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(main())

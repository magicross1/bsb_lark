"""
EDO Trigger E2E 本地测试

用法:
  uv run python scripts/test_edo_trigger.py <op_import_record_id>
  uv run python scripts/test_edo_trigger.py          # 自动发现待处理记录

环境变量:
  ZHIPUAI_API_KEY, LARK_APP_ID, LARK_APP_SECRET, LARK_BITABLE_APP_TOKEN
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.service.llm_service.edo.schemas import EdoProcessResult
from app.service.llm_service.edo.writeback_schemas import EdoWritebackResult


def print_result(
    enriched: EdoProcessResult,
    writeback: EdoWritebackResult,
    record_id: str,
) -> None:
    print(f"\n{'='*60}")
    print(f"Source Record: {record_id}")
    print(f"{'-'*60}")
    print(f"Parsed entries: {len(enriched.entries)}")
    for i, entry in enumerate(enriched.entries, 1):
        print(f"  [{i}] CTN: {entry.container_number}")
        print(f"      PIN: {entry.edo_pin or '(none)'}")
        sl = entry.shipping_line or "(none)"
        sl_match = f" -> {entry.shipping_line_match.name} ({entry.shipping_line_match.record_id})" if entry.shipping_line_match else " [NOT MATCHED]"
        print(f"      Shipping Line: {sl}{sl_match}")
        ep = entry.empty_park or "(none)"
        ep_match = f" -> {entry.empty_park_match.name} ({entry.empty_park_match.record_id})" if entry.empty_park_match else " [NOT MATCHED]"
        print(f"      Empty Park: {ep}{ep_match}")

    print(f"\nWriteback Results:")
    print(f"  Updated: {len(writeback.updated)}")
    for ref in writeback.updated:
        print(f"    - {ref.container_number}: {ref.status} (record {ref.record_id})")
    print(f"  Skipped: {len(writeback.skipped)}")
    for ref in writeback.skipped:
        print(f"    - {ref.container_number}: {ref.status} (record {ref.record_id})")


async def run_single(record_id: str) -> None:
    from app.service.llm_service.llm_service import LLMService

    svc = LLMService()
    enriched, writeback = await svc.trigger_edo_from_record(record_id)
    print_result(enriched, writeback, record_id)


async def run_pending() -> None:
    from app.service.llm_service.llm_service import LLMService

    svc = LLMService()
    results = await svc.trigger_pending_edo_records()
    print(f"\nProcessed {len(results)} pending records")


def main() -> None:
    from app.config.app_settings import settings

    if not settings.ZHIPUAI_API_KEY:
        print("Error: ZHIPUAI_API_KEY not set in .env")
        sys.exit(1)

    if len(sys.argv) > 1:
        record_id = sys.argv[1]
        asyncio.run(run_single(record_id))
    else:
        asyncio.run(run_pending())


if __name__ == "__main__":
    main()

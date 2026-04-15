"""Test trigger-based Cartage processing from an existing Op-Cartage record.

Usage:
    PYTHONUTF8=1 uv run python -m scripts.test_trigger_cartage --record-id recXXXXXX
"""

from __future__ import annotations

import argparse
import asyncio
import json

from app.service.llm_service.llm_service import LLMService


async def main() -> None:
    parser = argparse.ArgumentParser(description="Test trigger Cartage from Op-Cartage record")
    parser.add_argument("--record-id", required=True, help="Op-Cartage record_id with Cartage Advise attachment")
    parser.add_argument("--model", type=str, default="glm-5v-turbo")
    args = parser.parse_args()

    llm = LLMService()
    enriched, writeback = await llm.trigger_cartage_from_record(args.record_id, model=args.model)

    print("\n=== Enriched Result ===")
    print(json.dumps(enriched.model_dump(), ensure_ascii=False, indent=2))

    print("\n=== Writeback Result ===")
    print(json.dumps(writeback.model_dump(), ensure_ascii=False, indent=2))

    print(f"\nCartage refs: {len(writeback.cartage_refs)}")
    print(f"Imports:      {len(writeback.imports)}")
    print(f"Exports:      {len(writeback.exports)}")
    print(f"Skipped:      {len(writeback.skipped)}")


if __name__ == "__main__":
    asyncio.run(main())

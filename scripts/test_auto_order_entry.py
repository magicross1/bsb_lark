"""End-to-end test: Cartage auto-order-entry flow.

Parse PDF -> Enrich (address match) -> Writeback (Bitable records)

Usage:
    PYTHONUTF8=1 uv run python -m scripts.test_auto_order_entry
    PYTHONUTF8=1 uv run python -m scripts.test_auto_order_entry --dry-run
    PYTHONUTF8=1 uv run python -m scripts.test_auto_order_entry --file path/to/file.pdf
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from app.service.llm_service.llm_service import LLMService

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "tests" / "cartage_samples"


def _sep(title: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print("=" * 70)


async def run_single(
    llm: LLMService,
    source: str | Path,
    dry_run: bool,
    model: str = "glm-5v-turbo",
) -> None:
    source_name = Path(source).name if isinstance(source, (str, Path)) else "<text>"
    _sep(f"Step 1: Parse - {source_name}")

    parsed = await llm.parse_cartage_document(source, model=model)
    print(json.dumps(parsed.model_dump(), ensure_ascii=False, indent=2))

    _sep("Step 2: Enrich (address + deliver_config + consingee)")
    enriched = await llm._cartage_enrichment.enrich(parsed)
    print(json.dumps(enriched.model_dump(), ensure_ascii=False, indent=2))

    if enriched.address_match:
        print("\n  Address Match:")
        print(f"    record_id  = {enriched.address_match.record_id}")
        print(f"    address    = {enriched.address_match.address}")
        print(f"    score      = {enriched.address_match.score}")
        print(f"    review     = {enriched.address_needs_review}")
        print(f"    dc_id      = {enriched.address_match.deliver_config_id}")
        print(f"    dc_text    = {enriched.address_match.deliver_config}")
        print(f"    cons_id    = {enriched.address_match.consingee_id}")
        print(f"    cons_name  = {enriched.address_match.consingee_name}")
    else:
        print("\n  No address match found!")

    print(f"\n  Import containers: {len(enriched.import_containers)}")
    for i, c in enumerate(enriched.import_containers):
        print(f"    [{i}] {c.container_number} | {c.container_type} | "
              f"{c.container_weight}kg | {c.vessel_name} {c.voyage}")

    print(f"  Export bookings: {len(enriched.export_bookings)}")
    for i, b in enumerate(enriched.export_bookings):
        print(f"    [{i}] {b.booking_reference} | qty={b.release_qty} | {b.container_type} | {b.shipping_line}")

    if dry_run:
        _sep("DRY RUN - skipping writeback")
        return

    _sep("Step 3: Writeback to Bitable")
    writeback = await llm._cartage_writeback.writeback(enriched)

    for i, ref in enumerate(writeback.cartage_refs):
        print(f"  Op-Cartage[{i}]: record_id={ref.record_id}")
    for i, ref in enumerate(writeback.imports):
        print(f"  Op-Import[{i}]: record_id={ref.record_id}")
    for i, ref in enumerate(writeback.exports):
        print(f"  Op-Export[{i}]: record_id={ref.record_id}")

    _sep("Summary")
    print(f"  Source:      {source_name}")
    print(f"  Direction:   {enriched.direction}")
    print(f"  Booking:     {enriched.booking_reference}")
    print(f"  Address:     {enriched.address_match.address if enriched.address_match else 'N/A'}")
    print(f"  Consingee:   {enriched.address_match.consingee_name if enriched.address_match else 'N/A'}")
    print(f"  Cartages:    {len(writeback.cartage_refs)} records")
    print(f"  Imports:     {len(writeback.imports)} records")
    print(f"  Exports:     {len(writeback.exports)} records")
    if writeback.skipped:
        print(f"  Skipped:     {len(writeback.skipped)} containers")
        for s in writeback.skipped:
            print(f"    - {s.container_number}: {s.reason}")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Cartage auto-order-entry E2E test")
    parser.add_argument("--dry-run", action="store_true", help="Parse + enrich only, skip writeback")
    parser.add_argument("--file", type=str, default=None, help="Path to PDF/image/TXT file")
    parser.add_argument("--model", type=str, default="glm-5v-turbo")
    args = parser.parse_args()

    llm = LLMService()

    if args.file:
        await run_single(llm, args.file, args.dry_run, args.model)
        return

    sample_files = sorted(SAMPLES_DIR.glob("*"))
    sample_files = [f for f in sample_files if f.suffix.lower() in {".pdf", ".png", ".jpg", ".jpeg", ".txt", ".text"}]

    if not sample_files:
        print(f"No sample files found in {SAMPLES_DIR}")
        sys.exit(1)

    print(f"Found {len(sample_files)} sample files in {SAMPLES_DIR}")
    for f in sample_files:
        print(f"  - {f.name}")

    for f in sample_files:
        await run_single(llm, str(f), args.dry_run, args.model)
        llm.clear_cartage_cache()


if __name__ == "__main__":
    asyncio.run(main())

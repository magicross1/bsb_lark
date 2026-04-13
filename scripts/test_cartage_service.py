"""
Cartage Service 完整流程测试脚本

测试 AI 解析 → 地址归一化 → Bitable 地址匹配 → Deliver Config → Consingee

用法:
  uv run python scripts/test_cartage_service.py tests/cartage_samples/
  uv run python scripts/test_cartage_service.py "tests/cartage_samples/some file.pdf"
  uv run python scripts/test_cartage_service.py --text "SHIPMENT S00035088 ..."
  uv run python scripts/test_cartage_service.py tests/cartage_samples/ --model glm-4v-flash

环境变量:
  ZHIPUAI_API_KEY       - 智谱 API Key (必填)
  LARK_APP_ID           - Lark App ID (必填)
  LARK_APP_SECRET       - Lark App Secret (必填)
  LARK_BITABLE_APP_TOKEN - Bitable App Token (必填)
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.service.llm_service.cartage.process_schemas import CartageProcessResult


def print_process_result(name: str, result: CartageProcessResult, elapsed: float, model: str) -> None:
    direction = result.direction or "(unknown)"
    status = "OK" if result.booking_reference or result.import_containers or result.export_bookings else "EMPTY"
    print(f"\n{'=' * 70}")
    print(f"Source: {name}")
    print(f"Model:  {model}")
    print(f"Status: {status} | Direction: {direction} | Time: {elapsed:.1f}s")
    print(f"{'-' * 70}")
    print(f"  Booking Ref:  {result.booking_reference or '(none)'}")
    print(f"  Consingee:    {result.consingee_name or '(none)'}")
    print(f"  Deliver Addr: {result.deliver_address or '(none)'}")
    print(f"  Deliver Type: {result.deliver_type or '(none)'} ({result.deliver_type_raw or '-'})")

    print(f"  {'-' * 66}")
    print("  ADDRESS MATCH:")
    if result.address_match:
        m = result.address_match
        review_tag = " [NEEDS REVIEW]" if result.address_needs_review else ""
        print(f"    Score:     {m.score}{review_tag}")
        print(f"    Bitable:   {m.address} (id={m.record_id})")
        print(f"    Config ID: {m.deliver_config_id or '-'}")
        print(f"    Config:    {m.deliver_config or '-'}")
        print(f"    Consingee: {m.consingee_name or '-'} (id={m.consingee_id or '-'})")
    else:
        print("    NO MATCH (address not found in Bitable)")

    if result.import_containers:
        print(f"  {'-' * 66}")
        print(f"  IMPORT containers ({len(result.import_containers)}):")
        for i, c in enumerate(result.import_containers, 1):
            print(f"  [{i}] CTN: {c.container_number}")
            print(
                f"      Type: {c.container_type or '-'}"
                f" | Weight: {c.container_weight}t"
                f" | Commodity: {c.commodity or '-'}"
            )

    if result.export_bookings:
        print(f"  {'-' * 66}")
        print(f"  EXPORT bookings ({len(result.export_bookings)}):")
        for i, b in enumerate(result.export_bookings, 1):
            qty_str = f" (x{b.release_qty})" if b.release_qty > 1 else ""
            ctn_str = f" CTN: {b.container_number}" if b.container_number else ""
            print(f"  [{i}] Ref: {b.booking_reference or '-'}{qty_str}{ctn_str}")
            print(
                f"      Type: {b.container_type or '-'}"
                f" | Commodity: {b.commodity or '-'}"
                f" | Line: {b.shipping_line or '-'}"
            )

    if not result.import_containers and not result.export_bookings and result.raw_response:
        print(f"  Raw (first 300): {result.raw_response[:300]}")


async def run_service_test() -> None:
    from app.config.app_settings import settings

    if not settings.ZHIPUAI_API_KEY:
        print("Error: ZHIPUAI_API_KEY not set in .env")
        sys.exit(1)
    if not settings.LARK_APP_ID or not settings.LARK_APP_SECRET:
        print("Error: LARK_APP_ID / LARK_APP_SECRET not set in .env")
        sys.exit(1)

    from app.service.llm_service.llm_service import llm_service

    model = settings.AI_MODEL
    text_input: str | None = None
    file_arg: str | None = None
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg.startswith("--model="):
            model = arg.split("=", 1)[1]
        elif arg == "--model" and i + 1 < len(args):
            model = args[i + 1]
            i += 1
        elif arg == "--text" and i + 1 < len(args):
            text_input = args[i + 1]
            i += 1
        else:
            file_arg = arg
        i += 1

    results: list[tuple[str, CartageProcessResult, float]] = []

    if text_input:
        print(f"Mode: text input | Model: {model}")
        start = time.perf_counter()
        try:
            result = await llm_service.process_cartage_text(text_input, model=model)
            elapsed = time.perf_counter() - start
            print_process_result("<text input>", result, elapsed, model)
            results.append(("<text>", result, elapsed))
        except Exception as e:
            elapsed = time.perf_counter() - start
            print(f"ERROR: {type(e).__name__}: {e}")
            results.append(("<text>", CartageProcessResult(), elapsed))
    elif file_arg:
        target = Path(file_arg)
        if target.is_dir():
            all_files: set[Path] = set()
            for pattern in ["*.pdf", "*.PDF", "*.png", "*.PNG", "*.jpg", "*.jpeg", "*.JPG", "*.JPEG", "*.txt", "*.TXT"]:
                all_files.update(target.glob(pattern))
            files = sorted(all_files, key=lambda p: p.name.lower())
        elif target.is_file():
            files = [target]
        else:
            print(f"Error: {target} not found")
            sys.exit(1)

        if not files:
            print("No supported files found")
            sys.exit(1)

        print(f"Model: {model}")
        print(f"Found {len(files)} file(s)")

        for fpath in files:
            start = time.perf_counter()
            try:
                result = await llm_service.process_cartage_document(fpath, model=model)
                elapsed = time.perf_counter() - start
                print_process_result(fpath.name, result, elapsed, model)
                results.append((fpath.name, result, elapsed))
            except Exception as e:
                elapsed = time.perf_counter() - start
                print(f"\n{'=' * 70}")
                print(f"File: {fpath.name}")
                print(f"ERROR: {type(e).__name__}: {e}")
                results.append((fpath.name, CartageProcessResult(), elapsed))
    else:
        print("Usage: python scripts/test_cartage_service.py <path_or_dir> [--model MODEL] [--text TEXT]")
        sys.exit(1)

    llm_service.clear_cartage_cache()

    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")
    ok = sum(1 for _, r, _ in results if r.import_containers or r.export_bookings)
    matched = sum(1 for _, r, _ in results if r.address_match and not r.address_needs_review)
    review = sum(1 for _, r, _ in results if r.address_needs_review)
    no_match = sum(1 for _, r, _ in results if not r.address_match)
    total_import = sum(len(r.import_containers) for _, r, _ in results)
    total_export = sum(len(r.export_bookings) for _, r, _ in results)
    print(
        f"Total: {len(results)} | Parsed OK: {ok}"
        f" | Address Matched: {matched} | Needs Review: {review} | No Match: {no_match}"
    )
    print(f"Import CTNs: {total_import} | Export bookings: {total_export}")
    for name, r, t in results:
        status = "OK" if r.import_containers or r.export_bookings else "FAIL"
        direction = r.direction or "?"
        ref = r.booking_reference or "-"
        score_str = f"score={r.address_match.score}" if r.address_match else "no-match"
        review_str = " [REVIEW]" if r.address_needs_review else ""
        print(f"  [{status}] {name}: Dir={direction} Ref={ref} {score_str}{review_str} ({t:.1f}s)")


if __name__ == "__main__":
    asyncio.run(run_service_test())

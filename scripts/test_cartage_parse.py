"""
Cartage PDF 解析本地测试脚本

用法:
  uv run python scripts/test_cartage_parse.py tests/cartage_samples/
  uv run python scripts/test_cartage_parse.py tests/cartage_samples/sample.pdf
  uv run python scripts/test_cartage_parse.py tests/cartage_samples/ --model glm-4v-flash

环境变量:
  ZHIPUAI_API_KEY  - 智谱 API Key (必填，或写入 .env)
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.service.llm_service.cartage.parser import CartageParser
from app.service.llm_service.cartage.schemas import CartageParseResult


def print_result(pdf_name: str, result: CartageParseResult, elapsed: float, model: str) -> None:
    status = "OK" if result.booking_reference else "EMPTY"
    print(f"\n{'='*70}")
    print(f"File:   {pdf_name}")
    print(f"Model:  {model}")
    print(f"Status: {status} | Containers: {len(result.containers)} | Time: {elapsed:.1f}s")
    print(f"{'-'*70}")
    print(f"  Booking Ref:  {result.booking_reference or '(none)'}")
    print(f"  Direction:    {result.direction or '(none)'}")
    print(f"  Consingee:    {result.consingee_name or '(none)'}")
    print(f"  Deliver Addr: {result.deliver_address or '(none)'}")
    print(f"  Deliver Type: {result.deliver_type_raw or '(none)'}")
    print(f"  Vessel:       {result.vessel_name or '(none)'}")
    print(f"  Voyage:       {result.voyage or '(none)'}")
    print(f"  POD:          {result.port_of_discharge or '(none)'}")
    print(f"  {'-'*66}")
    for i, c in enumerate(result.containers, 1):
        print(f"  [{i}] CTN: {c.container_number}")
        print(
            f"      Type: {c.container_type or '(none)'} | "
            f"Weight: {c.container_weight}t | "
            f"Commodity: {c.commodity or '(none)'}"
        )
    if not result.booking_reference and result.raw_response:
        print(f"  Raw (first 500): {result.raw_response[:500]}")


def main() -> None:
    from app.config.app_settings import settings

    if not settings.ZHIPUAI_API_KEY:
        print("Error: ZHIPUAI_API_KEY not set in .env")
        sys.exit(1)

    model = settings.AI_MODEL
    pdf_arg = None
    for arg in sys.argv[1:]:
        if arg.startswith("--model="):
            model = arg.split("=", 1)[1]
        elif arg == "--model" and sys.argv.index(arg) + 1 < len(sys.argv):
            model = sys.argv[sys.argv.index(arg) + 1]
        else:
            pdf_arg = arg

    if not pdf_arg:
        print("Usage: python scripts/test_cartage_parse.py <pdf_path_or_dir> [--model MODEL]")
        sys.exit(1)

    target = Path(pdf_arg)
    if target.is_dir():
        pdfs = sorted(target.glob("*.pdf")) + sorted(target.glob("*.PDF"))
    elif target.suffix.lower() == ".pdf":
        pdfs = [target]
    else:
        print(f"Error: {target} is not a PDF file or directory")
        sys.exit(1)

    if not pdfs:
        print("No PDF files found")
        sys.exit(1)

    parser = CartageParser(model=model)
    print(f"Model: {model}")
    print(f"Found {len(pdfs)} PDF(s)")

    results: list[tuple[str, CartageParseResult, float]] = []
    for pdf_path in pdfs:
        start = time.perf_counter()
        try:
            result = parser.parse_pdf(pdf_path)
            elapsed = time.perf_counter() - start
            print_result(pdf_path.name, result, elapsed, model)
            results.append((pdf_path.name, result, elapsed))
        except Exception as e:
            elapsed = time.perf_counter() - start
            print(f"\n{'='*70}")
            print(f"File: {pdf_path.name}")
            print(f"ERROR: {type(e).__name__}: {e}")
            results.append((pdf_path.name, CartageParseResult(), elapsed))

    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    ok = sum(1 for _, r, _ in results if r.booking_reference)
    total_ctns = sum(len(r.containers) for _, r, _ in results)
    print(f"Total: {len(results)} | Success: {ok} | Failed: {len(results) - ok} | Containers: {total_ctns}")
    for name, r, t in results:
        status = "OK" if r.booking_reference else "FAIL"
        ref = r.booking_reference or "-"
        ctns = ", ".join(c.container_number for c in r.containers) if r.containers else "-"
        print(f"  [{status}] {name}: Ref={ref} | CTNs: {ctns} ({t:.1f}s)")


if __name__ == "__main__":
    main()

"""
EDO PDF 解析本地测试脚本

用法:
  uv run python scripts/test_edo_parse.py tests/edo_samples/sample.pdf
  uv run python scripts/test_edo_parse.py tests/edo_samples/            # 解析目录下所有 PDF
  uv run python scripts/test_edo_parse.py tests/edo_samples/ --model glm-4v-flash  # 指定模型

环境变量:
  ZHIPUAI_API_KEY  - 智谱 API Key (必填，或写入 .env)
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config.ai import get_ai_client
from app.modules.operations.edo.parser import EdoParser
from app.modules.operations.edo.schemas import EdoParseResult


def print_result(pdf_name: str, result: EdoParseResult, elapsed: float, model: str) -> None:
    status = "OK" if result.entries else "EMPTY"
    print(f"\n{'='*60}")
    print(f"File:   {pdf_name}")
    print(f"Model:  {model}")
    print(f"Status: {status} | Entries: {len(result.entries)} | Time: {elapsed:.1f}s")
    print(f"{'-'*60}")
    for i, entry in enumerate(result.entries, 1):
        print(f"  [{i}] CTN: {entry.container_number}")
        print(f"      PIN: {entry.edo_pin or '(none)'}")
        print(f"      Line: {entry.shipping_line or '(none)'}")
        print(f"      Park: {entry.empty_park or '(none)'}")
    if not result.entries and result.raw_response:
        print(f"  Raw (first 300): {result.raw_response[:300]}")


def main() -> None:
    from app.config.settings import settings

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
        print("Usage: python scripts/test_edo_parse.py <pdf_path_or_dir> [--model MODEL]")
        sys.exit(1)

    target = Path(pdf_arg)
    if target.is_dir():
        pdfs = sorted(target.glob("*.pdf"))
    elif target.suffix.lower() == ".pdf":
        pdfs = [target]
    else:
        print(f"Error: {target} is not a PDF file or directory")
        sys.exit(1)

    if not pdfs:
        print("No PDF files found")
        sys.exit(1)

    parser = EdoParser(model=model)
    print(f"Model: {model}")
    print(f"Found {len(pdfs)} PDF(s)")

    results: list[tuple[str, EdoParseResult, float]] = []
    for pdf_path in pdfs:
        start = time.perf_counter()
        try:
            result = parser.parse_pdf(pdf_path)
            elapsed = time.perf_counter() - start
            print_result(pdf_path.name, result, elapsed, model)
            results.append((pdf_path.name, result, elapsed))
        except Exception as e:
            elapsed = time.perf_counter() - start
            print(f"\n{'='*60}")
            print(f"File: {pdf_path.name}")
            print(f"ERROR: {type(e).__name__}: {e}")
            results.append((pdf_path.name, EdoParseResult(entries=[]), elapsed))

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    ok = sum(1 for _, r, _ in results if r.entries)
    total_ctns = sum(len(r.entries) for _, r, _ in results)
    print(f"Total: {len(results)} | Success: {ok} | Failed: {len(results) - ok} | Containers: {total_ctns}")
    for name, r, t in results:
        status = "OK" if r.entries else "FAIL"
        ctns = ", ".join(e.container_number for e in r.entries) if r.entries else "-"
        print(f"  [{status}] {name}: {ctns} ({t:.1f}s)")


if __name__ == "__main__":
    main()

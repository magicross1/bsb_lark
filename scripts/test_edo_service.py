"""
EDO 解析 + 匹配 本地测试脚本

用法:
  uv run python scripts/test_edo_service.py tests/edo_samples/TIIU5348694.PDF
  uv run python scripts/test_edo_service.py tests/edo_samples/            # 解析目录下所有 PDF
  uv run python scripts/test_edo_service.py --text "EDO PIN: 12345, Container: MSKU1234567, Shipping Line: COSCO, Empty Park: ACFS"
  uv run python scripts/test_edo_service.py tests/edo_samples/sample.pdf --model glm-4v-flash

环境变量:
  ZHIPUAI_API_KEY  - 智谱 API Key (必填，或写入 .env)
  LARK_APP_ID / LARK_APP_SECRET / LARK_BITABLE_APP_TOKEN - Bitable (匹配需要)
"""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.service.llm_service.edo.schemas import EdoDictValues, EdoProcessResult


def print_result(name: str, result: EdoProcessResult, elapsed: float, model: str) -> None:
    status = "OK" if result.entries else "EMPTY"
    print(f"\n{'='*60}")
    print(f"File:   {name}")
    print(f"Model:  {model}")
    print(f"Status: {status} | Entries: {len(result.entries)} | Time: {elapsed:.1f}s")
    print(f"{'-'*60}")
    for i, entry in enumerate(result.entries, 1):
        print(f"  [{i}] CTN: {entry.container_number}")
        print(f"      PIN: {entry.edo_pin or '(none)'}")
        sl = entry.shipping_line or "(none)"
        sl_match = ""
        if entry.shipping_line_match:
            sl_match = f" -> {entry.shipping_line_match.name} ({entry.shipping_line_match.record_id})"
        print(f"      Shipping Line: {sl}{sl_match}")
        ep = entry.empty_park or "(none)"
        ep_match = ""
        if entry.empty_park_match:
            ep_match = f" -> {entry.empty_park_match.name} ({entry.empty_park_match.record_id})"
        print(f"      Empty Park: {ep}{ep_match}")
        if entry.empty_park_address:
            print(f"      Park Address: {entry.empty_park_address}")
        if entry.shipping_line and not entry.shipping_line_match:
            print(f"      WARNING: Shipping Line NOT MATCHED")
        if entry.empty_park and not entry.empty_park_match:
            print(f"      WARNING: Empty Park NOT MATCHED")
    if not result.entries and result.raw_response:
        print(f"  Raw (first 300): {result.raw_response[:300]}")


async def run_process(source: str | Path, model: str, dict_values: EdoDictValues | None = None) -> EdoProcessResult:
    from app.service.llm_service.llm_service import LLMService

    svc = LLMService()
    return await svc.process_edo(source, model=model, dict_values=dict_values)


async def run_process_text(text: str, model: str, dict_values: EdoDictValues | None = None) -> EdoProcessResult:
    from app.service.llm_service.llm_service import LLMService

    svc = LLMService()
    return await svc.process_edo_text(text, model=model, dict_values=dict_values)


def main() -> None:
    from app.config.app_settings import settings

    if not settings.ZHIPUAI_API_KEY:
        print("Error: ZHIPUAI_API_KEY not set in .env")
        sys.exit(1)

    model = settings.AI_MODEL
    pdf_arg: str | None = None
    text_input: str | None = None
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg.startswith("--model="):
            model = arg.split("=", 1)[1]
        elif arg == "--model" and i + 1 < len(args):
            i += 1
            model = args[i]
        elif arg == "--text" and i + 1 < len(args):
            i += 1
            text_input = args[i]
        else:
            pdf_arg = arg
        i += 1

    if text_input:
        start = time.perf_counter()
        result = asyncio.run(run_process_text(text_input, model))
        elapsed = time.perf_counter() - start
        print_result("<text input>", result, elapsed, model)
        return

    if not pdf_arg:
        print("Usage: python scripts/test_edo_service.py <pdf_path_or_dir> [--model MODEL] [--text TEXT]")
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

    print(f"Model: {model}")
    print(f"Found {len(pdfs)} PDF(s)")

    results: list[tuple[str, EdoProcessResult, float]] = []
    for pdf_path in pdfs:
        start = time.perf_counter()
        try:
            result = asyncio.run(run_process(pdf_path, model))
            elapsed = time.perf_counter() - start
            print_result(pdf_path.name, result, elapsed, model)
            results.append((pdf_path.name, result, elapsed))
        except Exception as e:
            elapsed = time.perf_counter() - start
            print(f"\n{'='*60}")
            print(f"File: {pdf_path.name}")
            print(f"ERROR: {type(e).__name__}: {e}")
            results.append((pdf_path.name, EdoProcessResult(entries=[]), elapsed))

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    ok = sum(1 for _, r, _ in results if r.entries)
    total_ctns = sum(len(r.entries) for _, r, _ in results)
    sl_matched = sum(
        1 for _, r, _ in results for e in r.entries if e.shipping_line and e.shipping_line_match
    )
    sl_total = sum(1 for _, r, _ in results for e in r.entries if e.shipping_line)
    ep_matched = sum(
        1 for _, r, _ in results for e in r.entries if e.empty_park and e.empty_park_match
    )
    ep_total = sum(1 for _, r, _ in results for e in r.entries if e.empty_park)
    print(f"Total: {len(results)} | Success: {ok} | Failed: {len(results) - ok} | Containers: {total_ctns}")
    print(f"Shipping Line: {sl_matched}/{sl_total} matched")
    print(f"Empty Park: {ep_matched}/{ep_total} matched")
    for name, r, t in results:
        status = "OK" if r.entries else "FAIL"
        ctns = ", ".join(e.container_number for e in r.entries) if r.entries else "-"
        print(f"  [{status}] {name}: {ctns} ({t:.1f}s)")


if __name__ == "__main__":
    main()

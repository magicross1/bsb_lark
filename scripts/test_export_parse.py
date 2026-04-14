"""Quick parse test for Export PDF."""
from __future__ import annotations

import asyncio
import json

from app.service.llm_service.llm_service import LLMService


async def main() -> None:
    llm = LLMService()
    r = await llm.parse_cartage_document(
        "tests/cartage_samples/03288201-6993-43a4-b123-ebfb6aded277(2).pdf"
    )
    print(json.dumps(r.model_dump(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())

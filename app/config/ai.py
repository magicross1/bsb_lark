from __future__ import annotations

from zhipuai import ZhipuAI

from app.config.settings import settings

_client: ZhipuAI | None = None


def get_ai_client() -> ZhipuAI:
    global _client
    if _client is None:
        _client = ZhipuAI(api_key=settings.ZHIPUAI_API_KEY)
    return _client

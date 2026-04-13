from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from typing import Any

from zhipuai import ZhipuAI

from app.config.app_settings import settings


class LLMProvider(StrEnum):
    """已接入的 LLM 后端。新增厂商时在此增加枚举并实现对应 factory。"""

    ZHIPU = "zhipu"


# 需要智谱「思考」参数的模型 ID（与默认 glm系列其它模型区分）
THINKING_MODEL_IDS: frozenset[str] = frozenset({"glm-5v-turbo"})

_clients: dict[LLMProvider, Any] = {}


def _make_zhipu_client() -> ZhipuAI:
    return ZhipuAI(api_key=settings.ZHIPUAI_API_KEY)


_CLIENT_FACTORIES: dict[LLMProvider, Callable[[], ZhipuAI]] = {
    LLMProvider.ZHIPU: _make_zhipu_client,
}


def get_llm_client(*, provider: LLMProvider = LLMProvider.ZHIPU) -> ZhipuAI:
    """按厂商返回（懒加载、进程内单例）聊天客户端。当前仅 ZHIPU。"""
    if provider not in _clients:
        factory = _CLIENT_FACTORIES.get(provider)
        if factory is None:
            raise ValueError(f"No LLM client factory registered for provider {provider!r}")
        _clients[provider] = factory()
    return _clients[provider]


def model_requires_thinking(model_id: str) -> bool:
    """是否应为该模型 ID 附加智谱 thinking 相关参数。"""
    return model_id in THINKING_MODEL_IDS

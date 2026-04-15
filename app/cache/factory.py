from __future__ import annotations

from typing import Any

from app.cache.constants import CartageMatchingCacheKey, EdoMatchingCacheKey

_CacheKey = CartageMatchingCacheKey | EdoMatchingCacheKey


class CacheFactory:
    """进程内缓存；用常量键 ``get`` / ``set`` 读写，``clear`` 清空。"""

    __slots__ = ("_store",)

    def __init__(self) -> None:
        all_keys: list[_CacheKey] = list(CartageMatchingCacheKey) + list(EdoMatchingCacheKey)
        self._store: dict[_CacheKey, list[dict[str, Any]] | None] = {k: None for k in all_keys}

    def get(self, key: _CacheKey) -> list[dict[str, Any]] | None:
        return self._store[key]

    def set(self, key: _CacheKey, value: list[dict[str, Any]]) -> None:
        self._store[key] = value

    def clear(self, *keys: _CacheKey) -> None:
        """不传 key 则清空本存储内全部槽位；传入则只清空这些键。"""
        to_clear = keys if keys else tuple(self._store.keys())
        for k in to_clear:
            self._store[k] = None

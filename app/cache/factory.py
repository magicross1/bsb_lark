from __future__ import annotations

from typing import Any

from app.cache.constants import CartageMatchingCacheKey


class CacheFactory:
    """进程内缓存；用常量键 ``get`` / ``set`` 读写，``clear`` 清空。"""

    __slots__ = ("_store",)

    def __init__(self) -> None:
        self._store: dict[CartageMatchingCacheKey, list[dict[str, Any]] | None] = {
            k: None for k in CartageMatchingCacheKey
        }

    def get(self, key: CartageMatchingCacheKey) -> list[dict[str, Any]] | None:
        return self._store[key]

    def set(self, key: CartageMatchingCacheKey, value: list[dict[str, Any]]) -> None:
        self._store[key] = value

    def clear(self, *keys: CartageMatchingCacheKey) -> None:
        """不传 key 则清空本存储内全部槽位；传入则只清空这些键。"""
        to_clear = keys if keys else tuple(self._store.keys())
        for k in to_clear:
            self._store[k] = None

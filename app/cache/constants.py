from __future__ import annotations

from enum import StrEnum


class CartageMatchingCacheKey(StrEnum):
    """Cartage 主数据匹配缓存槽；与 :class:`app.cache.factory.CacheFactory` 约定。"""

    ADDRESSES = "cartage.matching.addresses"
    DELIVER_CONFIGS = "cartage.matching.deliver_configs"
    CONSINGEES = "cartage.matching.consingees"


class EdoMatchingCacheKey(StrEnum):
    """EDO 主数据匹配缓存槽。"""

    SHIPPING_LINES = "edo.matching.shipping_lines"
    EMPTY_PARKS = "edo.matching.empty_parks"

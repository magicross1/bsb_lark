from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from app.config.app_settings import settings

logger = logging.getLogger(__name__)

_API_URL = "https://maps.googleapis.com/maps/api/geocode/json"


@dataclass
class GeocodingResult:
    suburb: str | None = None
    state: str | None = None
    postcode: str | None = None
    formatted_address: str | None = None
    lat: float | None = None
    lng: float | None = None


class GoogleGeocodingProvider:
    """Google Geocoding API 封装，限定澳洲地址解析。"""

    async def geocode(self, address: str) -> GeocodingResult | None:
        """解析地址，返回 suburb/state/postcode。失败返回 None。"""
        if not address or not settings.GOOGLE_GEOCODING_API_KEY:
            return None

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(_API_URL, params={
                    "address": address,
                    "components": "country:AU",
                    "key": settings.GOOGLE_GEOCODING_API_KEY,
                })
                data = resp.json()
        except Exception:
            logger.exception("Google Geocoding 请求失败: %s", address[:80])
            return None

        if data.get("status") != "OK" or not data.get("results"):
            logger.warning("Google Geocoding 无结果: status=%s, address=%s", data.get("status"), address[:80])
            return None

        result = data["results"][0]
        components = {c["types"][0]: c["long_name"] for c in result.get("address_components", []) if c.get("types")}
        location = result.get("geometry", {}).get("location", {})

        return GeocodingResult(
            suburb=components.get("locality"),
            state=_normalize_state(components.get("administrative_area_level_1")),
            postcode=components.get("postal_code"),
            formatted_address=result.get("formatted_address"),
            lat=location.get("lat"),
            lng=location.get("lng"),
        )


# 州名全称 → 缩写
_STATE_MAP = {
    "NEW SOUTH WALES": "NSW",
    "VICTORIA": "VIC",
    "QUEENSLAND": "QLD",
    "SOUTH AUSTRALIA": "SA",
    "WESTERN AUSTRALIA": "WA",
    "TASMANIA": "TAS",
    "NORTHERN TERRITORY": "NT",
    "AUSTRALIAN CAPITAL TERRITORY": "ACT",
}


def _normalize_state(state: str | None) -> str | None:
    if not state:
        return None
    upper = state.strip().upper()
    return _STATE_MAP.get(upper, upper)

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.common.query_wrapper import QueryWrapper
from app.common.update_wrapper import UpdateWrapper
from app.component.GoogleGeocodingProvider import GoogleGeocodingProvider
from app.core.lark_bitable_value import extract_link_record_ids
from app.entity.address import normalize_address
from app.repository.base_node import BaseNodeRepository
from app.repository.distance_matrix import DistanceMatrixRepository
from app.repository.quote_input import QuoteInputRepository
from app.repository.suburb import SuburbRepository

logger = logging.getLogger(__name__)


@dataclass
class SuburbResolveResult:
    record_id: str | None = None
    suburb_name: str | None = None
    state: str | None = None
    postcode: str | None = None
    match_method: str | None = None
    matched: bool = False


def _extract_address(field_value: Any) -> str:
    """从 Bitable location 字段值提取地址文本。"""
    if isinstance(field_value, dict):
        return field_value.get("full_address") or field_value.get("address") or ""
    if isinstance(field_value, str):
        return field_value
    return ""


class SuburbResolveService:
    """Op-Quote Input 地址解析服务。

    完整流程：
    1. Deliver Address → Google Geocoding → MD-Suburb 匹配 → 写回 Suburb
    2. Suburb + Base Node → MD-Distance Matrix 匹配 → 写回 MD-Distance Matrix
    """

    def __init__(
        self,
        geocoding: GoogleGeocodingProvider | None = None,
        suburb_repo: SuburbRepository | None = None,
        quote_input_repo: QuoteInputRepository | None = None,
        distance_matrix_repo: DistanceMatrixRepository | None = None,
        base_node_repo: BaseNodeRepository | None = None,
    ) -> None:
        self._geocoding = geocoding or GoogleGeocodingProvider()
        self._suburb_repo = suburb_repo or SuburbRepository()
        self._quote_input_repo = quote_input_repo or QuoteInputRepository()
        self._dm_repo = distance_matrix_repo or DistanceMatrixRepository()
        self._base_node_repo = base_node_repo or BaseNodeRepository()

    async def resolve_and_update(self, record_id: str) -> dict[str, Any]:
        """完整流程：读取 Deliver Address + Base Node → 解析 Suburb → 查 Distance Matrix → 一次性写回。"""
        record = await self._quote_input_repo.findOne(QueryWrapper().eq("record_id", record_id))
        if not record:
            logger.warning("记录不存在: %s", record_id)
            return {"matched": False, "error": "record not found"}

        address = _extract_address(record.get("Deliver Address"))
        if not address:
            logger.warning("Deliver Address 为空: %s", record_id)
            return {"matched": False, "error": "deliver_address is empty"}

        # Step 1: 解析地址 → MD-Suburb
        suburb_result = await self.resolve_suburb(address)
        suburb_rid = suburb_result.record_id

        update = UpdateWrapper().eq("record_id", record_id)
        if suburb_result.matched and suburb_rid:
            update = update.set("Suburb", [suburb_rid])
            logger.info("Suburb 匹配: %s → %s (%s)", record_id, suburb_result.suburb_name, suburb_result.match_method)

        # Step 2: Suburb + Base Node → MD-Distance Matrix
        base_node_rid = await self._resolve_base_node_rid(record.get("Base Node"))
        dm_result = await self._find_distance_matrix(base_node_rid, suburb_rid)

        if dm_result:
            update = update.set("MD-Distance Matrix", [dm_result["record_id"]])
            logger.info("Distance Matrix 匹配: %s → %s", record_id, dm_result["record_id"])

        # 一次性写回所有字段
        if update._get_fields():
            await self._quote_input_repo.updateOne(update)

        return {
            "matched": suburb_result.matched,
            "suburb_name": suburb_result.suburb_name,
            "state": suburb_result.state,
            "postcode": suburb_result.postcode,
            "match_method": suburb_result.match_method,
            "suburb_record_id": suburb_rid,
            "distance_matrix_record_id": dm_result["record_id"] if dm_result else None,
            "distance": dm_result.get("Distance") if dm_result else None,
            "time": dm_result.get("Time") if dm_result else None,
            "toll_code": dm_result.get("Toll Code") if dm_result else None,
        }

    async def resolve_suburb(self, address: str) -> SuburbResolveResult:
        """纯解析: address → SuburbResolveResult（不写回，供其他场景复用）。"""
        suburb, state, postcode = None, None, None

        # 策略 1: Google Geocoding
        geo = await self._geocoding.geocode(address)
        if geo and geo.suburb:
            suburb, state, postcode = geo.suburb, geo.state, geo.postcode
            record = await self._find_suburb_record(suburb, state, postcode)
            if record:
                return SuburbResolveResult(
                    record_id=record["record_id"],
                    suburb_name=suburb,
                    state=state,
                    postcode=postcode,
                    match_method="google_suburb",
                    matched=True,
                )

        # 策略 2: fallback — normalize_address 提取 suburb/postcode
        parsed = normalize_address(address)
        if parsed.suburb or parsed.postcode:
            fb_suburb = parsed.suburb or suburb
            fb_state = parsed.state or state
            fb_postcode = parsed.postcode or postcode
            record = await self._find_suburb_record(fb_suburb, fb_state, fb_postcode)
            if record:
                return SuburbResolveResult(
                    record_id=record["record_id"],
                    suburb_name=fb_suburb,
                    state=fb_state,
                    postcode=fb_postcode,
                    match_method="fallback_address_parse",
                    matched=True,
                )

        return SuburbResolveResult(suburb_name=suburb, state=state, postcode=postcode)

    async def _find_suburb_record(
        self, suburb: str | None, state: str | None, postcode: str | None,
    ) -> dict[str, Any] | None:
        """在 MD-Suburb 中查找匹配记录。"""
        records = await self._suburb_repo.list(QueryWrapper())

        if suburb and state:
            search_key = f"{suburb} {state}".strip().upper()
            for r in records:
                if (r.get("Suburb") or "").strip().upper() == search_key:
                    return r

        if postcode:
            for r in records:
                if (r.get("Postcode") or "").strip() == postcode.strip():
                    return r

        return None

    async def _find_distance_matrix(
        self, base_node_rid: str | None, suburb_rid: str | None,
    ) -> dict[str, Any] | None:
        """在 MD-Distance Matrix 中查找 Base Node + Suburb 匹配的记录。"""
        if not base_node_rid or not suburb_rid:
            return None

        records = await self._dm_repo.list(QueryWrapper())
        for r in records:
            bn_ids = extract_link_record_ids(r.get("Base Node"))
            sb_ids = extract_link_record_ids(r.get("Suburb"))
            if base_node_rid in bn_ids and suburb_rid in sb_ids:
                return r

        logger.warning("Distance Matrix 未匹配: base_node=%s, suburb=%s", base_node_rid, suburb_rid)
        return None

    async def _resolve_base_node_rid(self, base_node_value: Any) -> str | None:
        """从 Op-Quote Input 的 Base Node 字段值解析出 record_id。

        单向关联字段被 _record_to_dict 转成了显示文本（如 "PORT OF SYDNEY"），
        需要反查 MD-Base Node 获取 record_id。如果是 dict 格式则直接提取。
        """
        ids = extract_link_record_ids(base_node_value)
        if ids and ids[0].startswith("rec"):
            return ids[0]

        # 文本格式：用 Base Node 名称去查
        name = str(base_node_value).strip() if base_node_value else ""
        if not name:
            return None

        record = await self._base_node_repo.findOne(QueryWrapper().eq("Base Node", name))
        return record["record_id"] if record else None

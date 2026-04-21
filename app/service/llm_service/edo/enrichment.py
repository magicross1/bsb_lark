from __future__ import annotations

import logging
import re

from app.core.lark_bitable_value import extract_cell_text
from app.service.edo.edo import EdoService
from app.service.llm_service.edo.schemas import (
    EdoEntryMatch,
    EdoParseResult,
    EdoProcessResult,
    EmptyParkMatch,
    ShippingLineMatch,
)

logger = logging.getLogger(__name__)


class EdoEnrichmentService:
    """将 :class:`EdoParseResult` 与主数据匹配，产出 :class:`EdoProcessResult`。

    匹配规则:
    - Shipping Line: 精确名称匹配 (AI 输出名 == Bitable Shipping Line 名)
    - Empty Park: 名称精确匹配 + 地址模糊匹配 双重验证
    """

    def __init__(self, edo: EdoService) -> None:
        self._edo = edo

    async def enrich(self, parse_result: EdoParseResult) -> EdoProcessResult:
        shipping_lines = await self._edo.list_shipping_lines_for_matching()
        empty_parks = await self._edo.list_empty_parks_for_matching()

        matched_entries: list[EdoEntryMatch] = []
        for entry in parse_result.entries:
            sl_match = self._match_shipping_line(entry.shipping_line, shipping_lines)
            ep_match = self._match_empty_park(
                entry.empty_park,
                entry.empty_park_address,
                empty_parks,
            )

            matched_entries.append(
                EdoEntryMatch(
                    container_number=entry.container_number,
                    edo_pin=entry.edo_pin,
                    shipping_line=entry.shipping_line,
                    empty_park=entry.empty_park,
                    empty_park_address=entry.empty_park_address,
                    shipping_line_match=sl_match,
                    empty_park_match=ep_match,
                )
            )

        return EdoProcessResult(entries=matched_entries, raw_response=parse_result.raw_response)

    @staticmethod
    def _match_shipping_line(
        name: str | None,
        all_lines: list[dict],
    ) -> ShippingLineMatch | None:
        if not name:
            return None

        name_upper = name.strip().upper()

        for line in all_lines:
            line_name = extract_cell_text(line.get("Shipping Line", line.get("shipping_line")))
            if line_name and line_name.strip().upper() == name_upper:
                return ShippingLineMatch(
                    record_id=line["record_id"],
                    name=line_name.strip(),
                )

        for line in all_lines:
            short_name = extract_cell_text(line.get("Shiiping Line Short Name", line.get("shiiping_line_short_name")))
            if short_name and short_name.strip().upper() == name_upper:
                full_name = extract_cell_text(line.get("Shipping Line", line.get("shipping_line")))
                return ShippingLineMatch(
                    record_id=line["record_id"],
                    name=full_name.strip() if full_name else short_name.strip(),
                )

        logger.warning("Shipping Line not matched: %r", name)
        return None

    @staticmethod
    def _match_empty_park(
        name: str | None,
        address: str | None,
        all_parks: list[dict],
    ) -> EmptyParkMatch | None:
        if not name:
            return None

        name_upper = name.strip().upper()

        name_matches: list[dict] = []
        for park in all_parks:
            park_name = extract_cell_text(park.get("Empty Park", park.get("empty_park")))
            if park_name and park_name.strip().upper() == name_upper:
                name_matches.append(park)

        if not name_matches:
            alias_matches = _match_by_alias(name_upper, all_parks)
            if alias_matches:
                name_matches = alias_matches

        if not name_matches:
            fuzzy_match = _fuzzy_match_empty_park(name, address, all_parks)
            if fuzzy_match:
                park_name = extract_cell_text(fuzzy_match.get("Empty Park", fuzzy_match.get("empty_park")))
                park_addr = extract_cell_text(fuzzy_match.get("Facility Address", fuzzy_match.get("facility_address")))
                logger.info(
                    "Empty Park fuzzy matched: %r -> %r",
                    name,
                    park_name,
                )
                return EmptyParkMatch(
                    record_id=fuzzy_match["record_id"],
                    name=park_name.strip() if park_name else name,
                    address=park_addr.strip() if park_addr else None,
                )
            logger.warning("Empty Park not matched by name: %r", name)
            return None

        if len(name_matches) == 1:
            park = name_matches[0]
            park_name = extract_cell_text(park.get("Empty Park", park.get("empty_park")))
            park_addr = extract_cell_text(park.get("Facility Address", park.get("facility_address")))
            return EmptyParkMatch(
                record_id=park["record_id"],
                name=park_name.strip() if park_name else name,
                address=park_addr.strip() if park_addr else None,
            )

        if address:
            best = _pick_by_address(name_matches, address)
            if best:
                park_name = extract_cell_text(best.get("Empty Park", best.get("empty_park")))
                park_addr = extract_cell_text(best.get("Facility Address", best.get("facility_address")))
                return EmptyParkMatch(
                    record_id=best["record_id"],
                    name=park_name.strip() if park_name else name,
                    address=park_addr.strip() if park_addr else None,
                )

        park = name_matches[0]
        park_name = extract_cell_text(park.get("Empty Park", park.get("empty_park")))
        park_addr = extract_cell_text(park.get("Facility Address", park.get("facility_address")))
        logger.warning(
            "Empty Park ambiguous (name=%r, %d candidates, no address match), using first",
            name,
            len(name_matches),
        )
        return EmptyParkMatch(
            record_id=park["record_id"],
            name=park_name.strip() if park_name else name,
            address=park_addr.strip() if park_addr else None,
        )


def _pick_by_address(candidates: list[dict], edo_address: str) -> dict | None:
    edo_norm = _normalize_for_comparison(edo_address)
    if not edo_norm:
        return None

    best: dict | None = None
    best_score = 0.0

    for park in candidates:
        park_addr = extract_cell_text(park.get("Facility Address", park.get("facility_address")))
        if not park_addr:
            continue
        park_norm = _normalize_for_comparison(str(park_addr))
        score = _address_similarity(edo_norm, park_norm)
        if score > best_score:
            best_score = score
            best = park

    if best and best_score >= 0.3:
        return best
    return None


def _normalize_for_comparison(addr: str) -> str:
    s = addr.upper()
    s = re.sub(r"\b(NSW|VIC|QLD|WA|SA|TAS|ACT|NT)\b", "", s)
    s = re.sub(r"\b\d{4}\b", "", s)
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return s.strip()


def _address_similarity(a: str, b: str) -> float:
    tokens_a = set(a.split())
    tokens_b = set(b.split())
    if not tokens_a or not tokens_b:
        return 0.0
    overlap = len(tokens_a & tokens_b)
    return overlap / max(len(tokens_a), len(tokens_b))


def _fuzzy_match_empty_park(
    name: str,
    address: str | None,
    all_parks: list[dict],
) -> dict | None:
    clean_name = re.sub(r"\s*\(.*?\)\s*", " ", name).strip()
    name_norm = _normalize_for_comparison(clean_name)

    name_scored: list[tuple[dict, float]] = []
    for park in all_parks:
        park_name = extract_cell_text(park.get("Empty Park", park.get("empty_park")))
        if not park_name:
            continue
        park_norm = _normalize_for_comparison(park_name)
        score = _token_similarity(name_norm, park_norm)
        if score >= 0.4:
            name_scored.append((park, score))

    name_scored.sort(key=lambda x: x[1], reverse=True)

    if not name_scored:
        return None

    if address:
        addr_best = _pick_by_address([p for p, _ in name_scored[:5]], address)
        if addr_best:
            return addr_best

    return name_scored[0][0]


def _token_similarity(a: str, b: str) -> float:
    tokens_a = set(a.split())
    tokens_b = set(b.split())
    if not tokens_a or not tokens_b:
        return 0.0
    overlap = len(tokens_a & tokens_b)
    return overlap / max(len(tokens_a), len(tokens_b))


def _match_by_alias(name_upper: str, all_parks: list[dict]) -> list[dict]:
    matches: list[dict] = []
    for park in all_parks:
        alias_raw = extract_cell_text(park.get("Alias", park.get("alias")))
        if not alias_raw:
            continue
        for alias in alias_raw.split(";"):
            alias_stripped = alias.strip().upper()
            if alias_stripped and alias_stripped == name_upper:
                matches.append(park)
                break
    return matches

from __future__ import annotations

from typing import Any

from app.config.cartage_matching import ADDRESS_MATCH_MIN_SCORE, ADDRESS_MATCH_REVIEW_BELOW_SCORE
from app.core.lark_bitable_value import extract_cell_text, link_field_contains_record_id
from app.entity.address import NormalizedAddress, address_match_score, normalize_address
from app.service.cartage import CartageService
from app.service.llm_service.cartage.process_schemas import (
    AddressMatch,
    CartageProcessResult,
    ExportBookingMatch,
)
from app.service.llm_service.cartage.schemas import CartageParseResult, ImportContainerMatch


class CartageEnrichmentService:
    """将 :class:`CartageParseResult` 与主数据匹配，产出 :class:`CartageProcessResult`。"""

    def __init__(self, cartage: CartageService) -> None:
        self._cartage = cartage

    async def enrich(self, parse_result: CartageParseResult) -> CartageProcessResult:
        address_match = None
        address_needs_review = False

        if parse_result.deliver_address:
            address_match, address_needs_review = await self._match_deliver_address(
                parse_result.deliver_address,
                parse_result.deliver_type,
            )

        import_matches = [ImportContainerMatch(**c.model_dump()) for c in parse_result.import_containers]

        export_matches = [ExportBookingMatch(**b.model_dump()) for b in parse_result.export_bookings]

        return CartageProcessResult(
            booking_reference=parse_result.booking_reference,
            direction=parse_result.direction,
            consingee_name=parse_result.consingee_name,
            deliver_address=parse_result.deliver_address,
            deliver_type=parse_result.deliver_type,
            deliver_type_raw=parse_result.deliver_type_raw,
            address_match=address_match,
            address_needs_review=address_needs_review,
            import_containers=import_matches,
            export_bookings=export_matches,
            raw_response=parse_result.raw_response,
        )

    async def _match_deliver_address(
        self,
        address_str: str,
        deliver_type: str | None = None,
    ) -> tuple[AddressMatch | None, bool]:
        parsed = normalize_address(address_str)
        candidates = await self._get_address_candidates(parsed)
        if not candidates:
            return None, True

        scored: list[tuple[dict[str, Any], float]] = []
        for candidate_raw in candidates:
            candidate_addr = candidate_raw.get("Address", candidate_raw.get("address", ""))
            if not candidate_addr:
                continue
            candidate_norm = normalize_address(str(candidate_addr))
            score = address_match_score(parsed, candidate_norm)
            scored.append((candidate_raw, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        if not scored or scored[0][1] < ADDRESS_MATCH_MIN_SCORE:
            return None, True

        best_raw, best_score = scored[0]
        best_record_id = best_raw.get("record_id", "")
        best_address = str(best_raw.get("Address", best_raw.get("address", "")))
        needs_review = best_score < ADDRESS_MATCH_REVIEW_BELOW_SCORE

        deliver_config_id = None
        deliver_config = None
        consingee_id = None
        consingee_name = None

        deliver_configs = await self._find_deliver_configs(best_record_id, deliver_type)
        if deliver_configs:
            dc = deliver_configs[0]
            deliver_config_id = dc.get("record_id")
            deliver_config = extract_cell_text(dc.get("Deliver Config", dc.get("deliver_config")))

        consingee = await self._find_consingee_by_address(best_record_id)
        if consingee:
            consingee_id = consingee.get("record_id")
            consingee_name = extract_cell_text(consingee.get("Name", consingee.get("name")))

        return AddressMatch(
            record_id=best_record_id,
            address=best_address,
            score=round(best_score, 3),
            deliver_config_id=deliver_config_id,
            deliver_config=deliver_config,
            consingee_id=consingee_id,
            consingee_name=consingee_name,
        ), needs_review

    async def _get_address_candidates(self, parsed: NormalizedAddress) -> list[dict[str, Any]]:
        all_addresses = await self._cartage.list_addresses_for_matching()
        if not parsed.postcode and not parsed.street_name:
            return all_addresses[:20]

        filtered = all_addresses
        if parsed.postcode:
            postcode_candidates = [
                a for a in all_addresses if parsed.postcode in str(a.get("Address", a.get("address", "")))
            ]
            if postcode_candidates:
                filtered = postcode_candidates

        if parsed.street_name and len(filtered) > 20:
            street_lower = parsed.street_name.lower()
            street_candidates = [
                a for a in filtered if street_lower in str(a.get("Address", a.get("address", ""))).lower()
            ]
            if street_candidates:
                filtered = street_candidates

        return filtered

    async def _find_deliver_configs(
        self,
        warehouse_address_id: str,
        deliver_type: str | None = None,
    ) -> list[dict[str, Any]]:
        all_configs = await self._cartage.list_deliver_configs_for_matching()
        matching = []
        for config in all_configs:
            if link_field_contains_record_id(
                config.get("Warehouse Address", config.get("warehouse_address")),
                warehouse_address_id,
            ):
                matching.append(config)

        if deliver_type and matching:
            dt_filtered = [c for c in matching if deliver_type in str(c.get("Deliver Type", c.get("deliver_type", "")))]
            if dt_filtered:
                return dt_filtered

        return matching

    async def _find_consingee_by_address(self, warehouse_address_id: str) -> dict[str, Any] | None:
        all_consingees = await self._cartage.list_consingees_for_matching()
        for consingee in all_consingees:
            if link_field_contains_record_id(
                consingee.get("MD-Warehouse Address", consingee.get("warehouse_address")),
                warehouse_address_id,
            ):
                return consingee
        return None

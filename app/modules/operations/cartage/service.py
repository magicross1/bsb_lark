from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.modules.master_data.repository import (
    ConsingeeRepository,
    WarehouseAddressRepository,
    WarehouseDeliverConfigRepository,
)
from app.modules.operations.cartage.parser import CartageParser
from app.modules.operations.cartage.schemas import (
    AddressMatch,
    CartageDictValues,
    CartageParseResult,
    CartageProcessResult,
    ExportBookingEntry,
    ExportBookingMatch,
    ImportContainerMatch,
)
from app.shared.address import address_match_score, normalize_address

logger = logging.getLogger(__name__)

MATCH_THRESHOLD = 0.6
REVIEW_THRESHOLD = 0.8


def _extract_text(field: Any) -> str | None:
    if field is None:
        return None
    if isinstance(field, str):
        return field
    if isinstance(field, list):
        parts = []
        for item in field:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if text:
                    parts.append(text)
        return ", ".join(parts) if parts else None
    return str(field)


class CartageService:
    def __init__(self) -> None:
        self.warehouse_address_repo = WarehouseAddressRepository()
        self.warehouse_deliver_config_repo = WarehouseDeliverConfigRepository()
        self.consingee_repo = ConsingeeRepository()
        self._address_cache: list[dict[str, Any]] | None = None
        self._deliver_config_cache: list[dict[str, Any]] | None = None
        self._consingee_cache: list[dict[str, Any]] | None = None

    async def parse_document(
        self,
        source: str | Path,
        *,
        model: str = "glm-5v-turbo",
        dict_values: CartageDictValues | None = None,
    ) -> CartageParseResult:
        parser = CartageParser(model=model, dict_values=dict_values)
        source = Path(source) if not isinstance(source, Path) else source
        suffix = source.suffix.lower()

        if suffix in {".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tiff"}:
            return parser.parse(source)
        if suffix in {".txt", ".text"}:
            return parser.parse_text_file(source)
        raise ValueError(f"Unsupported file type: {suffix}")

    async def parse_text(
        self,
        text: str,
        *,
        model: str = "glm-5v-turbo",
        dict_values: CartageDictValues | None = None,
    ) -> CartageParseResult:
        parser = CartageParser(model=model, dict_values=dict_values)
        return parser.parse_text(text)

    async def process_document(
        self,
        source: str | Path,
        *,
        model: str = "glm-5v-turbo",
        dict_values: CartageDictValues | None = None,
    ) -> CartageProcessResult:
        parse_result = await self.parse_document(source, model=model, dict_values=dict_values)
        return await self._enrich_parse_result(parse_result)

    async def process_text(
        self,
        text: str,
        *,
        model: str = "glm-5v-turbo",
        dict_values: CartageDictValues | None = None,
    ) -> CartageProcessResult:
        parse_result = await self.parse_text(text, model=model, dict_values=dict_values)
        return await self._enrich_parse_result(parse_result)

    async def _enrich_parse_result(self, parse_result: CartageParseResult) -> CartageProcessResult:
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

        if not scored or scored[0][1] < MATCH_THRESHOLD:
            return None, True

        best_raw, best_score = scored[0]
        best_record_id = best_raw.get("record_id", "")
        best_address = str(best_raw.get("Address", best_raw.get("address", "")))
        needs_review = best_score < REVIEW_THRESHOLD

        deliver_config_id = None
        deliver_config = None
        consingee_id = None
        consingee_name = None

        deliver_configs = await self._find_deliver_configs(best_record_id, deliver_type)
        if deliver_configs:
            dc = deliver_configs[0]
            deliver_config_id = dc.get("record_id")
            deliver_config = _extract_text(dc.get("Deliver Config", dc.get("deliver_config")))

        consingee = await self._find_consingee_by_address(best_record_id)
        if consingee:
            consingee_id = consingee.get("record_id")
            consingee_name = _extract_text(consingee.get("Name", consingee.get("name")))

        return AddressMatch(
            record_id=best_record_id,
            address=best_address,
            score=round(best_score, 3),
            deliver_config_id=deliver_config_id,
            deliver_config=deliver_config,
            consingee_id=consingee_id,
            consingee_name=consingee_name,
        ), needs_review

    async def _get_address_candidates(
        self,
        parsed: Any,
    ) -> list[dict[str, Any]]:
        all_addresses = await self._load_addresses()
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
        all_configs = await self._load_deliver_configs()
        matching = []
        for config in all_configs:
            if self._link_contains_id(
                config.get("Warehouse Address", config.get("warehouse_address")), warehouse_address_id
            ):
                matching.append(config)

        if deliver_type and matching:
            dt_filtered = [
                c for c in matching if deliver_type in str(c.get("Deliver Type", config.get("deliver_type", "")))
            ]
            if dt_filtered:
                return dt_filtered

        return matching

    async def _find_consingee_by_address(
        self,
        warehouse_address_id: str,
    ) -> dict[str, Any] | None:
        all_consingees = await self._load_consingees()
        for consingee in all_consingees:
            if self._link_contains_id(
                consingee.get("MD-Warehouse Address", consingee.get("warehouse_address")), warehouse_address_id
            ):
                return consingee
        return None

    @staticmethod
    def _link_contains_id(link_field: Any, record_id: str) -> bool:
        if link_field is None:
            return False
        if isinstance(link_field, str):
            return link_field == record_id
        if isinstance(link_field, list):
            for item in link_field:
                if isinstance(item, str) and item == record_id:
                    return True
                if isinstance(item, dict):
                    ids = item.get("record_ids", [])
                    if record_id in ids:
                        return True
                    if item.get("text", "").endswith(record_id):
                        return True
        return False

    async def _load_addresses(self) -> list[dict[str, Any]]:
        if self._address_cache is None:
            self._address_cache = await self.warehouse_address_repo.list_all_records(
                field_names=["Address", "Location", "Detail"],
            )
        return self._address_cache

    async def _load_deliver_configs(self) -> list[dict[str, Any]]:
        if self._deliver_config_cache is None:
            self._deliver_config_cache = await self.warehouse_deliver_config_repo.list_all_records(
                field_names=["Deliver Config", "Deliver Type", "Warehouse Address"],
            )
        return self._deliver_config_cache

    async def _load_consingees(self) -> list[dict[str, Any]]:
        if self._consingee_cache is None:
            self._consingee_cache = await self.consingee_repo.list_all_records(
                field_names=["Name", "MD-Warehouse Address"],
            )
        return self._consingee_cache

    def clear_cache(self) -> None:
        self._address_cache = None
        self._deliver_config_cache = None
        self._consingee_cache = None

    @staticmethod
    def expand_export_bookings(bookings: list[ExportBookingEntry]) -> list[ExportBookingEntry]:
        expanded: list[ExportBookingEntry] = []
        for booking in bookings:
            qty = max(booking.release_qty, 1)
            if qty == 1:
                expanded.append(booking)
                continue
            for i in range(1, qty + 1):
                suffix = f"-{i}" if booking.booking_reference else ""
                expanded.append(
                    ExportBookingEntry(
                        booking_reference=f"{booking.booking_reference}{suffix}" if booking.booking_reference else None,
                        release_qty=1,
                        vessel_name=booking.vessel_name,
                        voyage=booking.voyage,
                        base_node=booking.base_node,
                        container_type=booking.container_type,
                        commodity=booking.commodity,
                        shipping_line=booking.shipping_line,
                        container_number=booking.container_number,
                    )
                )
        return expanded

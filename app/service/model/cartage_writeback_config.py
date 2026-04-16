from __future__ import annotations

from dataclasses import dataclass

from app.common.lark_tables import T
from app.entity.link_resolver import LinkLookup, NestedLink


@dataclass(frozen=True)
class WritebackFieldRule:
    """字段写回规则：描述如何把业务字段映射到 Bitable 列。"""

    bitable_field: str
    source_key: str
    required: bool = False
    default_value: str | None = None
    link_lookup: LinkLookup | None = None
    is_direct_link: bool = False


# ── Op-Cartage（进口） ────────────────────────────────────────
OP_CARTAGE_IMPORT_RULES: list[WritebackFieldRule] = [
    WritebackFieldRule(
        bitable_field="Booking Reference",
        source_key="booking_reference",
        required=True,
        default_value="TBC",
    ),
    WritebackFieldRule(
        bitable_field="Consingnee Name",
        source_key="consingee_id",
        required=True,
        is_direct_link=True,
    ),
    WritebackFieldRule(
        bitable_field="Deliver Config",
        source_key="deliver_config_id",
        required=True,
        is_direct_link=True,
    ),
]

# ── Op-Cartage（出口） ────────────────────────────────────────
OP_CARTAGE_EXPORT_RULES: list[WritebackFieldRule] = [
    WritebackFieldRule(
        bitable_field="Booking Reference",
        source_key="booking_reference",
        required=True,
        default_value="TBC",
    ),
    WritebackFieldRule(
        bitable_field="Consingnee Name",
        source_key="consingee_id",
        is_direct_link=True,
    ),
    WritebackFieldRule(
        bitable_field="Deliver Config",
        source_key="deliver_config_id",
        is_direct_link=True,
    ),
]

# ── Op-Import ─────────────────────────────────────────────────
OP_IMPORT_RULES: list[WritebackFieldRule] = [
    WritebackFieldRule(
        bitable_field="Container Number",
        source_key="container_number",
        required=True,
        default_value="TBC",
    ),
    WritebackFieldRule(
        bitable_field="FULL Vessel Name",
        source_key="vessel_name",
        required=True,
        link_lookup=LinkLookup(
            target_table_id=T.op_vessel_schedule.id,
            search_field="Vessel Name",
            filter_expr='AND(CurrentValue.[Voyage]="{voyage}", CurrentValue.[Base Node]="{base_node}")',
            create_if_missing=True,
            create_fields={
                "Vessel Name": "{value}",
                "Voyage": "{voyage}",
            },
            create_links={
                "Base Node": NestedLink(
                    source_key="base_node",
                    lookup=LinkLookup(
                        target_table_id=T.md_base_node.id,
                        search_field="Base Node",
                        create_if_missing=True,
                        create_fields={"Base Node": "{value}"},
                    ),
                ),
            },
            default_if_missing="TBC",
        ),
    ),
    WritebackFieldRule(
        bitable_field="Container Type",
        source_key="container_type",
    ),
    WritebackFieldRule(
        bitable_field="Commodity",
        source_key="commodity",
    ),
    WritebackFieldRule(
        bitable_field="Container Weight",
        source_key="container_weight",
    ),
]

# ── Op-Export ─────────────────────────────────────────────────
OP_EXPORT_RULES: list[WritebackFieldRule] = [
    WritebackFieldRule(
        bitable_field="Booking Reference",
        source_key="booking_reference",
        required=True,
        default_value="TBC",
    ),
    WritebackFieldRule(
        bitable_field="Container Number",
        source_key="container_number",
    ),
    WritebackFieldRule(
        bitable_field="Release Qty",
        source_key="release_qty",
    ),
    WritebackFieldRule(
        bitable_field="FULL Vessel Name",
        source_key="vessel_name",
        link_lookup=LinkLookup(
            target_table_id=T.op_vessel_schedule.id,
            search_field="Vessel Name",
            filter_expr='AND(CurrentValue.[Voyage]="{voyage}", CurrentValue.[Base Node]="{base_node}")',
            create_if_missing=True,
            create_fields={
                "Vessel Name": "{value}",
                "Voyage": "{voyage}",
            },
            create_links={
                "Base Node": NestedLink(
                    source_key="base_node",
                    lookup=LinkLookup(
                        target_table_id=T.md_base_node.id,
                        search_field="Base Node",
                        create_if_missing=True,
                        create_fields={"Base Node": "{value}"},
                    ),
                ),
            },
        ),
    ),
    WritebackFieldRule(
        bitable_field="Container Type",
        source_key="container_type",
    ),
    WritebackFieldRule(
        bitable_field="Commodity",
        source_key="commodity",
    ),
]

"""Test RelationResolver: Op-Cartage -> Deliver Config -> Warehouse Address -> Suburb

Usage:
    PYTHONUTF8=1 uv run python -m scripts.test_relation_resolver

Lookup chain:
    Op-Cartage
      -> [Deliver Config] -> MD-Warehouse Deliver Config
        -> [Warehouse Address] -> MD-Warehouse Address
          -> [Suburb] -> MD-Suburb (Rural Tailgate, Postcode)
          -> [Warehouse - Consingee] -> MD-Consingee
"""

from __future__ import annotations

import asyncio
import json

from app.common.lark_tables import T
from app.entity.relation import RelationHop, RelationResolver

CARTAGE_RECORD_ID = "recvgdvg0m9xQ0"


async def main() -> None:
    resolver = RelationResolver()

    print("=" * 70)
    print("RelationResolver test")
    print(f"Start: Op-Cartage record_id={CARTAGE_RECORD_ID}")
    print("=" * 70)

    # Hop 1: Op-Cartage -> MD-Warehouse Deliver Config
    # Get Deliver Config text
    print("\n--- Hop 1: Op-Cartage -> Deliver Config -> Deliver Config ---")
    dc_text = await resolver.resolve_single(
        start_table_id=T.op_cartage.id,
        start_record_id=CARTAGE_RECORD_ID,
        path=[
            RelationHop(
                table_id=T.md_warehouse_deliver_config.id,
                link_field="Deliver Config",
            ),
        ],
        target_field="Deliver Config",
    )
    print(f"  Deliver Config: {dc_text!r}")

    # Hop 2: Op-Cartage -> Deliver Config -> Warehouse Address -> Address
    print("\n--- Hop 2: -> Warehouse Address -> Address ---")
    address = await resolver.resolve_single(
        start_table_id=T.op_cartage.id,
        start_record_id=CARTAGE_RECORD_ID,
        path=[
            RelationHop(
                table_id=T.md_warehouse_deliver_config.id,
                link_field="Deliver Config",
            ),
            RelationHop(
                table_id=T.md_warehouse_address.id,
                link_field="Warehouse Address",
            ),
        ],
        target_field="Address",
    )
    print(f"  Address: {address!r}")

    # Hop 3a: -> Warehouse Address -> Warehouse - Consingee -> Name
    print("\n--- Hop 3a: -> Warehouse Address -> Warehouse - Consingee -> Name ---")
    consingee_name = await resolver.resolve_single(
        start_table_id=T.op_cartage.id,
        start_record_id=CARTAGE_RECORD_ID,
        path=[
            RelationHop(
                table_id=T.md_warehouse_deliver_config.id,
                link_field="Deliver Config",
            ),
            RelationHop(
                table_id=T.md_warehouse_address.id,
                link_field="Warehouse Address",
            ),
            RelationHop(
                table_id=T.md_consingee.id,
                link_field="Warehouse - Consingee",
            ),
        ],
        target_field="Name",
    )
    print(f"  Consingee Name: {consingee_name!r}")

    # Hop 3b: -> Warehouse Address -> Suburb -> Rural Tailgate
    print("\n--- Hop 3b: -> Warehouse Address -> Suburb -> Rural Tailgate ---")
    rural_tg = await resolver.resolve_single(
        start_table_id=T.op_cartage.id,
        start_record_id=CARTAGE_RECORD_ID,
        path=[
            RelationHop(
                table_id=T.md_warehouse_deliver_config.id,
                link_field="Deliver Config",
            ),
            RelationHop(
                table_id=T.md_warehouse_address.id,
                link_field="Warehouse Address",
            ),
            RelationHop(
                table_id=T.md_suburb.id,
                link_field="Suburb",
            ),
        ],
        target_field="Rural Tailgate",
    )
    print(f"  Rural Tailgate: {rural_tg!r}")

    # Hop 3c: -> Warehouse Address -> Suburb -> Postcode
    print("\n--- Hop 3c: -> Warehouse Address -> Suburb -> Postcode ---")
    postcode = await resolver.resolve_single(
        start_table_id=T.op_cartage.id,
        start_record_id=CARTAGE_RECORD_ID,
        path=[
            RelationHop(
                table_id=T.md_warehouse_deliver_config.id,
                link_field="Deliver Config",
            ),
            RelationHop(
                table_id=T.md_warehouse_address.id,
                link_field="Warehouse Address",
            ),
            RelationHop(
                table_id=T.md_suburb.id,
                link_field="Suburb",
            ),
        ],
        target_field="Postcode",
    )
    print(f"  Postcode: {postcode!r}")

    # Full chain summary
    print("\n" + "=" * 70)
    print("Summary:")
    print(f"  Op-Cartage [{CARTAGE_RECORD_ID}]")
    print(f"    -> Deliver Config: {dc_text}")
    print(f"    -> Address: {address}")
    print(f"    -> Consingee: {consingee_name}")
    print(f"    -> Rural Tailgate: {rural_tg}")
    print(f"    -> Postcode: {postcode}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

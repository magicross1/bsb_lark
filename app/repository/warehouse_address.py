from __future__ import annotations

from app.common.lark_tables import T
from app.common.lark_repository import BaseRepository


class WarehouseAddressRepository(BaseRepository):
    table_id = T.md_warehouse_address.id

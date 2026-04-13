from __future__ import annotations

from app.common.lark_tables import T
from app.common.lark_repository import BaseRepository


class WarehouseDeliverConfigRepository(BaseRepository):
    table_id = T.md_warehouse_deliver_config.id

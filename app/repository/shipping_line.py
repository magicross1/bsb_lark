from __future__ import annotations

from app.common.lark_repository import BaseRepository
from app.common.lark_tables import T


class ShippingLineRepository(BaseRepository):
    table_id = T.md_shipping_line.id

from __future__ import annotations

from app.common.lark_repository import LarkRepository
from app.common.lark_tables import T


class ShippingLineRepository(LarkRepository):
    table_id = T.md_shipping_line.id

from __future__ import annotations

from app.common.lark_tables import T
from app.common.lark_repository import BaseRepository


class DTCommodityRepository(BaseRepository):
    table_id = T.dt_commodity.id

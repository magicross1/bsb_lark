from __future__ import annotations

from app.common.lark_tables import T
from app.common.lark_repository import BaseRepository


class DriverRepository(BaseRepository):
    table_id = T.md_driver.id

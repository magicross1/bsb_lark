from __future__ import annotations

from app.common.lark_tables import T
from app.common.lark_repository import BaseRepository


class ConsingeeRepository(BaseRepository):
    table_id = T.md_consingee.id

from __future__ import annotations

from app.common.lark_repository import BaseRepository
from app.common.lark_tables import T


class ExportRepository(BaseRepository):
    table_id = T.op_export.id

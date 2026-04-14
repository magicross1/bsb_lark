from __future__ import annotations

from app.common.lark_repository import LarkRepository
from app.common.lark_tables import T


class ExportRepository(LarkRepository):
    table_id = T.op_export.id

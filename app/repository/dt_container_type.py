from __future__ import annotations

from app.common.lark_tables import T
from app.common.lark_repository import BaseRepository


class DTContainerTypeRepository(BaseRepository):
    table_id = T.dt_container_type.id

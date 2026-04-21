from __future__ import annotations

from app.common.lark_tables import T
from app.common.lark_repository import BaseRepository


class VesselScheduleRepository(BaseRepository):
    table_id = T.op_vessel_schedule.id

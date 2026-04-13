from __future__ import annotations

from app.common.lark_repository import LarkRepository
from app.common.lark_tables import T


class CartageRepository(LarkRepository):
    """飞书 Bitable「Op-Cartage」表；与其它 Repository 一样，仅绑定 table_id，不组合其它 Repository。"""

    table_id = T.op_cartage.id

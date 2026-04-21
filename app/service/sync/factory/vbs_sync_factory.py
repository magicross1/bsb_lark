from __future__ import annotations

from app.component.VbsSearchProvider import VbsSearchProvider
from app.repository.import_ import ImportRepository
from app.service.sync.constants.vbs_constants import _CONDITIONS
from app.service.sync.scene.vbs.dp_world_nsw import DpWorldNswVbsSync
from app.service.sync.scene.vbs.dp_world_vic import DpWorldVicVbsSync
from app.service.sync.scene.vbs.patrick_nsw import PatrickNswVbsSync
from app.service.sync.scene.vbs.patrick_vic import PatrickVicVbsSync
from app.service.sync.scene.vbs.vict_vic import VictVicVbsSync
from app.service.sync.workflow.sync_template import SyncTemplate


class VbsSyncFactory:
    """VBS 同步器策略工厂。

    按 Terminal Full Name（大写）路由到对应码头的 SyncTemplate 实现。
    新增码头只需注册到 _registry，无需改动 service 层。
    """

    def __init__(
        self,
        import_repo: ImportRepository | None = None,
        vbs: VbsSearchProvider | None = None,
    ) -> None:
        repo = import_repo or ImportRepository()
        _vbs = vbs or VbsSearchProvider()
        self._registry: dict[str, SyncTemplate] = {
            DpWorldNswVbsSync.TERMINAL_FULL_NAME: DpWorldNswVbsSync(repo, _vbs),
            DpWorldVicVbsSync.TERMINAL_FULL_NAME: DpWorldVicVbsSync(repo, _vbs),
            PatrickNswVbsSync.TERMINAL_FULL_NAME: PatrickNswVbsSync(repo, _vbs),
            PatrickVicVbsSync.TERMINAL_FULL_NAME: PatrickVicVbsSync(repo, _vbs),
            VictVicVbsSync.TERMINAL_FULL_NAME: VictVicVbsSync(repo, _vbs),
        }

    def get(self, terminal_full_name: str) -> SyncTemplate | None:
        """按 Terminal Full Name 返回对应同步器，未知码头返回 None。"""
        return self._registry.get((terminal_full_name or "").strip().upper())

    def all(self) -> list[SyncTemplate]:
        """返回全部已注册的同步器。"""
        return list(self._registry.values())

    @staticmethod
    def list_conditions() -> list[str]:
        return list(_CONDITIONS.keys())

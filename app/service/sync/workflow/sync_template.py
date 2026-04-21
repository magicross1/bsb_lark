from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from app.common.lark_repository import BaseRepository
from app.common.update_wrapper import UpdateWrapper
from app.service.sync.workflow.batch_sync_result import BatchSyncResult
from app.service.sync.workflow.sync_data import SyncData

logger = logging.getLogger(__name__)


class SyncTemplate(ABC):
    """同步流程三步骨架（模板模式）。

    run_batch 定义不可更改的主流程：
        Step 1  fetch_records       — 从 Bitable 筛选待同步记录
        Step 2  fetch_provider_data — 按码头路由查外部 Provider，解析为 SyncData 列表
        Step 3  build_update_wrappers — 将 SyncData 列表转为 UpdateWrapper 列表

    最终由 _persist 写回 Bitable（batch 优先，失败逐条回退）。
    """

    async def run_batch(self, condition: str) -> BatchSyncResult:
        """主流程（不允许子类覆盖）。"""
        records = await self.fetch_records(condition)
        if not records:
            logger.info("[%s] 无待同步记录", self.__class__.__name__)
            return BatchSyncResult()

        data_list = await self.fetch_provider_data(records)
        wrappers = self.build_update_wrappers(data_list)
        return await self._persist(wrappers)

    # ── Step 1 ──────────────────────────────────────────────

    @abstractmethod
    async def fetch_records(self, condition: str) -> list[dict]:
        """从 Bitable 获取待同步记录。

        子类负责：定义支持的 condition 名称，构建 BitableQuery，返回筛选后的记录列表。
        """

    # ── Step 2 ──────────────────────────────────────────────

    @abstractmethod
    async def fetch_provider_data(self, records: list[dict]) -> list[SyncData]:
        """从外部 Provider 获取数据并解析为 SyncData 对象列表。

        子类负责：按码头路由到正确的 Provider，处理类型转换（datetime → 时间戳，link → record_id）。
        每条 SyncData 须包含对应记录的 record_id。
        """

    # ── Step 3 ──────────────────────────────────────────────

    def build_update_wrappers(self, data_list: list[SyncData]) -> list[UpdateWrapper]:
        """将 SyncData 列表转为 UpdateWrapper 列表（默认实现，子类可覆盖）。"""
        return [d.to_update_wrapper() for d in data_list if d.has_fields()]

    # ── Repository ──────────────────────────────────────────

    @property
    @abstractmethod
    def repository(self) -> BaseRepository:
        """子类提供对应的 Bitable repository。"""

    # ── 写回 ────────────────────────────────────────────────

    async def _persist(self, wrappers: list[UpdateWrapper]) -> BatchSyncResult:
        """批量写回 Bitable，失败时逐条回退。"""
        if not wrappers:
            return BatchSyncResult()

        repo = self.repository
        try:
            await repo.batch_update(wrappers)
            logger.info("[%s] 批量写回成功: %d 条", self.__class__.__name__, len(wrappers))
            return BatchSyncResult(total=len(wrappers), synced=len(wrappers))
        except Exception as batch_err:
            logger.warning("[%s] batch_update 失败，逐条回退: %s", self.__class__.__name__, batch_err)
            synced, errors = 0, 0
            for wrapper in wrappers:
                try:
                    await repo.updateOne(wrapper)
                    synced += 1
                except Exception as e:
                    logger.error(
                        "[%s] 写回失败 %s: %s",
                        self.__class__.__name__,
                        wrapper._get_label() or wrapper._get_record_id_hint() or "?",
                        e,
                    )
                    errors += 1
            return BatchSyncResult(total=len(wrappers), synced=synced, errors=errors)

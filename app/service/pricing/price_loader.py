from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.common.lark_repository import BaseRepository
from app.common.lark_tables import T
from app.common.query_wrapper import QueryWrapper
from app.core.lark_bitable_value import extract_link_record_ids

logger = logging.getLogger(__name__)


class _Repo(BaseRepository):
    """动态 table_id 的轻量 repo，仅用于 PriceLoader 内部批量加载。"""
    def __init__(self, tid: str) -> None:
        super().__init__()
        self._tid = tid

    @property
    def table_id(self) -> str:  # type: ignore[override]
        return self._tid


def _extract_pl_rid(record: dict[str, Any]) -> str | None:
    """从记录的 Price Level 字段提取 record_id。"""
    pl = record.get("Price Level")
    ids = extract_link_record_ids(pl)
    return ids[0] if ids else None


class PriceLoader:
    """6 张价格表的并发加载器 — 一次 load 全部到内存，按 price_level_rid 过滤。

    每张表建内存索引，提供 O(1) 查找方法。
    """

    def __init__(self) -> None:
        self._cartage: list[dict] = []
        self._terminal: list[dict] = []
        self._extra: list[dict] = []
        self._overweight: list[dict] = []
        self._toll: list[dict] = []
        self._empty: list[dict] = []

        # 内存索引 — load 后建立
        self._cartage_idx: dict[str, float] = {}
        self._terminal_idx: dict[str, float] = {}
        self._extra_idx: dict[str, float] = {}
        self._extra_unit_idx: dict[str, str] = {}
        self._overweight_idx: dict[str, float] = {}
        self._toll_idx: dict[str, float] = {}
        self._empty_idx: dict[str, float] = {}

    async def load(self, price_level_rid: str) -> None:
        """分批并发加载 6 张价格表（每批 2 张，避免 Bitable 限流），按 price_level_rid 过滤并建索引。"""
        batches = [
            [_Repo(T.md_price_cartage.id), _Repo(T.md_price_terminal.id)],
            [_Repo(T.md_price_extra.id), _Repo(T.md_price_overweight.id)],
            [_Repo(T.md_price_toll.id), _Repo(T.md_price_empty.id)],
        ]

        results: list[list[dict]] = []
        for batch in batches:
            batch_results = await asyncio.gather(*[r.list(QueryWrapper()) for r in batch])
            results.extend(batch_results)

        def _filter(records: list[dict]) -> list[dict]:
            return [r for r in records if _extract_pl_rid(r) == price_level_rid]

        self._cartage = _filter(results[0])
        self._terminal = _filter(results[1])
        self._extra = _filter(results[2])
        self._overweight = _filter(results[3])
        self._toll = _filter(results[4])
        self._empty = _filter(results[5])

        self._build_indexes()
        logger.info(
            "PriceLoader: cartage=%d, terminal=%d, extra=%d, overweight=%d, toll=%d, empty=%d",
            len(self._cartage), len(self._terminal), len(self._extra),
            len(self._overweight), len(self._toll), len(self._empty),
        )

    def _build_indexes(self) -> None:
        # Cartage: fee_code|ctn_size|deliver_type → amount
        for r in self._cartage:
            fc = (r.get("Fee Code") or "").strip()
            ctn = (r.get("CTN Size") or "").strip()
            dt = (r.get("Deliver Type") or "").strip()
            key = f"{fc}|{ctn}|{dt}"
            amt = r.get("Amount")
            if amt is not None:
                self._cartage_idx[key] = float(amt)

        # Terminal: fee_type|terminal → amount
        for r in self._terminal:
            ft = (r.get("Fee Type") or "").strip()
            term = (r.get("Terminal") or "").strip()
            key = f"{ft}|{term}"
            amt = r.get("Amount")
            if amt is not None:
                self._terminal_idx[key] = float(amt)

        # Extra: fee_code → amount, fee_code → unit
        for r in self._extra:
            fc = (r.get("Fee Code") or "").strip()
            amt = r.get("Amount")
            if fc and amt is not None:
                self._extra_idx[fc] = float(amt)
                self._extra_unit_idx[fc] = (r.get("Unit") or "fixed").strip()

        # Overweight: weight_range|deliver_type → amount
        for r in self._overweight:
            wr = (r.get("Weight Range") or "").strip()
            dt = (r.get("Deliver Type") or "").strip()
            key = f"{wr}|{dt}"
            amt = r.get("Amount")
            if amt is not None:
                self._overweight_idx[key] = float(amt)

        # Toll: toll_code → amount
        for r in self._toll:
            tc = (r.get("Toll Code") or "").strip()
            amt = r.get("Amount")
            if tc and amt is not None:
                self._toll_idx[tc] = float(amt)

        # Empty: empty_class → amount
        for r in self._empty:
            ec = (r.get("Empty Class") or "").strip()
            amt = r.get("Amount")
            if ec and amt is not None:
                self._empty_idx[ec] = float(amt)

    # ── 查找方法 (O(1)) ──────────────────────────────────────

    def find_cartage(self, zone_code: str, ctn_size: str, deliver_type: str) -> float | None:
        return self._cartage_idx.get(f"{zone_code}|{ctn_size}|{deliver_type}")

    def find_terminal(self, fee_type: str, terminal: str = "Default") -> float | None:
        return self._terminal_idx.get(f"{fee_type}|{terminal}")

    def find_extra(self, fee_code: str) -> float | None:
        return self._extra_idx.get(fee_code)

    def find_extra_unit(self, fee_code: str) -> str:
        return self._extra_unit_idx.get(fee_code, "fixed")

    def find_overweight(self, weight_range: str, deliver_type: str) -> float | None:
        return self._overweight_idx.get(f"{weight_range}|{deliver_type}")

    def find_toll(self, toll_code: str) -> float | None:
        return self._toll_idx.get(toll_code)

    def find_empty(self, empty_class: str = "Default") -> float | None:
        return self._empty_idx.get(empty_class)

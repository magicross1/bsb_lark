from __future__ import annotations

import logging
import math
from typing import Any

from app.common.collection_utils import to_map
from app.common.query_wrapper import QueryWrapper
from app.common.update_wrapper import UpdateWrapper
from app.core.lark_bitable_value import extract_cell_text, extract_select_text
from app.repository.base_node import BaseNodeRepository
from app.repository.quote_input import QuoteInputRepository
from app.repository.quote_output import QuoteOutputRepository
from app.service.pricing.price_loader import PriceLoader

logger = logging.getLogger(__name__)

# 6 种 箱型+配送方式 组合
_COMBOS: list[tuple[str, str]] = [
    ("20", "Standard Trailer(STD)"),
    ("40", "Standard Trailer(STD)"),
    ("20", "Sideloader(SDL)"),
    ("40", "Sideloader(SDL)"),
    ("20", "Drop Trailer(DROP)"),
    ("40", "Drop Trailer(DROP)"),
]

# Op-Quote Input 自定义价格字段 → (ctn_size, deliver_type)
_CUSTOM_PRICE_FIELDS: dict[str, tuple[str, str]] = {
    "20 STD": ("20", "Standard Trailer(STD)"),
    "40 STD": ("40", "Standard Trailer(STD)"),
    "20 SDL": ("20", "Sideloader(SDL)"),
    "40 SDL": ("40", "Sideloader(SDL)"),
    "20 DROP": ("20", "Drop Trailer(DROP)"),
    "40 DROP": ("40", "Drop Trailer(DROP)"),
}

# 超出 zone 范围时的公式: base = Distance * 2 * 3 + 200, 再按组合加价
_OVER_ZONE_SURCHARGE: dict[tuple[str, str], float] = {
    ("20", "Standard Trailer(STD)"): 0,
    ("40", "Standard Trailer(STD)"): 40,
    ("20", "Sideloader(SDL)"): 80,
    ("40", "Sideloader(SDL)"): 120,
    ("20", "Drop Trailer(DROP)"): 80,
    ("40", "Drop Trailer(DROP)"): 120,
}


def _over_zone_cartage(distance: float, ctn_size: str, deliver_type: str) -> float:
    """超出 zone 范围时的 Cartage Fee 公式。"""
    base = distance * 2 * 3 + 200
    surcharge = _OVER_ZONE_SURCHARGE.get((ctn_size, deliver_type), 0)
    return round(base + surcharge, 2)


def _distance_to_zone(distance: float, state: str) -> str:
    """距离 → zone code (Z1, Z1.5, Z2, ...)。不 cap 上限，超出范围的 zone 查表会返回 None → 走公式。"""
    if state == "VIC":
        idx = int(distance // 5)
        zone_num = (idx // 2) + 1
        is_half = idx % 2 == 1
        return f"Z{zone_num}.5" if is_half else f"Z{zone_num}"
    return f"Z{int(distance // 10) + 1}"


def _parse_number(val: Any) -> float:
    """安全地从 Bitable 字段提取数值（兼容 lookup 返回的 list 格式如 [38]）。"""
    if val is None:
        return 0.0
    if isinstance(val, list):
        return _parse_number(val[0]) if val else 0.0
    if isinstance(val, (int, float)):
        return float(val)
    try:
        return float(str(val).strip().replace(",", ""))
    except (ValueError, TypeError):
        return 0.0


class QuoteEngine:
    """报价计算引擎 — 读 Input → 批量加载价格表 → 计算 → batch_update Output。"""

    def __init__(
        self,
        quote_input_repo: QuoteInputRepository | None = None,
        quote_output_repo: QuoteOutputRepository | None = None,
        base_node_repo: BaseNodeRepository | None = None,
    ) -> None:
        self._input_repo = quote_input_repo or QuoteInputRepository()
        self._output_repo = quote_output_repo or QuoteOutputRepository()
        self._base_node_repo = base_node_repo or BaseNodeRepository()

    async def calculate(self, record_id: str) -> dict[str, Any]:
        """完整报价计算流程。"""
        # Step 1: 读 Op-Quote Input
        input_rec = await self._input_repo.findOne(QueryWrapper().eq("record_id", record_id))
        if not input_rec:
            return {"error": "record not found"}

        # Step 2: 确定 state + price_level_rid
        state = await self._resolve_state(input_rec)
        if not state:
            return {"error": "cannot determine state from Base Node"}

        price_level_rid = await self._resolve_price_level_rid(input_rec, state)
        if not price_level_rid:
            return {"error": f"no Price Level found for state={state}"}

        # Step 3: 并发加载 6 张价格表
        loader = PriceLoader()
        await loader.load(price_level_rid)

        # Step 4: 提取输入参数
        distance = _parse_number(input_rec.get("Distance"))
        tc_val = input_rec.get("Toll Code")
        toll_code = extract_select_text(tc_val[0] if isinstance(tc_val, list) else tc_val).strip()
        fuel_rate = _parse_number(input_rec.get("Fuel Rate"))
        dg_rate = _parse_number(input_rec.get("DG Rate"))
        rural_tailgate = await self._resolve_rural_tailgate(input_rec)
        specific_raw = input_rec.get("Specific") or ""
        is_dg = "DG Quote" in (specific_raw if isinstance(specific_raw, str) else ", ".join(specific_raw))
        zone_code = _distance_to_zone(distance, state)

        # 自定义价格
        custom_prices: dict[tuple[str, str], float | None] = {}
        for field_name, combo in _CUSTOM_PRICE_FIELDS.items():
            val = input_rec.get(field_name)
            custom_prices[combo] = float(val) if val and _parse_number(val) > 0 else None

        # Step 5: 计算每种组合的全部费用
        fee_map: dict[tuple[str, str, str], float | None] = {}

        for ctn_size, deliver_type in _COMBOS:
            combo = (ctn_size, deliver_type)
            is_sdl = "Sideloader" in deliver_type
            is_drop = "Drop" in deliver_type

            # 1. Cartage Fee — 优先自定义价 → 查表 → 超 zone 公式兜底
            cartage = custom_prices.get(combo)
            if cartage is None:
                cartage = loader.find_cartage(zone_code, ctn_size, deliver_type)
            if cartage is None and distance > 0:
                cartage = _over_zone_cartage(distance, ctn_size, deliver_type)
            fee_map[("Cartage Fee", ctn_size, deliver_type)] = cartage

            # 2. Fuel Surcharge
            fee_map[("Fuel Surcharge", ctn_size, deliver_type)] = (
                round(cartage * fuel_rate, 2) if cartage and fuel_rate else None
            )

            # 3. TimeSlot Booking Fee
            fee_map[("TimeSlot Booking Fee", ctn_size, deliver_type)] = loader.find_terminal("TimeSlot Booking Fee")

            # 4. Infrastructure Fee
            fee_map[("Infrasucure Fee", ctn_size, deliver_type)] = loader.find_terminal("Infrasucure Fee")

            # 5. Sideloader Fee (仅 SDL)
            if is_sdl:
                fee_map[("Sideloader Fee", ctn_size, deliver_type)] = loader.find_terminal("Sideloader Fee")

            # 6. Empty De-hire Booking Fee
            fee_map[("Empty De-hire Booking Fee", ctn_size, deliver_type)] = loader.find_empty("Default")

            # 7. Toll Surcharge
            fee_map[("Toll Surcharge", ctn_size, deliver_type)] = loader.find_toll(toll_code) if toll_code else None

            # 8. Via Tailgate Surcharge (仅 Rural Tailgate=Y)
            fee_map[("Via Tailgate Surcharge", ctn_size, deliver_type)] = (
                loader.find_extra("VIATAILGATE") if rural_tailgate else None
            )

            # 9. DG Surcharge (仅 Specific 含 DG Quote)
            fee_map[("DG Surcharge", ctn_size, deliver_type)] = (
                round(cartage * dg_rate, 2) if is_dg and cartage and dg_rate else None
            )

            # 10-13. Overweight Surcharges (SDL: 4 档)
            if is_sdl:
                fee_map[("Overweight Surcharge(22-23.9t)", ctn_size, deliver_type)] = (
                    loader.find_overweight("22 < ctn_weight < 24", "Sideloader(SDL)")
                )
                fee_map[("Overweight Surcharge(24-27.9t)", ctn_size, deliver_type)] = (
                    loader.find_overweight("24 <= ctn_weight < 27", "Sideloader(SDL)")
                )
                fee_map[("Overweight Surcharge(27.0-28.0tones)", ctn_size, deliver_type)] = (
                    loader.find_overweight("27 <= ctn_weight < 28", "Sideloader(SDL)")
                )
                fee_map[("Overweight Surcharge(28-29t)", ctn_size, deliver_type)] = (
                    loader.find_overweight("ctn_weight >= 28", "Sideloader(SDL)")
                )
            else:
                # 14. STD/DROP: 只有 28t+
                fee_map[("Overweight Surcharge(28-29t)", ctn_size, deliver_type)] = (
                    loader.find_overweight("ctn_weight >= 28", "Standard Trailer(STD)")
                )

            # 15. Lifting Fee
            fee_map[("Lifting Fee", ctn_size, deliver_type)] = loader.find_extra("LIFTING")

            # 16. Via Yard Fee
            fee_map[("Via Yard Fee", ctn_size, deliver_type)] = loader.find_extra("VIAYARD")

            # 17. Yard Storage Fee (分 20/40)
            storage_code = f"{ctn_size}'STORAGE"
            fee_map[("Yard Storage Fee", ctn_size, deliver_type)] = loader.find_extra(storage_code)

            # 18. Failuretrip
            fee_map[("Failuretrip (within 20kms)", ctn_size, deliver_type)] = loader.find_extra("FAIURETRIP")

            # 19. Waiting Fee (分 SDL vs STD/DROP)
            waiting_code = "Waitting Sideloader" if is_sdl else "Waitting Trailer"
            fee_map[("Waiting Fee", ctn_size, deliver_type)] = loader.find_extra(waiting_code)

            # 20. Drop Trailer Fee (仅 DROP)
            if is_drop:
                fee_map[("Drop Trailer Fee", ctn_size, deliver_type)] = loader.find_extra("DROPTRAILER")

            # 21. Terminal Waiting Fee (仅 VIC)
            fee_map[("Terminal Wating Fee", ctn_size, deliver_type)] = (
                loader.find_terminal("Terminal Wating Fee") if state == "VIC" else None
            )

            # 22. TimeSlot Cancel Fee
            fee_map[("TimeSlot Cancel Fee", ctn_size, deliver_type)] = loader.find_terminal("TimeSlot Cancel Fee")

        # Step 6: 读 Op-Quote Output，建 (fee_name, ctn_size, deliver_type) → record_id map
        output_records = await self._output_repo.list(QueryWrapper())
        output_map: dict[tuple[str, str, str], str] = {}
        for r in output_records:
            fn = (r.get("Fee Name") or "").strip()
            cs = extract_select_text(r.get("Container Size")).strip()
            dt = extract_select_text(r.get("Deliver Type")).strip()
            if fn and cs and dt:
                output_map[(fn, cs, dt)] = r["record_id"]

        # Step 7: batch_update
        wrappers: list[UpdateWrapper] = []
        updated_count = 0
        for (fee_name, ctn_size, deliver_type), amount in fee_map.items():
            rid = output_map.get((fee_name, ctn_size, deliver_type))
            if not rid:
                continue
            if amount is not None:
                wrappers.append(
                    UpdateWrapper().eq("record_id", rid).set("Amount", round(amount, 2))
                )
                updated_count += 1

        if wrappers:
            await self._output_repo.batch_update(wrappers)

        logger.info("报价计算完成: record=%s, state=%s, zone=%s, 更新=%d 项", record_id, state, zone_code, updated_count)

        return {
            "state": state,
            "zone": zone_code,
            "distance": distance,
            "fuel_rate": fuel_rate,
            "dg_rate": dg_rate,
            "toll_code": toll_code,
            "rural_tailgate": rural_tailgate,
            "is_dg": is_dg,
            "calculated": len(fee_map),
            "updated": updated_count,
        }

    async def _resolve_state(self, input_rec: dict) -> str | None:
        """从 Base Node 反查 MD-Base Node 获取 State。"""
        bn_text = extract_cell_text(input_rec.get("Base Node")) or ""
        if not bn_text:
            return None
        record = await self._base_node_repo.findOne(QueryWrapper().eq("Base Node", bn_text))
        if not record:
            return None
        return extract_select_text(record.get("State")).strip().upper() or None

    async def _resolve_rural_tailgate(self, input_rec: dict) -> bool:
        """从 MD-Suburb 读 Rural Tailgate（Input 的 lookup 字段返回 option ID，不可靠）。"""
        from app.repository.suburb import SuburbRepository

        suburb_text = extract_cell_text(input_rec.get("Suburb")) or ""
        if not suburb_text:
            return False
        repo = SuburbRepository()
        records = await repo.list(QueryWrapper())
        for r in records:
            if (r.get("Suburb") or "").strip().upper() == suburb_text.strip().upper():
                return (r.get("Rural Tailgate") or "").strip().upper() == "Y"
        return False

    async def _resolve_price_level_rid(self, input_rec: dict, state: str) -> str | None:
        """从 Op-Quote Input 的 lookup 字段获取对应 state 的 Price Level record_id。

        MD-Price Level(NSW) / MD-Price Level(VIC) 是 lookup 字段，
        值为显示文本（如 "NR NSW"），需要反查 MD-Price Level 获取 record_id。
        """
        from app.service.pricing.price_loader import _Repo
        from app.common.lark_tables import T

        field = "MD-Price Level(NSW)" if state == "NSW" else "MD-Price Level(VIC)"
        pl_text = extract_cell_text(input_rec.get(field)) or ""
        if not pl_text:
            return None

        repo = _Repo(T.md_price_level.id)
        records = await repo.list(QueryWrapper())
        for r in records:
            if (r.get("Description") or "").strip() == pl_text.strip():
                return r["record_id"]
        return None

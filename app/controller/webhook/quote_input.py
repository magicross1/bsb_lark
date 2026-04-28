from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel

from app.common.response import ApiResponse
from app.service.geocoding.suburb_resolve import SuburbResolveService
from app.service.pricing.quote_engine import QuoteEngine

logger = logging.getLogger(__name__)

router = APIRouter()

_suburb_svc = SuburbResolveService()
_quote_engine = QuoteEngine()


class RecordIdRequest(BaseModel):
    """Lark 自动化 webhook 通用请求体。"""

    record_id: str


@router.post("/quote-input/suburb-resolve")
async def resolve_suburb(req: RecordIdRequest):
    """Deliver Address / Base Node 变更 → 解析 Suburb + Distance Matrix → 写回。"""
    result = await _suburb_svc.resolve_and_update(req.record_id)
    return ApiResponse.ok(data=result)


@router.post("/quote-input/calculate")
async def calculate_quote(req: RecordIdRequest):
    """Start Quote → 一次性计算 96 项费用 → batch_update Op-Quote Output。"""
    result = await _quote_engine.calculate(req.record_id)
    return ApiResponse.ok(data=result)

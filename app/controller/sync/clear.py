from __future__ import annotations

import logging

from fastapi import APIRouter

from app.common.response import ApiResponse
from app.service.sync.model.clear_sync_schemas import ClearSyncRequest, ClearBatchSyncRequest
from app.service.sync.clear_sync import ClearSyncService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["sync"])

_clear_sync = ClearSyncService()


@router.get("/clear/conditions")
async def list_clear_conditions():
    return ApiResponse.ok(ClearSyncService.list_conditions())


@router.post("/clear")
async def sync_clear(req: ClearSyncRequest):
    result = await _clear_sync.sync(
        container_numbers=req.container_numbers,
        terminal_full_name=req.terminal_full_name,
    )
    return ApiResponse.ok(result.model_dump())


@router.post("/clear/batch")
async def sync_clear_batch(req: ClearBatchSyncRequest):
    result = await _clear_sync.sync_batch(condition=req.condition)
    return ApiResponse.ok(result.model_dump())

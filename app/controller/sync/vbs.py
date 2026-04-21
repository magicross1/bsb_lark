from __future__ import annotations

import logging

from fastapi import APIRouter

from app.common.response import ApiResponse
from app.service.sync.request.vbs_batch_sync_request import VbsBatchSyncRequest
from app.service.sync.request.vbs_sync_request import VbsSyncRequest
from app.service.sync.scene.vbs.vbs_sync_service import VbsSyncService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["sync"])

_vbs_sync = VbsSyncService()


@router.get("/vbs/conditions")
async def list_vbs_conditions():
    return ApiResponse.ok(VbsSyncService.list_conditions())


@router.post("/vbs")
async def sync_vbs(req: VbsSyncRequest):
    result = await _vbs_sync.sync(
        container_numbers=req.container_numbers,
        terminal_full_name=req.terminal_full_name,
    )
    return ApiResponse.ok(result.model_dump())


@router.post("/vbs/batch")
async def sync_vbs_batch(req: VbsBatchSyncRequest):
    result = await _vbs_sync.sync_batch(condition=req.condition)
    return ApiResponse.ok(result.model_dump())

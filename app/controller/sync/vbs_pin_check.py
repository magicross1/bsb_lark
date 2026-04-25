from __future__ import annotations

import logging

from fastapi import APIRouter

from app.common.response import ApiResponse
from app.service.sync.request.vbs_pin_check_batch_sync_request import VbsPinCheckBatchSyncRequest
from app.service.sync.request.vbs_pin_check_sync_request import VbsPinCheckSyncRequest
from app.service.sync.scene.vbs_pin_check.vbs_pin_check_sync import VbsPinCheckSyncService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["sync"])

_svc = VbsPinCheckSyncService()


@router.get("/vbs-pin-check/conditions")
async def list_vbs_pin_check_conditions():
    return ApiResponse.ok(VbsPinCheckSyncService.list_conditions())


@router.post("/vbs-pin-check")
async def sync_vbs_pin_check(req: VbsPinCheckSyncRequest):
    result = await _svc.sync_single(req.container_number, req.terminal_full_name)
    return ApiResponse.ok(result.model_dump())


@router.post("/vbs-pin-check/batch")
async def sync_vbs_pin_check_batch(req: VbsPinCheckBatchSyncRequest):
    result = await _svc.sync_batch(condition=req.condition)
    return ApiResponse.ok(result.model_dump())

from __future__ import annotations

import logging

from fastapi import APIRouter

from app.common.response import ApiResponse
from app.service.sync.request.vbs_add_container_batch_sync_request import VbsAddContainerBatchSyncRequest
from app.service.sync.request.vbs_add_container_sync_request import VbsAddContainerSyncRequest
from app.service.sync.scene.vbs_add_container.vbs_add_container_sync import VbsAddContainerSyncService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["sync"])

_svc = VbsAddContainerSyncService()


@router.get("/vbs-add-container/conditions")
async def list_vbs_add_container_conditions():
    return ApiResponse.ok(VbsAddContainerSyncService.list_conditions())


@router.post("/vbs-add-container")
async def sync_vbs_add_container(req: VbsAddContainerSyncRequest):
    result = await _svc.sync_single(req.container_number, req.terminal_full_name)
    return ApiResponse.ok(result.model_dump())


@router.post("/vbs-add-container/batch")
async def sync_vbs_add_container_batch(req: VbsAddContainerBatchSyncRequest):
    result = await _svc.sync_batch(condition=req.condition)
    return ApiResponse.ok(result.model_dump())

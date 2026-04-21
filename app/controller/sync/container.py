from __future__ import annotations

import logging

from fastapi import APIRouter

from app.common.response import ApiResponse
from app.service.sync.request.container_batch_sync_request import ContainerBatchSyncRequest
from app.service.sync.request.container_sync_request import ContainerSyncRequest
from app.service.sync.scene.container.container_sync import ContainerSyncService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["sync"])

_container_sync = ContainerSyncService()


@router.get("/container/conditions")
async def list_container_conditions():
    return ApiResponse.ok(ContainerSyncService.list_conditions())


@router.post("/container")
async def sync_container(req: ContainerSyncRequest):
    result = await _container_sync.sync(req.container_numbers)
    return ApiResponse.ok(result.model_dump())


@router.post("/container/batch")
async def sync_container_batch(req: ContainerBatchSyncRequest):
    result = await _container_sync.sync_batch(condition=req.condition)
    return ApiResponse.ok(result.model_dump())

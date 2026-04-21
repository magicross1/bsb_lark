from __future__ import annotations

import logging

from fastapi import APIRouter

from app.common.response import ApiResponse
from app.service.sync.request.vessel_batch_sync_request import VesselBatchSyncRequest
from app.service.sync.request.vessel_sync_request import VesselSyncRequest
from app.service.sync.scene.vessel.vessel_sync import VesselSyncService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["sync"])

_vessel_sync = VesselSyncService()


@router.get("/vessel/conditions")
async def list_vessel_conditions():
    return ApiResponse.ok(VesselSyncService.list_conditions())


@router.post("/vessel")
async def sync_vessel(req: VesselSyncRequest):
    result = await _vessel_sync.sync_single(req.record_id)
    return ApiResponse.ok(result.model_dump())


@router.post("/vessel/batch")
async def sync_vessel_batch(req: VesselBatchSyncRequest):
    result = await _vessel_sync.sync_batch(
        condition=req.condition,
        base_node=req.base_node,
    )
    return ApiResponse.ok(result.model_dump())

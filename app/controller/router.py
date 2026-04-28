from __future__ import annotations

from fastapi import APIRouter

from app.controller.data import router as data_router
from app.controller.llm.llm import router as llm_router
from app.controller.sync.container import router as sync_container_router
from app.controller.sync.clear import router as sync_clear_router
from app.controller.sync.vbs import router as sync_vbs_router
from app.controller.sync.vbs_add_container import router as sync_vbs_add_container_router
from app.controller.sync.vbs_pin_check import router as sync_vbs_pin_check_router
from app.controller.sync.vessel import router as sync_vessel_router
from app.controller.webhook import router as webhook_router

router = APIRouter()
router.include_router(data_router)
router.include_router(llm_router)
router.include_router(webhook_router)
router.include_router(sync_vessel_router)
router.include_router(sync_container_router)
router.include_router(sync_clear_router)
router.include_router(sync_vbs_router)
router.include_router(sync_vbs_add_container_router)
router.include_router(sync_vbs_pin_check_router)

__all__ = ["router"]

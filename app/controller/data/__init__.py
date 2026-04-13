from __future__ import annotations

from fastapi import APIRouter

from .consingee import router as consingee_router
from .distance_matrix import router as distance_matrix_router
from .driver import router as driver_router
from .empty_park import router as empty_park_router
from .freight_forwarder import router as freight_forwarder_router
from .suburb import router as suburb_router
from .terminal import router as terminal_router
from .vehicle import router as vehicle_router
from .warehouse_address import router as warehouse_address_router

router = APIRouter(prefix="/master-data", tags=["Master Data"])

router.include_router(warehouse_address_router)
router.include_router(consingee_router)
router.include_router(suburb_router)
router.include_router(driver_router)
router.include_router(vehicle_router)
router.include_router(terminal_router)
router.include_router(freight_forwarder_router)
router.include_router(empty_park_router)
router.include_router(distance_matrix_router)

__all__ = ["router"]

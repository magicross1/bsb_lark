from __future__ import annotations

from fastapi import APIRouter

from app.controller.data import router as data_router
from app.controller.llm.llm import router as llm_router

router = APIRouter()
router.include_router(data_router)
router.include_router(llm_router)

__all__ = ["router"]

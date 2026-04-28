from __future__ import annotations

from fastapi import APIRouter

from app.controller.webhook.quote_input import router as quote_input_router

router = APIRouter(prefix="/webhook", tags=["webhook"])
router.include_router(quote_input_router)

__all__ = ["router"]

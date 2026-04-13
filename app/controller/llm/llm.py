from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile

from app.common.response import ApiResponse
from app.service.llm_service.llm_service import llm_service

cartage_router = APIRouter(prefix="/cartage", tags=["Cartage Operations"])

edo_router = APIRouter(prefix="/edo", tags=["EDO Operations"])

router = APIRouter()
router.include_router(cartage_router)
router.include_router(edo_router)


# ── Cartage ─────────────────────────────────────────────────


@cartage_router.post("/parse")
async def parse_cartage_document(
    file: UploadFile = File(..., description="PDF, image, or TXT file"),  # noqa: B008
    model: str = Form(default="glm-5v-turbo"),
):
    suffix = Path(file.filename or "").suffix.lower()
    allowed = {".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tiff", ".txt", ".text"}
    if suffix not in allowed:
        return ApiResponse.error(message=f"Unsupported file type: {suffix}. Allowed: {sorted(allowed)}")

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        result = await llm_service.parse_cartage_document(tmp_path, model=model)
        return ApiResponse.ok(data=result.model_dump())
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)


@cartage_router.post("/parse-text")
async def parse_cartage_text(
    text: str = Form(..., description="Cartage document text content"),
    model: str = Form(default="glm-5v-turbo"),
):
    result = await llm_service.parse_cartage_text(text, model=model)
    return ApiResponse.ok(data=result.model_dump())


@cartage_router.post("/process")
async def process_cartage_document(
    file: UploadFile = File(..., description="PDF, image, or TXT file"),  # noqa: B008
    model: str = Form(default="glm-5v-turbo"),
):
    suffix = Path(file.filename or "").suffix.lower()
    allowed = {".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tiff", ".txt", ".text"}
    if suffix not in allowed:
        return ApiResponse.error(message=f"Unsupported file type: {suffix}. Allowed: {sorted(allowed)}")

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        result = await llm_service.process_cartage_document(tmp_path, model=model)
        return ApiResponse.ok(data=result.model_dump())
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)


@cartage_router.post("/process-text")
async def process_cartage_text(
    text: str = Form(..., description="Cartage document text content"),
    model: str = Form(default="glm-5v-turbo"),
):
    result = await llm_service.process_cartage_text(text, model=model)
    return ApiResponse.ok(data=result.model_dump())


@cartage_router.post("/clear-cache")
async def clear_cartage_cache():
    llm_service.clear_cartage_cache()
    return ApiResponse.ok(message="cache cleared")


# ── EDO ─────────────────────────────────────────────────────


@edo_router.post("/parse")
async def parse_edo_document(
    file: UploadFile = File(..., description="PDF or image file"),  # noqa: B008
    model: str = Form(default="glm-5v-turbo"),
):
    suffix = Path(file.filename or "").suffix.lower()
    allowed = {".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tiff", ".txt", ".text"}
    if suffix not in allowed:
        return ApiResponse.error(message=f"Unsupported file type: {suffix}. Allowed: {sorted(allowed)}")

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        result = await llm_service.parse_edo(tmp_path, model=model)
        return ApiResponse.ok(data=result.model_dump())
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)

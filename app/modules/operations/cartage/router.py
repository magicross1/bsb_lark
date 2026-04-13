from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile

from app.core.response import ApiResponse
from app.modules.operations.cartage.service import CartageService

router = APIRouter(prefix="/cartage", tags=["Cartage Operations"])

_service = CartageService()


@router.post("/parse")
async def parse_cartage_document(
    file: UploadFile = File(..., description="PDF, image, or TXT file"),
    model: str = Form(default="glm-5v-turbo"),
):
    suffix = Path(file.filename or "").suffix.lower()
    allowed = {".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tiff", ".txt", ".text"}
    if suffix not in allowed:
        return ApiResponse.error(message=f"Unsupported file type: {suffix}. Allowed: {sorted(allowed)}")

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        result = await _service.parse_document(tmp_path, model=model)
        return ApiResponse.ok(data=result.model_dump())
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@router.post("/parse-text")
async def parse_cartage_text(
    text: str = Form(..., description="Cartage document text content"),
    model: str = Form(default="glm-5v-turbo"),
):
    result = await _service.parse_text(text, model=model)
    return ApiResponse.ok(data=result.model_dump())


@router.post("/process")
async def process_cartage_document(
    file: UploadFile = File(..., description="PDF, image, or TXT file"),
    model: str = Form(default="glm-5v-turbo"),
):
    suffix = Path(file.filename or "").suffix.lower()
    allowed = {".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tiff", ".txt", ".text"}
    if suffix not in allowed:
        return ApiResponse.error(message=f"Unsupported file type: {suffix}. Allowed: {sorted(allowed)}")

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        result = await _service.process_document(tmp_path, model=model)
        return ApiResponse.ok(data=result.model_dump())
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@router.post("/process-text")
async def process_cartage_text(
    text: str = Form(..., description="Cartage document text content"),
    model: str = Form(default="glm-5v-turbo"),
):
    result = await _service.process_text(text, model=model)
    return ApiResponse.ok(data=result.model_dump())


@router.post("/clear-cache")
async def clear_cartage_cache():
    _service.clear_cache()
    return ApiResponse.ok(message="cache cleared")

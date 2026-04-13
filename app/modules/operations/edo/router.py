from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile

from app.core.response import ApiResponse
from app.modules.operations.edo.parser import EdoParser

router = APIRouter(prefix="/edo", tags=["EDO Operations"])


@router.post("/parse")
async def parse_edo_document(
    file: UploadFile = File(..., description="PDF or image file"),
    model: str = Form(default="glm-5v-turbo"),
):
    suffix = Path(file.filename or "").suffix.lower()
    allowed = {".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tiff"}
    if suffix not in allowed:
        return ApiResponse.error(message=f"Unsupported file type: {suffix}. Allowed: {sorted(allowed)}")

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        parser = EdoParser(model=model)
        result = parser.parse(tmp_path)
        return ApiResponse.ok(data=result.model_dump())
    finally:
        Path(tmp_path).unlink(missing_ok=True)

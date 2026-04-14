from __future__ import annotations

import base64
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import fitz
from zhipuai import ZhipuAI

from app.config.app_settings import settings
from app.core.llm import get_llm_client, model_requires_thinking

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tiff"}
PDF_EXTENSIONS = {".pdf"}


def pdf_to_images(pdf_path: str | Path) -> list[str]:
    doc = fitz.open(str(pdf_path))
    pages: list[str] = []
    for page in doc:
        pix = page.get_pixmap(dpi=200)
        img_bytes = pix.tobytes("png")
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        pages.append(b64)
    doc.close()
    return pages


def image_to_base64(image_path: str | Path) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def extract_json_from_response(raw: str) -> dict[str, Any] | None:
    json_str = raw
    if "```json" in raw:
        json_str = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        json_str = raw.split("```")[1].split("```")[0].strip()
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None


class BaseParser(ABC):
    system_prompt: str
    user_hint: str

    def __init__(
        self,
        client: ZhipuAI | None = None,
        *,
        model: str | None = None,
    ) -> None:
        self._client = client or get_llm_client()
        self._model = model if model is not None else settings.AI_MODEL

    def parse(self, source: str | Path) -> Any:
        source = Path(source) if not isinstance(source, Path) else source
        suffix = source.suffix.lower()

        if suffix in PDF_EXTENSIONS:
            return self.parse_pdf(source)
        if suffix in IMAGE_EXTENSIONS:
            return self.parse_image(source)
        if suffix in {".txt", ".text"}:
            return self.parse_text_file(source)
        raise ValueError(f"Unsupported file type: {suffix}")

    def parse_pdf(self, pdf_path: str | Path) -> Any:
        images = pdf_to_images(pdf_path)
        return self._parse_images(images)

    def parse_image(self, image_path: str | Path) -> Any:
        b64 = image_to_base64(image_path)
        return self._parse_images([b64])

    def parse_base64_images(self, images: list[str]) -> Any:
        return self._parse_images(images)

    def parse_text(self, text: str) -> Any:
        return self._parse_text(text)

    def parse_text_file(self, file_path: str | Path) -> Any:
        text = Path(file_path).read_text(encoding="utf-8")
        return self._parse_text(text)

    def _build_image_messages(self, images: list[str]) -> list[dict[str, Any]]:
        content: list[dict[str, Any]] = [
            {"type": "text", "text": self.user_hint},
        ]
        for img_b64 in images:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{img_b64}"},
                }
            )
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": content},
        ]

    def _build_text_messages(self, text: str) -> list[dict[str, Any]]:
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": text},
        ]

    def _create_completion(self, messages: list[dict[str, Any]]) -> str:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": 4096,
        }
        if model_requires_thinking(self._model):
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": 8192}
        response = self._client.chat.completions.create(**kwargs)
        return response.choices[0].message.content.strip()

    def _parse_images(self, images: list[str]) -> Any:
        messages = self._build_image_messages(images)
        raw = self._create_completion(messages)
        return self.build_result(raw)

    def _parse_text(self, text: str) -> Any:
        messages = self._build_text_messages(text)
        raw = self._create_completion(messages)
        return self.build_result(raw)

    @abstractmethod
    def build_result(self, raw: str) -> Any: ...

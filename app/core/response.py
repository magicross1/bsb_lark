from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse


class ApiResponse:
    @staticmethod
    def ok(data: Any = None, message: str = "success") -> JSONResponse:
        return JSONResponse(content={"code": 0, "data": data, "message": message})

    @staticmethod
    def error(code: int = -1, message: str = "error", data: Any = None) -> JSONResponse:
        return JSONResponse(content={"code": code, "data": data, "message": message}, status_code=400)

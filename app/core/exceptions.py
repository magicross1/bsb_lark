from __future__ import annotations


class AppError(Exception):
    def __init__(self, code: int = -1, message: str = "error", *, detail: str = ""):
        self.code = code
        self.message = message
        self.detail = detail
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, resource: str = "resource", detail: str = ""):
        super().__init__(code=404, message=f"{resource} not found", detail=detail)


class ValidationError(AppError):
    def __init__(self, message: str = "validation error", detail: str = ""):
        super().__init__(code=422, message=message, detail=detail)


class LarkApiError(AppError):
    def __init__(self, lark_code: int, message: str, detail: str = ""):
        super().__init__(code=lark_code, message=message, detail=detail)

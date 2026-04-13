from __future__ import annotations

from fastapi import FastAPI

from .middleware import RequestContextMiddleware

_registered_modules: list[str] = []


def register_modules(app: FastAPI) -> None:
    del app


def get_registered_modules() -> list[str]:
    return list(_registered_modules)


__all__ = [
    "RequestContextMiddleware",
    "get_registered_modules",
    "register_modules",
]

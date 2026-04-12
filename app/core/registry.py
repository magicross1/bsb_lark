from __future__ import annotations

import importlib
import pkgutil
from typing import Any

from fastapi import FastAPI

_MODULE_REGISTRY: dict[str, dict[str, Any]] = {}


def register_modules(app: FastAPI) -> None:
    from app import modules

    for module_info in pkgutil.iter_modules(modules.__path__):
        module_name = module_info.name
        try:
            router_module = importlib.import_module(f"app.modules.{module_name}.router")
        except (ImportError, ModuleNotFoundError):
            continue

        router = getattr(router_module, "router", None)
        if router is not None:
            app.include_router(router)
            _MODULE_REGISTRY[module_name] = {
                "prefix": router.prefix,
                "routes": [r.path for r in router.routes],
            }


def get_registered_modules() -> dict[str, dict[str, Any]]:
    return _MODULE_REGISTRY

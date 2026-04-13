from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.config.app_settings import settings
from app.controller.router import router as app_router
from app.core.midlleware import (
    RequestContextMiddleware,
    get_registered_modules,
    register_modules,
)

app = FastAPI(
    title="BSB Lark API",
    description="BSB Transport Australia - Lark-based logistics backend",
    version="0.1.0",
)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_modules(app)
app.include_router(app_router)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.ENV}


@app.get("/modules")
async def list_modules():
    return get_registered_modules()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=settings.ENV == "development")

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.common.response import ApiResponse
from app.service.master.suburb import suburb_service as service

router = APIRouter()


@router.get("/suburbs")
async def list_suburbs(
    page_size: int = Query(default=100, le=500),
    page_token: str | None = Query(default=None),
    filter_expr: str | None = Query(default=None),
) -> JSONResponse:
    records, next_token = await service.list_suburbs(
        page_size=page_size,
        page_token=page_token,
        filter_expr=filter_expr,
    )
    return ApiResponse.ok(data={"records": records, "next_page_token": next_token})


@router.get("/suburbs/all")
async def list_all_suburbs(
    filter_expr: str | None = Query(default=None),
) -> JSONResponse:
    records = await service.list_all_suburbs(filter_expr=filter_expr)
    return ApiResponse.ok(data={"records": records, "total": len(records)})


@router.get("/suburbs/{record_id}")
async def get_suburb(record_id: str) -> JSONResponse:
    record = await service.get_suburb(record_id)
    return ApiResponse.ok(data=record)


@router.post("/suburbs")
async def create_suburb(fields: dict[str, Any]) -> JSONResponse:
    record = await service.create_suburb(fields)
    return ApiResponse.ok(data=record, message="created")


@router.patch("/suburbs/{record_id}")
async def update_suburb(record_id: str, fields: dict[str, Any]) -> JSONResponse:
    record = await service.update_suburb(record_id, fields)
    return ApiResponse.ok(data=record, message="updated")


@router.delete("/suburbs/{record_id}")
async def delete_suburb(record_id: str) -> JSONResponse:
    await service.delete_suburb(record_id)
    return ApiResponse.ok(message="deleted")

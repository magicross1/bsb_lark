from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.common.response import ApiResponse
from app.service.master.empty_park import empty_park_service as service

router = APIRouter()


@router.get("/empty-parks")
async def list_empty_parks(
    page_size: int = Query(default=100, le=500),
    page_token: str | None = Query(default=None),
    filter_expr: str | None = Query(default=None),
) -> JSONResponse:
    records, next_token = await service.list_empty_parks(
        page_size=page_size,
        page_token=page_token,
        filter_expr=filter_expr,
    )
    return ApiResponse.ok(data={"records": records, "next_page_token": next_token})


@router.get("/empty-parks/all")
async def list_all_empty_parks(
    filter_expr: str | None = Query(default=None),
) -> JSONResponse:
    records = await service.list_all_empty_parks(filter_expr=filter_expr)
    return ApiResponse.ok(data={"records": records, "total": len(records)})


@router.post("/empty-parks")
async def create_empty_park(fields: dict[str, Any]) -> JSONResponse:
    record = await service.create_empty_park(fields)
    return ApiResponse.ok(data=record, message="created")


@router.patch("/empty-parks/{record_id}")
async def update_empty_park(record_id: str, fields: dict[str, Any]) -> JSONResponse:
    record = await service.update_empty_park(record_id, fields)
    return ApiResponse.ok(data=record, message="updated")


@router.delete("/empty-parks/{record_id}")
async def delete_empty_park(record_id: str) -> JSONResponse:
    await service.delete_empty_park(record_id)
    return ApiResponse.ok(message="deleted")

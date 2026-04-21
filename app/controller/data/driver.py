from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.common.response import ApiResponse
from app.service.master.driver import driver_service as service

router = APIRouter()


@router.get("/drivers")
async def list_drivers(
    page_size: int = Query(default=100, le=500),
    page_token: str | None = Query(default=None),
    filter_expr: str | None = Query(default=None),
) -> JSONResponse:
    records, next_token = await service.list_drivers(
        page_size=page_size,
        page_token=page_token,
        filter_expr=filter_expr,
    )
    return ApiResponse.ok(data={"records": records, "next_page_token": next_token})


@router.get("/drivers/all")
async def list_all_drivers(
    filter_expr: str | None = Query(default=None),
) -> JSONResponse:
    records = await service.list_all_drivers(filter_expr=filter_expr)
    return ApiResponse.ok(data={"records": records, "total": len(records)})


@router.post("/drivers")
async def create_driver(fields: dict[str, Any]) -> JSONResponse:
    record = await service.create_driver(fields)
    return ApiResponse.ok(data=record, message="created")


@router.patch("/drivers/{record_id}")
async def update_driver(record_id: str, fields: dict[str, Any]) -> JSONResponse:
    record = await service.update_driver(record_id, fields)
    return ApiResponse.ok(data=record, message="updated")


@router.delete("/drivers/{record_id}")
async def delete_driver(record_id: str) -> JSONResponse:
    await service.delete_driver(record_id)
    return ApiResponse.ok(message="deleted")

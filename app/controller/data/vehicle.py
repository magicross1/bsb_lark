from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.common.response import ApiResponse
from app.service.master.vehicle import vehicle_service as service

router = APIRouter()


@router.get("/vehicles")
async def list_vehicles(
    page_size: int = Query(default=100, le=500),
    page_token: str | None = Query(default=None),
    filter_expr: str | None = Query(default=None),
) -> JSONResponse:
    records, next_token = await service.list_vehicles(
        page_size=page_size,
        page_token=page_token,
        filter_expr=filter_expr,
    )
    return ApiResponse.ok(data={"records": records, "next_page_token": next_token})


@router.get("/vehicles/all")
async def list_all_vehicles(
    filter_expr: str | None = Query(default=None),
) -> JSONResponse:
    records = await service.list_all_vehicles(filter_expr=filter_expr)
    return ApiResponse.ok(data={"records": records, "total": len(records)})


@router.post("/vehicles")
async def create_vehicle(fields: dict[str, Any]) -> JSONResponse:
    record = await service.create_vehicle(fields)
    return ApiResponse.ok(data=record, message="created")


@router.patch("/vehicles/{record_id}")
async def update_vehicle(record_id: str, fields: dict[str, Any]) -> JSONResponse:
    record = await service.update_vehicle(record_id, fields)
    return ApiResponse.ok(data=record, message="updated")


@router.delete("/vehicles/{record_id}")
async def delete_vehicle(record_id: str) -> JSONResponse:
    await service.delete_vehicle(record_id)
    return ApiResponse.ok(message="deleted")

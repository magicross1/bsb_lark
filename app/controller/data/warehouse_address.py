from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.common.response import ApiResponse
from app.service.master.warehouse_address import warehouse_address_service as service

router = APIRouter()


@router.get("/warehouse-addresses")
async def list_warehouse_addresses(
    page_size: int = Query(default=100, le=500),
    page_token: str | None = Query(default=None),
    filter_expr: str | None = Query(default=None),
) -> JSONResponse:
    records, next_token = await service.list_warehouse_addresses(
        page_size=page_size,
        page_token=page_token,
        filter_expr=filter_expr,
    )
    return ApiResponse.ok(data={"records": records, "next_page_token": next_token})


@router.get("/warehouse-addresses/all")
async def list_all_warehouse_addresses(
    filter_expr: str | None = Query(default=None),
) -> JSONResponse:
    records = await service.list_all_warehouse_addresses(filter_expr=filter_expr)
    return ApiResponse.ok(data={"records": records, "total": len(records)})


@router.get("/warehouse-addresses/{record_id}")
async def get_warehouse_address(record_id: str) -> JSONResponse:
    record = await service.get_warehouse_address(record_id)
    return ApiResponse.ok(data=record)


@router.post("/warehouse-addresses")
async def create_warehouse_address(fields: dict[str, Any]) -> JSONResponse:
    record = await service.create_warehouse_address(fields)
    return ApiResponse.ok(data=record, message="created")


@router.patch("/warehouse-addresses/{record_id}")
async def update_warehouse_address(record_id: str, fields: dict[str, Any]) -> JSONResponse:
    record = await service.update_warehouse_address(record_id, fields)
    return ApiResponse.ok(data=record, message="updated")


@router.delete("/warehouse-addresses/{record_id}")
async def delete_warehouse_address(record_id: str) -> JSONResponse:
    await service.delete_warehouse_address(record_id)
    return ApiResponse.ok(message="deleted")

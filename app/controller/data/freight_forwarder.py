from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.common.response import ApiResponse
from app.service.freight_forwarder import freight_forwarder_service as service

router = APIRouter()


@router.get("/freight-forwarders")
async def list_freight_forwarders(
    page_size: int = Query(default=100, le=500),
    page_token: str | None = Query(default=None),
    filter_expr: str | None = Query(default=None),
) -> JSONResponse:
    records, next_token = await service.list_freight_forwarders(
        page_size=page_size,
        page_token=page_token,
        filter_expr=filter_expr,
    )
    return ApiResponse.ok(data={"records": records, "next_page_token": next_token})


@router.get("/freight-forwarders/all")
async def list_all_freight_forwarders(
    filter_expr: str | None = Query(default=None),
) -> JSONResponse:
    records = await service.list_all_freight_forwarders(filter_expr=filter_expr)
    return ApiResponse.ok(data={"records": records, "total": len(records)})


@router.post("/freight-forwarders")
async def create_freight_forwarder(fields: dict[str, Any]) -> JSONResponse:
    record = await service.create_freight_forwarder(fields)
    return ApiResponse.ok(data=record, message="created")


@router.patch("/freight-forwarders/{record_id}")
async def update_freight_forwarder(record_id: str, fields: dict[str, Any]) -> JSONResponse:
    record = await service.update_freight_forwarder(record_id, fields)
    return ApiResponse.ok(data=record, message="updated")


@router.delete("/freight-forwarders/{record_id}")
async def delete_freight_forwarder(record_id: str) -> JSONResponse:
    await service.delete_freight_forwarder(record_id)
    return ApiResponse.ok(message="deleted")

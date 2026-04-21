from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.common.response import ApiResponse
from app.service.master.terminal import terminal_service as service

router = APIRouter()


@router.get("/terminals")
async def list_terminals(
    page_size: int = Query(default=100, le=500),
    page_token: str | None = Query(default=None),
    filter_expr: str | None = Query(default=None),
) -> JSONResponse:
    records, next_token = await service.list_terminals(
        page_size=page_size,
        page_token=page_token,
        filter_expr=filter_expr,
    )
    return ApiResponse.ok(data={"records": records, "next_page_token": next_token})


@router.get("/terminals/all")
async def list_all_terminals(
    filter_expr: str | None = Query(default=None),
) -> JSONResponse:
    records = await service.list_all_terminals(filter_expr=filter_expr)
    return ApiResponse.ok(data={"records": records, "total": len(records)})


@router.post("/terminals")
async def create_terminal(fields: dict[str, Any]) -> JSONResponse:
    record = await service.create_terminal(fields)
    return ApiResponse.ok(data=record, message="created")


@router.patch("/terminals/{record_id}")
async def update_terminal(record_id: str, fields: dict[str, Any]) -> JSONResponse:
    record = await service.update_terminal(record_id, fields)
    return ApiResponse.ok(data=record, message="updated")


@router.delete("/terminals/{record_id}")
async def delete_terminal(record_id: str) -> JSONResponse:
    await service.delete_terminal(record_id)
    return ApiResponse.ok(message="deleted")

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.common.response import ApiResponse
from app.service.master.consingee import consingee_service as service

router = APIRouter()


@router.get("/consingees")
async def list_consingees(
    page_size: int = Query(default=100, le=500),
    page_token: str | None = Query(default=None),
) -> JSONResponse:
    records, next_token = await service.list_consingees(
        page_size=page_size,
        page_token=page_token,
    )
    return ApiResponse.ok(data={"records": records, "next_page_token": next_token})


@router.get("/consingees/all")
async def list_all_consingees(
) -> JSONResponse:
    records = await service.list_all_consingees()
    return ApiResponse.ok(data={"records": records, "total": len(records)})


@router.get("/consingees/{record_id}")
async def get_consingee(record_id: str) -> JSONResponse:
    record = await service.get_consingee(record_id)
    return ApiResponse.ok(data=record)


@router.post("/consingees")
async def create_consingee(fields: dict[str, Any]) -> JSONResponse:
    record = await service.create_consingee(fields)
    return ApiResponse.ok(data=record, message="created")


@router.patch("/consingees/{record_id}")
async def update_consingee(record_id: str, fields: dict[str, Any]) -> JSONResponse:
    record = await service.update_consingee(record_id, fields)
    return ApiResponse.ok(data=record, message="updated")


@router.delete("/consingees/{record_id}")
async def delete_consingee(record_id: str) -> JSONResponse:
    await service.delete_consingee(record_id)
    return ApiResponse.ok(message="deleted")

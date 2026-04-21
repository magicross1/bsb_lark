from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.common.response import ApiResponse
from app.service.master.distance_matrix import distance_matrix_service as service

router = APIRouter()


@router.get("/distance-matrix")
async def list_distance_matrix(
    page_size: int = Query(default=100, le=500),
    page_token: str | None = Query(default=None),
) -> JSONResponse:
    records, next_token = await service.list_distance_matrix(
        page_size=page_size,
        page_token=page_token,
    )
    return ApiResponse.ok(data={"records": records, "next_page_token": next_token})


@router.get("/distance-matrix/all")
async def list_all_distance_matrix(
) -> JSONResponse:
    records = await service.list_all_distance_matrix()
    return ApiResponse.ok(data={"records": records, "total": len(records)})


@router.post("/distance-matrix")
async def create_distance_matrix(fields: dict[str, Any]) -> JSONResponse:
    record = await service.create_distance_matrix(fields)
    return ApiResponse.ok(data=record, message="created")


@router.patch("/distance-matrix/{record_id}")
async def update_distance_matrix(record_id: str, fields: dict[str, Any]) -> JSONResponse:
    record = await service.update_distance_matrix(record_id, fields)
    return ApiResponse.ok(data=record, message="updated")


@router.delete("/distance-matrix/{record_id}")
async def delete_distance_matrix(record_id: str) -> JSONResponse:
    await service.delete_distance_matrix(record_id)
    return ApiResponse.ok(message="deleted")

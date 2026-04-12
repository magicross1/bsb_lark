from typing import Any

from fastapi import APIRouter, Query

from app.core.response import ApiResponse
from app.modules.master_data.service import MasterDataService

router = APIRouter(prefix="/master-data", tags=["Master Data"])

_service = MasterDataService()


# ── Warehouse Address ───────────────────────────────────

@router.get("/warehouse-addresses")
async def list_warehouse_addresses(
    page_size: int = Query(default=100, le=500),
    page_token: str | None = Query(default=None),
    filter_expr: str | None = Query(default=None),
):
    records, next_token = await _service.list_warehouse_addresses(
        page_size=page_size, page_token=page_token, filter_expr=filter_expr,
    )
    return ApiResponse.ok(data={"records": records, "next_page_token": next_token})


@router.get("/warehouse-addresses/all")
async def list_all_warehouse_addresses(
    filter_expr: str | None = Query(default=None),
):
    records = await _service.list_all_warehouse_addresses(filter_expr=filter_expr)
    return ApiResponse.ok(data={"records": records, "total": len(records)})


@router.get("/warehouse-addresses/{record_id}")
async def get_warehouse_address(record_id: str):
    record = await _service.get_warehouse_address(record_id)
    return ApiResponse.ok(data=record)


@router.post("/warehouse-addresses")
async def create_warehouse_address(fields: dict[str, Any]):
    record = await _service.create_warehouse_address(fields)
    return ApiResponse.ok(data=record, message="created")


@router.patch("/warehouse-addresses/{record_id}")
async def update_warehouse_address(record_id: str, fields: dict[str, Any]):
    record = await _service.update_warehouse_address(record_id, fields)
    return ApiResponse.ok(data=record, message="updated")


@router.delete("/warehouse-addresses/{record_id}")
async def delete_warehouse_address(record_id: str):
    await _service.delete_warehouse_address(record_id)
    return ApiResponse.ok(message="deleted")


# ── Consingee ───────────────────────────────────────────

@router.get("/consingees")
async def list_consingees(
    page_size: int = Query(default=100, le=500),
    page_token: str | None = Query(default=None),
    filter_expr: str | None = Query(default=None),
):
    records, next_token = await _service.list_consingees(
        page_size=page_size, page_token=page_token, filter_expr=filter_expr,
    )
    return ApiResponse.ok(data={"records": records, "next_page_token": next_token})


@router.get("/consingees/all")
async def list_all_consingees(
    filter_expr: str | None = Query(default=None),
):
    records = await _service.list_all_consingees(filter_expr=filter_expr)
    return ApiResponse.ok(data={"records": records, "total": len(records)})


@router.get("/consingees/{record_id}")
async def get_consingee(record_id: str):
    record = await _service.get_consingee(record_id)
    return ApiResponse.ok(data=record)


@router.post("/consingees")
async def create_consingee(fields: dict[str, Any]):
    record = await _service.create_consingee(fields)
    return ApiResponse.ok(data=record, message="created")


@router.patch("/consingees/{record_id}")
async def update_consingee(record_id: str, fields: dict[str, Any]):
    record = await _service.update_consingee(record_id, fields)
    return ApiResponse.ok(data=record, message="updated")


@router.delete("/consingees/{record_id}")
async def delete_consingee(record_id: str):
    await _service.delete_consingee(record_id)
    return ApiResponse.ok(message="deleted")


# ── Suburb ──────────────────────────────────────────────

@router.get("/suburbs")
async def list_suburbs(
    page_size: int = Query(default=100, le=500),
    page_token: str | None = Query(default=None),
    filter_expr: str | None = Query(default=None),
):
    records, next_token = await _service.list_suburbs(
        page_size=page_size, page_token=page_token, filter_expr=filter_expr,
    )
    return ApiResponse.ok(data={"records": records, "next_page_token": next_token})


@router.get("/suburbs/all")
async def list_all_suburbs(
    filter_expr: str | None = Query(default=None),
):
    records = await _service.list_all_suburbs(filter_expr=filter_expr)
    return ApiResponse.ok(data={"records": records, "total": len(records)})


@router.get("/suburbs/{record_id}")
async def get_suburb(record_id: str):
    record = await _service.get_suburb(record_id)
    return ApiResponse.ok(data=record)


@router.post("/suburbs")
async def create_suburb(fields: dict[str, Any]):
    record = await _service.create_suburb(fields)
    return ApiResponse.ok(data=record, message="created")


@router.patch("/suburbs/{record_id}")
async def update_suburb(record_id: str, fields: dict[str, Any]):
    record = await _service.update_suburb(record_id, fields)
    return ApiResponse.ok(data=record, message="updated")


@router.delete("/suburbs/{record_id}")
async def delete_suburb(record_id: str):
    await _service.delete_suburb(record_id)
    return ApiResponse.ok(message="deleted")


# ── Driver ──────────────────────────────────────────────

@router.get("/drivers")
async def list_drivers(
    page_size: int = Query(default=100, le=500),
    page_token: str | None = Query(default=None),
    filter_expr: str | None = Query(default=None),
):
    records, next_token = await _service.list_drivers(
        page_size=page_size, page_token=page_token, filter_expr=filter_expr,
    )
    return ApiResponse.ok(data={"records": records, "next_page_token": next_token})


@router.get("/drivers/all")
async def list_all_drivers(
    filter_expr: str | None = Query(default=None),
):
    records = await _service.list_all_drivers(filter_expr=filter_expr)
    return ApiResponse.ok(data={"records": records, "total": len(records)})


@router.post("/drivers")
async def create_driver(fields: dict[str, Any]):
    record = await _service.create_driver(fields)
    return ApiResponse.ok(data=record, message="created")


@router.patch("/drivers/{record_id}")
async def update_driver(record_id: str, fields: dict[str, Any]):
    record = await _service.update_driver(record_id, fields)
    return ApiResponse.ok(data=record, message="updated")


@router.delete("/drivers/{record_id}")
async def delete_driver(record_id: str):
    await _service.delete_driver(record_id)
    return ApiResponse.ok(message="deleted")


# ── Vehicle ─────────────────────────────────────────────

@router.get("/vehicles")
async def list_vehicles(
    page_size: int = Query(default=100, le=500),
    page_token: str | None = Query(default=None),
    filter_expr: str | None = Query(default=None),
):
    records, next_token = await _service.list_vehicles(
        page_size=page_size, page_token=page_token, filter_expr=filter_expr,
    )
    return ApiResponse.ok(data={"records": records, "next_page_token": next_token})


@router.get("/vehicles/all")
async def list_all_vehicles(
    filter_expr: str | None = Query(default=None),
):
    records = await _service.list_all_vehicles(filter_expr=filter_expr)
    return ApiResponse.ok(data={"records": records, "total": len(records)})


@router.post("/vehicles")
async def create_vehicle(fields: dict[str, Any]):
    record = await _service.create_vehicle(fields)
    return ApiResponse.ok(data=record, message="created")


@router.patch("/vehicles/{record_id}")
async def update_vehicle(record_id: str, fields: dict[str, Any]):
    record = await _service.update_vehicle(record_id, fields)
    return ApiResponse.ok(data=record, message="updated")


@router.delete("/vehicles/{record_id}")
async def delete_vehicle(record_id: str):
    await _service.delete_vehicle(record_id)
    return ApiResponse.ok(message="deleted")


# ── Terminal ────────────────────────────────────────────

@router.get("/terminals")
async def list_terminals(
    page_size: int = Query(default=100, le=500),
    page_token: str | None = Query(default=None),
    filter_expr: str | None = Query(default=None),
):
    records, next_token = await _service.list_terminals(
        page_size=page_size, page_token=page_token, filter_expr=filter_expr,
    )
    return ApiResponse.ok(data={"records": records, "next_page_token": next_token})


@router.get("/terminals/all")
async def list_all_terminals(
    filter_expr: str | None = Query(default=None),
):
    records = await _service.list_all_terminals(filter_expr=filter_expr)
    return ApiResponse.ok(data={"records": records, "total": len(records)})


@router.post("/terminals")
async def create_terminal(fields: dict[str, Any]):
    record = await _service.create_terminal(fields)
    return ApiResponse.ok(data=record, message="created")


@router.patch("/terminals/{record_id}")
async def update_terminal(record_id: str, fields: dict[str, Any]):
    record = await _service.update_terminal(record_id, fields)
    return ApiResponse.ok(data=record, message="updated")


@router.delete("/terminals/{record_id}")
async def delete_terminal(record_id: str):
    await _service.delete_terminal(record_id)
    return ApiResponse.ok(message="deleted")


# ── Freight Forwarder ───────────────────────────────────

@router.get("/freight-forwarders")
async def list_freight_forwarders(
    page_size: int = Query(default=100, le=500),
    page_token: str | None = Query(default=None),
    filter_expr: str | None = Query(default=None),
):
    records, next_token = await _service.list_freight_forwarders(
        page_size=page_size, page_token=page_token, filter_expr=filter_expr,
    )
    return ApiResponse.ok(data={"records": records, "next_page_token": next_token})


@router.get("/freight-forwarders/all")
async def list_all_freight_forwarders(
    filter_expr: str | None = Query(default=None),
):
    records = await _service.list_all_freight_forwarders(filter_expr=filter_expr)
    return ApiResponse.ok(data={"records": records, "total": len(records)})


@router.post("/freight-forwarders")
async def create_freight_forwarder(fields: dict[str, Any]):
    record = await _service.create_freight_forwarder(fields)
    return ApiResponse.ok(data=record, message="created")


@router.patch("/freight-forwarders/{record_id}")
async def update_freight_forwarder(record_id: str, fields: dict[str, Any]):
    record = await _service.update_freight_forwarder(record_id, fields)
    return ApiResponse.ok(data=record, message="updated")


@router.delete("/freight-forwarders/{record_id}")
async def delete_freight_forwarder(record_id: str):
    await _service.delete_freight_forwarder(record_id)
    return ApiResponse.ok(message="deleted")


# ── Empty Park ──────────────────────────────────────────

@router.get("/empty-parks")
async def list_empty_parks(
    page_size: int = Query(default=100, le=500),
    page_token: str | None = Query(default=None),
    filter_expr: str | None = Query(default=None),
):
    records, next_token = await _service.list_empty_parks(
        page_size=page_size, page_token=page_token, filter_expr=filter_expr,
    )
    return ApiResponse.ok(data={"records": records, "next_page_token": next_token})


@router.get("/empty-parks/all")
async def list_all_empty_parks(
    filter_expr: str | None = Query(default=None),
):
    records = await _service.list_all_empty_parks(filter_expr=filter_expr)
    return ApiResponse.ok(data={"records": records, "total": len(records)})


@router.post("/empty-parks")
async def create_empty_park(fields: dict[str, Any]):
    record = await _service.create_empty_park(fields)
    return ApiResponse.ok(data=record, message="created")


@router.patch("/empty-parks/{record_id}")
async def update_empty_park(record_id: str, fields: dict[str, Any]):
    record = await _service.update_empty_park(record_id, fields)
    return ApiResponse.ok(data=record, message="updated")


@router.delete("/empty-parks/{record_id}")
async def delete_empty_park(record_id: str):
    await _service.delete_empty_park(record_id)
    return ApiResponse.ok(message="deleted")


# ── Distance Matrix ─────────────────────────────────────

@router.get("/distance-matrix")
async def list_distance_matrix(
    page_size: int = Query(default=100, le=500),
    page_token: str | None = Query(default=None),
    filter_expr: str | None = Query(default=None),
):
    records, next_token = await _service.list_distance_matrix(
        page_size=page_size, page_token=page_token, filter_expr=filter_expr,
    )
    return ApiResponse.ok(data={"records": records, "next_page_token": next_token})


@router.get("/distance-matrix/all")
async def list_all_distance_matrix(
    filter_expr: str | None = Query(default=None),
):
    records = await _service.list_all_distance_matrix(filter_expr=filter_expr)
    return ApiResponse.ok(data={"records": records, "total": len(records)})


@router.post("/distance-matrix")
async def create_distance_matrix(fields: dict[str, Any]):
    record = await _service.create_distance_matrix(fields)
    return ApiResponse.ok(data=record, message="created")


@router.patch("/distance-matrix/{record_id}")
async def update_distance_matrix(record_id: str, fields: dict[str, Any]):
    record = await _service.update_distance_matrix(record_id, fields)
    return ApiResponse.ok(data=record, message="updated")


@router.delete("/distance-matrix/{record_id}")
async def delete_distance_matrix(record_id: str):
    await _service.delete_distance_matrix(record_id)
    return ApiResponse.ok(message="deleted")

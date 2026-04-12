from typing import Any

from app.core.base_service import BaseService
from app.modules.master_data.repository import (
    ConsingeeRepository,
    DistanceMatrixRepository,
    DriverRepository,
    EmptyParkRepository,
    FreightForwarderRepository,
    SuburbRepository,
    TerminalRepository,
    VehicleRepository,
    WarehouseAddressRepository,
)


class MasterDataService(BaseService):
    def __init__(self) -> None:
        self.warehouse_address_repo = WarehouseAddressRepository()
        self.consingee_repo = ConsingeeRepository()
        self.suburb_repo = SuburbRepository()
        self.driver_repo = DriverRepository()
        self.vehicle_repo = VehicleRepository()
        self.terminal_repo = TerminalRepository()
        self.ff_repo = FreightForwarderRepository()
        self.empty_park_repo = EmptyParkRepository()
        self.distance_matrix_repo = DistanceMatrixRepository()
        super().__init__(self.warehouse_address_repo)

    async def list_warehouse_addresses(self, **kwargs: Any) -> tuple[list[dict[str, Any]], str | None]:
        return await self.warehouse_address_repo.list_records(**kwargs)

    async def list_all_warehouse_addresses(self, **kwargs: Any) -> list[dict[str, Any]]:
        return await self.warehouse_address_repo.list_all_records(**kwargs)

    async def get_warehouse_address(self, record_id: str) -> dict[str, Any]:
        return await self.warehouse_address_repo.get_record(record_id)

    async def create_warehouse_address(self, fields: dict[str, Any]) -> dict[str, Any]:
        return await self.warehouse_address_repo.create_record(fields)

    async def update_warehouse_address(self, record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        return await self.warehouse_address_repo.update_record(record_id, fields)

    async def delete_warehouse_address(self, record_id: str) -> None:
        await self.warehouse_address_repo.delete_record(record_id)

    async def list_consingees(self, **kwargs: Any) -> tuple[list[dict[str, Any]], str | None]:
        return await self.consingee_repo.list_records(**kwargs)

    async def list_all_consingees(self, **kwargs: Any) -> list[dict[str, Any]]:
        return await self.consingee_repo.list_all_records(**kwargs)

    async def get_consingee(self, record_id: str) -> dict[str, Any]:
        return await self.consingee_repo.get_record(record_id)

    async def create_consingee(self, fields: dict[str, Any]) -> dict[str, Any]:
        return await self.consingee_repo.create_record(fields)

    async def update_consingee(self, record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        return await self.consingee_repo.update_record(record_id, fields)

    async def delete_consingee(self, record_id: str) -> None:
        await self.consingee_repo.delete_record(record_id)

    async def list_suburbs(self, **kwargs: Any) -> tuple[list[dict[str, Any]], str | None]:
        return await self.suburb_repo.list_records(**kwargs)

    async def list_all_suburbs(self, **kwargs: Any) -> list[dict[str, Any]]:
        return await self.suburb_repo.list_all_records(**kwargs)

    async def get_suburb(self, record_id: str) -> dict[str, Any]:
        return await self.suburb_repo.get_record(record_id)

    async def create_suburb(self, fields: dict[str, Any]) -> dict[str, Any]:
        return await self.suburb_repo.create_record(fields)

    async def update_suburb(self, record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        return await self.suburb_repo.update_record(record_id, fields)

    async def delete_suburb(self, record_id: str) -> None:
        await self.suburb_repo.delete_record(record_id)

    async def list_drivers(self, **kwargs: Any) -> tuple[list[dict[str, Any]], str | None]:
        return await self.driver_repo.list_records(**kwargs)

    async def list_all_drivers(self, **kwargs: Any) -> list[dict[str, Any]]:
        return await self.driver_repo.list_all_records(**kwargs)

    async def create_driver(self, fields: dict[str, Any]) -> dict[str, Any]:
        return await self.driver_repo.create_record(fields)

    async def update_driver(self, record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        return await self.driver_repo.update_record(record_id, fields)

    async def delete_driver(self, record_id: str) -> None:
        await self.driver_repo.delete_record(record_id)

    async def list_vehicles(self, **kwargs: Any) -> tuple[list[dict[str, Any]], str | None]:
        return await self.vehicle_repo.list_records(**kwargs)

    async def list_all_vehicles(self, **kwargs: Any) -> list[dict[str, Any]]:
        return await self.vehicle_repo.list_all_records(**kwargs)

    async def create_vehicle(self, fields: dict[str, Any]) -> dict[str, Any]:
        return await self.vehicle_repo.create_record(fields)

    async def update_vehicle(self, record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        return await self.vehicle_repo.update_record(record_id, fields)

    async def delete_vehicle(self, record_id: str) -> None:
        await self.vehicle_repo.delete_record(record_id)

    async def list_terminals(self, **kwargs: Any) -> tuple[list[dict[str, Any]], str | None]:
        return await self.terminal_repo.list_records(**kwargs)

    async def list_all_terminals(self, **kwargs: Any) -> list[dict[str, Any]]:
        return await self.terminal_repo.list_all_records(**kwargs)

    async def create_terminal(self, fields: dict[str, Any]) -> dict[str, Any]:
        return await self.terminal_repo.create_record(fields)

    async def update_terminal(self, record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        return await self.terminal_repo.update_record(record_id, fields)

    async def delete_terminal(self, record_id: str) -> None:
        await self.terminal_repo.delete_record(record_id)

    async def list_freight_forwarders(self, **kwargs: Any) -> tuple[list[dict[str, Any]], str | None]:
        return await self.ff_repo.list_records(**kwargs)

    async def list_all_freight_forwarders(self, **kwargs: Any) -> list[dict[str, Any]]:
        return await self.ff_repo.list_all_records(**kwargs)

    async def create_freight_forwarder(self, fields: dict[str, Any]) -> dict[str, Any]:
        return await self.ff_repo.create_record(fields)

    async def update_freight_forwarder(self, record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        return await self.ff_repo.update_record(record_id, fields)

    async def delete_freight_forwarder(self, record_id: str) -> None:
        await self.ff_repo.delete_record(record_id)

    async def list_empty_parks(self, **kwargs: Any) -> tuple[list[dict[str, Any]], str | None]:
        return await self.empty_park_repo.list_records(**kwargs)

    async def list_all_empty_parks(self, **kwargs: Any) -> list[dict[str, Any]]:
        return await self.empty_park_repo.list_all_records(**kwargs)

    async def create_empty_park(self, fields: dict[str, Any]) -> dict[str, Any]:
        return await self.empty_park_repo.create_record(fields)

    async def update_empty_park(self, record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        return await self.empty_park_repo.update_record(record_id, fields)

    async def delete_empty_park(self, record_id: str) -> None:
        await self.empty_park_repo.delete_record(record_id)

    async def list_distance_matrix(self, **kwargs: Any) -> tuple[list[dict[str, Any]], str | None]:
        return await self.distance_matrix_repo.list_records(**kwargs)

    async def list_all_distance_matrix(self, **kwargs: Any) -> list[dict[str, Any]]:
        return await self.distance_matrix_repo.list_all_records(**kwargs)

    async def create_distance_matrix(self, fields: dict[str, Any]) -> dict[str, Any]:
        return await self.distance_matrix_repo.create_record(fields)

    async def update_distance_matrix(self, record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        return await self.distance_matrix_repo.update_record(record_id, fields)

    async def delete_distance_matrix(self, record_id: str) -> None:
        await self.distance_matrix_repo.delete_record(record_id)

from __future__ import annotations

from app.repository.cartage import CartageRepository
from app.repository.consingee import ConsingeeRepository
from app.repository.distance_matrix import DistanceMatrixRepository
from app.repository.driver import DriverRepository
from app.repository.empty_park import EmptyParkRepository
from app.repository.freight_forwarder import FreightForwarderRepository
from app.repository.suburb import SuburbRepository
from app.repository.terminal import TerminalRepository
from app.repository.vehicle import VehicleRepository
from app.repository.warehouse_address import WarehouseAddressRepository
from app.repository.warehouse_deliver_config import WarehouseDeliverConfigRepository

__all__ = [
    "CartageRepository",
    "ConsingeeRepository",
    "DistanceMatrixRepository",
    "DriverRepository",
    "EmptyParkRepository",
    "FreightForwarderRepository",
    "SuburbRepository",
    "TerminalRepository",
    "VehicleRepository",
    "WarehouseAddressRepository",
    "WarehouseDeliverConfigRepository",
]

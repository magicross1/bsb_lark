from app.core.base_repository import BaseRepository
from app.shared.lark_tables import T


class WarehouseAddressRepository(BaseRepository):
    table_id = T.md_warehouse_address.id


class ConsingeeRepository(BaseRepository):
    table_id = T.md_consingee.id


class SuburbRepository(BaseRepository):
    table_id = T.md_suburb.id


class DriverRepository(BaseRepository):
    table_id = T.md_driver.id


class VehicleRepository(BaseRepository):
    table_id = T.md_vehicle.id


class TerminalRepository(BaseRepository):
    table_id = T.md_terminal.id


class FreightForwarderRepository(BaseRepository):
    table_id = T.md_freight_forwarder.id


class EmptyParkRepository(BaseRepository):
    table_id = T.md_empty_park.id


class DistanceMatrixRepository(BaseRepository):
    table_id = T.md_distance_matrix.id

from pydantic import BaseModel


class WarehouseAddressOut(BaseModel):
    record_id: str
    address: str | None = None
    detail: str | None = None


class ConsingeeOut(BaseModel):
    record_id: str
    name: str | None = None
    contact: str | None = None
    phone: str | None = None
    email: str | None = None


class SuburbOut(BaseModel):
    record_id: str
    suburb: str | None = None
    state: str | None = None
    postcode: str | None = None
    rural_tailgate: str | None = None

from typing import Any
from pydantic import BaseModel, Field


class DeviceCreate(BaseModel):
    name: str = Field(max_length=255)
    protocol: str = Field(pattern=r"^(bacnet|modbus|mqtt)$")
    address: str
    port: int | None = None
    config_json: dict[str, Any] | None = None
    area: str | None = Field(default=None, max_length=100)
    auto_start: bool = False
    modbus_unit_id: int | None = Field(default=None, ge=1, le=247)
    modbus_transport: str | None = Field(default=None, pattern=r"^(tcp|rtu)$")
    modbus_baudrate: int | None = None


class DeviceUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    address: str | None = None
    port: int | None = None
    config_json: dict[str, Any] | None = None
    area: str | None = Field(default=None, max_length=100)
    auto_start: bool | None = None
    is_simulator: bool | None = None
    modbus_unit_id: int | None = Field(default=None, ge=1, le=247)
    modbus_transport: str | None = Field(default=None, pattern=r"^(tcp|rtu)$")
    modbus_baudrate: int | None = None


class DeviceResponse(BaseModel):
    id: int
    name: str
    protocol: str
    address: str
    port: int | None
    config_json: dict[str, Any] | None
    area: str | None
    status: str
    is_simulator: bool
    auto_start: bool
    modbus_unit_id: int | None = None
    modbus_transport: str | None = None
    modbus_baudrate: int | None = None

    model_config = {"from_attributes": True}


class DeviceScanResult(BaseModel):
    discovered: list[DeviceResponse]
    scan_duration_ms: int

"""
Adaptador Modbus — TCP y RTU via pymodbus 3.x.

Una instancia por dispositivo. Soporta:
- coil (FC01/FC05)
- discrete_input (FC02)
- holding_register (FC03/FC06)
- input_register (FC04)

Data types sobre holding/input: bool, uint16, int16, float32 (IEEE 754, 2 registros).
"""
import struct
from typing import TYPE_CHECKING

from core.logger import get_logger

if TYPE_CHECKING:
    from models.devices import Device
    from models.points import Point

logger = get_logger(__name__)


class ModbusAdapter:
    """Adaptador Modbus — una instancia por dispositivo."""

    def __init__(self, device: "Device") -> None:
        self._device = device
        self._client = None

    @classmethod
    def from_device(cls, device: "Device") -> "ModbusAdapter":
        return cls(device)

    def connect(self) -> bool:
        transport = (self._device.modbus_transport or "tcp").lower()
        try:
            if transport == "tcp":
                from pymodbus.client import ModbusTcpClient
                address = self._device.address or "127.0.0.1:502"
                if ":" in address:
                    host, port_str = address.rsplit(":", 1)
                    port = int(port_str)
                else:
                    host, port = address, 502
                self._client = ModbusTcpClient(host=host, port=port)
            else:
                from pymodbus.client import ModbusSerialClient
                baudrate = self._device.modbus_baudrate or 9600
                self._client = ModbusSerialClient(
                    port=self._device.address or "/dev/ttyUSB0",
                    baudrate=baudrate,
                    bytesize=8,
                    parity="N",
                    stopbits=1,
                )
            connected = self._client.connect()
            if not connected:
                logger.warning(
                    "Modbus connect falló",
                    extra={"device_id": self._device.id, "transport": transport},
                )
            return bool(connected)
        except Exception as exc:
            logger.error(
                "Modbus connect error",
                extra={"device_id": self._device.id, "error": str(exc)},
            )
            return False

    def disconnect(self) -> None:
        try:
            if self._client:
                self._client.close()
        except Exception:
            pass
        finally:
            self._client = None

    def read_point(self, point: "Point") -> "float | bool | None":
        if not self._client:
            return None
        unit_id = self._device.modbus_unit_id or 1
        register_type = (point.modbus_register_type or "holding_register").lower()
        data_type = (point.modbus_data_type or "uint16").lower()
        try:
            address = int(point.address)
        except (TypeError, ValueError):
            logger.error("Dirección Modbus inválida", extra={"point_id": point.id, "address": point.address})
            return None

        try:
            if register_type == "coil":
                rr = self._client.read_coils(address, count=1, slave=unit_id)
                if rr.isError():
                    return None
                return bool(rr.bits[0])

            if register_type == "discrete_input":
                rr = self._client.read_discrete_inputs(address, count=1, slave=unit_id)
                if rr.isError():
                    return None
                return bool(rr.bits[0])

            count = 2 if data_type == "float32" else 1
            if register_type == "holding_register":
                rr = self._client.read_holding_registers(address, count=count, slave=unit_id)
            else:
                rr = self._client.read_input_registers(address, count=count, slave=unit_id)

            if rr.isError():
                return None

            return self._decode_registers(rr.registers, data_type)

        except Exception as exc:
            logger.error(
                "Modbus read_point error",
                extra={"point_id": point.id, "error": str(exc)},
            )
            return None

    def write_point(self, point: "Point", value: "float | bool") -> bool:
        if not self._client:
            return False
        unit_id = self._device.modbus_unit_id or 1
        register_type = (point.modbus_register_type or "holding_register").lower()
        data_type = (point.modbus_data_type or "uint16").lower()

        if register_type in ("discrete_input", "input_register"):
            raise ValueError(f"Register type '{register_type}' es solo lectura")

        try:
            address = int(point.address)
        except (TypeError, ValueError):
            return False

        try:
            if register_type == "coil":
                rr = self._client.write_coil(address, bool(value), slave=unit_id)
                return not rr.isError()

            if data_type == "float32":
                packed = struct.pack(">f", float(value))
                w1, w2 = struct.unpack(">HH", packed)
                rr = self._client.write_registers(address, [w1, w2], slave=unit_id)
            else:
                int_value = int(value)
                if data_type == "int16" and int_value < 0:
                    int_value = int_value & 0xFFFF
                rr = self._client.write_register(address, int_value & 0xFFFF, slave=unit_id)

            return not rr.isError()

        except Exception as exc:
            logger.error(
                "Modbus write_point error",
                extra={"point_id": point.id, "error": str(exc)},
            )
            return False

    @staticmethod
    def _decode_registers(registers: list[int], data_type: str) -> float:
        if data_type == "float32" and len(registers) >= 2:
            packed = struct.pack(">HH", registers[0], registers[1])
            return float(struct.unpack(">f", packed)[0])
        if data_type == "int16":
            val = registers[0]
            return float(val if val < 0x8000 else val - 0x10000)
        return float(registers[0])

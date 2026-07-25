"""
Simulador Modbus TCP — servidor usando pymodbus.

Levanta un servidor Modbus TCP en el puerto configurado y expone
registros holding con valores simulados (temperatura, presión, estado).
Se registra en la BD con is_simulator=True y protocol="modbus".
"""
import asyncio
import random
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


async def run_modbus_simulator(device_id: int, config: dict[str, Any]) -> None:
    """
    Arranca el servidor Modbus TCP simulado.

    config esperada:
    {
        "port": 5020,
        "registers": [
            {"address": 0, "name": "temp_supply", "value_range": [180, 260]},
            {"address": 1, "name": "pressure",    "value_range": [0, 1000]},
            {"address": 2, "name": "fan_status",  "value_range": [0, 1]}
        ]
    }
    """
    from pymodbus.datastore import (
        ModbusSequentialDataBlock,
        ModbusServerContext,
        ModbusSlaveContext,
    )
    from pymodbus.server import StartAsyncTcpServer

    port = config.get("port", 5020)
    registers_cfg = config.get("registers", [
        {"address": 0, "name": "temp_supply", "value_range": [180, 260]},
        {"address": 1, "name": "pressure",    "value_range": [0, 1000]},
        {"address": 2, "name": "fan_status",  "value_range": [0, 1]},
    ])

    # Inicializar registros con valores aleatorios
    initial_values = [0] * 100
    for reg in registers_cfg:
        addr = reg["address"]
        lo, hi = reg["value_range"]
        if addr < 100:
            initial_values[addr] = int(random.uniform(lo, hi))

    store = ModbusSlaveContext(
        hr=ModbusSequentialDataBlock(0, initial_values),
    )
    context = ModbusServerContext(slaves=store, single=True)

    logger.info("Iniciando simulador Modbus TCP",
                extra={"device_id": device_id, "port": port})

    async def _update_values():
        while True:
            await asyncio.sleep(5)
            for reg in registers_cfg:
                addr = reg["address"]
                lo, hi = reg["value_range"]
                context[0].setValues(3, addr, [int(random.uniform(lo, hi))])

    asyncio.create_task(_update_values())

    await StartAsyncTcpServer(
        context=context,
        address=("0.0.0.0", port),
    )

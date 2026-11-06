from __future__ import annotations

import asyncio
from array import array
import threading

from PySide6.QtCore import QThread, Signal
from pymodbus.datastore import ModbusServerContext
from pymodbus.server import ModbusTcpServer


class MutableModbusContext(ModbusServerContext):
    """A small mutable datastore for the PyModbus 3.x server interface."""

    def __init__(self, unit_id: int) -> None:
        # PyModbus 3.13 routes a context with a non-empty ``simdevices`` list
        # through its immutable simulator model. Keep it empty so its documented
        # async context interface below serves the live editable banks.
        self.simdevices = []
        self._unit_id = unit_id
        self._lock = threading.RLock()
        self._banks: dict[int, bytearray | array] = {
            1: bytearray(65536),
            2: bytearray(65536),
            3: array("H", [0]) * 65536,
            4: array("H", [0]) * 65536,
        }
        self._banks[3][:16] = array("H", [0, 123, 250, 1000, 0, 1, 42, 65535, 12, 34, 56, 78, 90, 120, 300, 600])
        self._banks[4][:16] = array("H", [220, 231, 228, 240, 235, 233, 229, 222, 218, 225, 237, 241, 232, 226, 219, 230])
        self._banks[1][:16] = bytes([True, False, True, True, False, False, True, False, True, False, False, True, False, True, True, False])
        self._banks[2][:16] = bytes([False, True, False, False, True, True, False, True, False, True, True, False, True, False, False, True])

    def device_ids(self) -> list[int]:
        return [self._unit_id]

    @staticmethod
    def _bank_for_function(function: int) -> int:
        if function in (1, 5, 15):
            return 1
        if function == 2:
            return 2
        if function in (3, 6, 16, 22, 23):
            return 3
        if function == 4:
            return 4
        raise ValueError(f"不支持功能码 FC{function:02d}")

    async def async_getValues(self, device_id: int, func_code: int, address: int, count: int = 1):
        if device_id not in (self._unit_id, 0):
            raise ValueError(f"未知 Unit ID：{device_id}")
        bank = self._bank_for_function(func_code)
        if address < 0 or count < 1 or address + count > 65536:
            raise ValueError("请求地址超出模拟数据区范围。")
        with self._lock:
            return list(self._banks[bank][address : address + count])

    async def async_setValues(self, device_id: int, func_code: int, address: int, values: list[int | bool]):
        if device_id not in (self._unit_id, 0):
            raise ValueError(f"未知 Unit ID：{device_id}")
        bank = self._bank_for_function(func_code)
        if address < 0 or address + len(values) > 65536:
            raise ValueError("写入地址超出模拟数据区范围。")
        with self._lock:
            if bank in (1, 2):
                self._banks[bank][address : address + len(values)] = bytes(bool(value) for value in values)
            else:
                numeric_values = [int(value) for value in values]
                if any(not 0 <= value <= 0xFFFF for value in numeric_values):
                    raise ValueError("保持寄存器值必须在 0–65535 范围内。")
                self._banks[bank][address : address + len(values)] = array("H", numeric_values)
        return None

    def set_local_values(self, function: int, address: int, values: list[int | bool]) -> None:
        bank = self._bank_for_function(function)
        if address < 0 or address + len(values) > 65536:
            raise ValueError("地址超出模拟数据区范围。")
        with self._lock:
            if bank in (1, 2):
                self._banks[bank][address : address + len(values)] = bytes(bool(value) for value in values)
            else:
                numeric_values = [int(value) for value in values]
                if any(not 0 <= value <= 0xFFFF for value in numeric_values):
                    raise ValueError("保持寄存器值必须在 0–65535 范围内。")
                self._banks[bank][address : address + len(values)] = array("H", numeric_values)

    def get_local_values(self, function: int, address: int, count: int) -> list[int | bool]:
        bank = self._bank_for_function(function)
        if address < 0 or count < 1 or address + count > 65536:
            raise ValueError("地址超出模拟数据区范围。")
        with self._lock:
            return list(self._banks[bank][address : address + count])


class TcpSimulatorThread(QThread):
    started_server = Signal(str)
    stopped_server = Signal()
    failed = Signal(str)

    def __init__(
        self,
        host: str,
        port: int,
        unit_id: int,
        context: MutableModbusContext | None = None,
    ) -> None:
        super().__init__()
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self._stop_requested = threading.Event()
        self.context = context or MutableModbusContext(unit_id)

    def run(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def serve() -> None:
            server = ModbusTcpServer(self.context, address=(self.host, self.port))
            await server.serve_forever(background=True)
            self.started_server.emit(f"从站 ID {self.unit_id} 正在监听 {self.host}:{self.port}")
            while not self._stop_requested.is_set():
                await asyncio.sleep(0.1)
            await server.shutdown()

        try:
            loop.run_until_complete(serve())
        except Exception as exc:
            if not self._stop_requested.is_set():
                self.failed.emit(str(exc))
        finally:
            loop.close()
            self.stopped_server.emit()

    def request_stop(self) -> None:
        self._stop_requested.set()

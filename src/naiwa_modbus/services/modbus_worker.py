from __future__ import annotations

from datetime import datetime
from time import perf_counter
from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal, Slot
from pymodbus.client import ModbusSerialClient, ModbusTcpClient


class ModbusWorker(QObject):
    """Owns one synchronous PyModbus client in a dedicated Qt thread."""

    connected = Signal(bool, str)
    data_received = Signal(dict)
    log_message = Signal(str, str)
    operation_finished = Signal(bool, str)
    closed = Signal()

    connect_requested = Signal(dict)
    disconnect_requested = Signal()
    read_once_requested = Signal(dict)
    start_poll_requested = Signal(dict, int)
    stop_poll_requested = Signal()
    write_requested = Signal(dict, int, int, object)
    shutdown_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._client: Any | None = None
        self._settings: dict[str, Any] | None = None
        self._timer: QTimer | None = None

        self.connect_requested.connect(self._connect)
        self.disconnect_requested.connect(self._disconnect)
        self.read_once_requested.connect(self._read_once)
        self.start_poll_requested.connect(self._start_polling)
        self.stop_poll_requested.connect(self._stop_polling)
        self.write_requested.connect(self._write)
        self.shutdown_requested.connect(self.shutdown)

    @Slot()
    def initialize(self) -> None:
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._perform_read)

    @Slot(dict)
    def _connect(self, settings: dict[str, Any]) -> None:
        self._close_client()
        self._settings = settings
        try:
            timeout = float(settings.get("timeout", 1.2))
            if settings["protocol"] == "Modbus TCP":
                self._client = ModbusTcpClient(
                    settings["host"],
                    port=settings["port"],
                    timeout=timeout,
                    retries=0,
                )
            else:
                self._client = ModbusSerialClient(
                    settings["port_name"],
                    baudrate=settings["baudrate"],
                    bytesize=8,
                    parity=settings["parity"],
                    stopbits=settings["stopbits"],
                    timeout=timeout,
                    retries=0,
                )
            if not self._client.connect():
                raise ConnectionError("连接失败，请确认端口、网络和设备状态。")
            self.connected.emit(True, "已连接")
            self.log_message.emit("OK", self._connection_summary(settings))
        except Exception as exc:  # PyModbus and operating-system connection errors.
            self._close_client()
            self.connected.emit(False, str(exc))
            self.log_message.emit("ERR", f"连接失败：{exc}")

    @staticmethod
    def _connection_summary(settings: dict[str, Any]) -> str:
        if settings["protocol"] == "Modbus TCP":
            return f"已连接 TCP {settings['host']}:{settings['port']} · 站号 {settings['unit_id']}"
        return f"已连接 RTU {settings['port_name']} · {settings['baudrate']} {settings['parity']} · 站号 {settings['unit_id']}"

    @Slot(dict)
    def _read_once(self, settings: dict[str, Any]) -> None:
        self._settings = settings
        if self._client is None:
            self._connect(settings)
        if self._client is not None:
            self._perform_read()

    @Slot(dict, int)
    def _start_polling(self, settings: dict[str, Any], interval_ms: int) -> None:
        self._settings = settings
        if self._client is None:
            self._connect(settings)
        if self._client is None or self._timer is None:
            return
        self._timer.start(max(100, interval_ms))
        self.log_message.emit("INFO", f"开始轮询 · 间隔 {max(100, interval_ms)} ms")
        self._perform_read()

    @Slot()
    def _stop_polling(self) -> None:
        if self._timer is not None:
            self._timer.stop()
        self.log_message.emit("INFO", "已停止轮询")

    @Slot()
    def _disconnect(self) -> None:
        self._stop_polling()
        self._close_client()
        self.connected.emit(False, "未连接")

    @Slot()
    def _perform_read(self) -> None:
        settings = self._settings
        client = self._client
        if settings is None or client is None:
            return
        function = int(settings["function"])
        address = int(settings["address"])
        count = int(settings["count"])
        unit_id = int(settings["unit_id"])
        methods = {
            1: client.read_coils,
            2: client.read_discrete_inputs,
            3: client.read_holding_registers,
            4: client.read_input_registers,
        }
        function_name = {1: "01 线圈", 2: "02 离散输入", 3: "03 保持寄存器", 4: "04 输入寄存器"}[function]
        self.log_message.emit("TX", f"FC{function:02d} · 地址 {address} · 数量 {count} · Unit {unit_id}")
        started = perf_counter()
        try:
            response = methods[function](address, count=count, device_id=unit_id)
            elapsed_ms = (perf_counter() - started) * 1000
            if response.isError():
                raise RuntimeError(str(response))
            values = list(response.bits[:count] if function in (1, 2) else response.registers[:count])
            stamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            self.data_received.emit({
                "address": address,
                "count": count,
                "function": function,
                "function_name": function_name,
                "latency_ms": elapsed_ms,
                "timestamp": stamp,
                "unit_id": unit_id,
                "values": values,
            })
            preview = ", ".join(str(value) for value in values[:8])
            if len(values) > 8:
                preview += ", …"
            self.log_message.emit("RX", f"{function_name} · {len(values)} 项 · {elapsed_ms:.1f} ms · {preview}")
        except Exception as exc:
            self.log_message.emit("ERR", f"读取失败：{exc}")
            self.operation_finished.emit(False, str(exc))

    @Slot(dict, int, int, object)
    def _write(self, settings: dict[str, Any], function: int, address: int, value: object) -> None:
        if self._client is None:
            self._connect(settings)
        if self._client is None:
            return
        try:
            if function == 5:
                result = self._client.write_coil(address, bool(value), device_id=int(settings["unit_id"]))
                shown_value = "ON" if value else "OFF"
            else:
                result = self._client.write_register(address, int(value), device_id=int(settings["unit_id"]))
                shown_value = str(value)
            if result.isError():
                raise RuntimeError(str(result))
            message = f"写入成功 · FC{function:02d} · 地址 {address} · 值 {shown_value}"
            self.log_message.emit("WRITE", message)
            self.operation_finished.emit(True, message)
        except Exception as exc:
            message = f"写入失败：{exc}"
            self.log_message.emit("ERR", message)
            self.operation_finished.emit(False, message)

    def _close_client(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
        self._client = None

    @Slot()
    def shutdown(self) -> None:
        self._disconnect()
        self.closed.emit()

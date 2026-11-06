from __future__ import annotations

import csv
import json
import struct
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QThread, QSettings, QTimer
from PySide6.QtGui import QAction, QColor, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDockWidget,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QMdiArea,
    QMdiSubWindow,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from naiwa_modbus.services.audio import LaughPlayer
from naiwa_modbus.services.modbus_worker import ModbusWorker
from naiwa_modbus.services.simulator import TcpSimulatorThread
from naiwa_modbus.ui.mascot import MascotWidget


def card(title: str | None = None) -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(10)
    if title:
        heading = QLabel(title)
        heading.setObjectName("sectionTitle")
        layout.addWidget(heading)
    return frame, layout


def form_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("muted")
    return label


def parse_integer(text: str) -> int:
    value = text.strip().lower()
    if value.startswith(("0x", "+0x", "-0x")):
        sign = -1 if value.startswith("-") else 1
        digits = value[3:] if value[0] in "+-" else value[2:]
        return sign * int(digits, 16)
    return int(value, 10)


class WheelGuardComboBox(QComboBox):
    """Keep wheel scrolling in a dock from changing a setting by accident."""

    def wheelEvent(self, event) -> None:  # noqa: N802 - Qt event naming.
        event.ignore()


class WheelGuardSpinBox(QSpinBox):
    """Let the parent scroll area consume wheel events over numeric fields."""

    def wheelEvent(self, event) -> None:  # noqa: N802 - Qt event naming.
        event.ignore()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("奶蛙 Modbus · 主站 / 从站工作台")
        self.resize(1460, 900)
        self.setMinimumSize(1100, 720)
        self.settings = QSettings("BUWANNAB", "NaiWaModbus")
        self.audio = LaughPlayer()
        self.audio.enabled = self.settings.value("sound_enabled", True, type=bool)
        self.audio.custom_path = self.settings.value("custom_audio", "", type=str) or None
        self._data_log_path = self.settings.value("data_log_path", "", type=str) or ""
        self._data_log_enabled = bool(
            self._data_log_path and self.settings.value("data_log_enabled", False, type=bool)
        )
        self._records: list[tuple[str, str, str]] = []
        self._connected = False
        self._connecting = False
        self._polling = False
        self._auto_poll_after_connect = False
        self._latest_values: list[int | bool] = []
        self._latest_address = 0
        self._latest_function = 3
        self._latencies: list[float] = []
        self._tx_count = 0
        self._rx_count = 0
        self._error_count = 0
        self._simulator: TcpSimulatorThread | None = None
        self._sim_values: dict[int, list[int | bool]] = {
            1: [True, False, True, True, False, False, True, False, True, False, False, True, False, True, True, False],
            2: [False, True, False, False, True, True, False, True, False, True, True, False, True, False, False, True],
            3: [0, 123, 250, 1000, 0, 1, 42, 65535, 12, 34, 56, 78, 90, 120, 300, 600],
            4: [220, 231, 228, 240, 235, 233, 229, 222, 218, 225, 237, 241, 232, 226, 219, 230],
        }

        self._make_worker()
        self._build_ui()
        self._refresh_serial_ports()
        self._update_protocol_fields()
        self._update_write_controls()
        self._append_log("READY", "奶蛙准备好了 · 连接设备或启动本机从站模拟")

    def _make_worker(self) -> None:
        self.worker_thread = QThread(self)
        self.worker = ModbusWorker()
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.initialize)
        self.worker.connected.connect(self._on_connection_changed)
        self.worker.data_received.connect(self._on_data_received)
        self.worker.log_message.connect(self._append_log)
        self.worker.operation_finished.connect(self._on_operation_finished)
        self.worker.closed.connect(
            self.worker_thread.quit,
            Qt.ConnectionType.DirectConnection,
        )
        self.worker_thread.start()

    def _build_ui(self) -> None:
        self.setDockNestingEnabled(True)
        self.mdi_area = QMdiArea()
        self.mdi_area.setViewMode(QMdiArea.ViewMode.SubWindowView)
        self.mdi_area.setOption(QMdiArea.AreaOption.DontMaximizeSubWindowOnActivation, False)
        self.mdi_area.setBackground(QColor("#D7D3CB"))
        self.setCentralWidget(self.mdi_area)

        master_controls = self._build_master_page()
        self.control_dock = QDockWidget("连接与轮询", self)
        self.control_dock.setObjectName("controlDock")
        self.control_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.control_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self.control_dock.setMinimumWidth(300)
        self.control_dock.setMaximumWidth(410)
        self.control_dock.setWidget(master_controls)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.control_dock)

        self.master_subwindow = self.mdi_area.addSubWindow(self.master_data_widget)
        self.master_subwindow.setObjectName("masterDataWindow")
        self.master_subwindow.setWindowTitle("Mbpoll1 · 主站数据监视")
        self.master_subwindow.setMinimumSize(640, 420)
        self.master_subwindow.resize(980, 640)

        self.slave_subwindow = self.mdi_area.addSubWindow(self._build_slave_page())
        self.slave_subwindow.setObjectName("slaveDataWindow")
        self.slave_subwindow.setWindowTitle("Modbus Slave · 从站模拟")
        self.slave_subwindow.setMinimumSize(640, 420)
        self.slave_subwindow.resize(980, 640)
        self.slave_subwindow.hide()
        self.master_subwindow.show()

        self.master_mode_button = QPushButton("主站")
        self.master_mode_button.setObjectName("modeButtonActive")
        self.slave_mode_button = QPushButton("从站")
        self.mode_hint = QLabel("主站 · 读取真实设备并自动轮询")
        self.mode_hint.setObjectName("muted")
        self.master_mode_button.clicked.connect(lambda: self._switch_mode(0))
        self.slave_mode_button.clicked.connect(lambda: self._switch_mode(1))
        self._build_actions()
        self.statusBar().showMessage("就绪 · 地址使用 0 起始协议地址")
        self.protocol_status_label = QLabel()
        self.protocol_status_label.setObjectName("protocolStatus")
        self.statusBar().addPermanentWidget(self.protocol_status_label)
        self.function_combo.currentIndexChanged.connect(self._refresh_status_line)
        self.interval_input.valueChanged.connect(self._refresh_status_line)
        self.unit_id_input.valueChanged.connect(self._refresh_status_line)
        self._refresh_status_line()
        QTimer.singleShot(0, lambda: self._fit_subwindow(self.master_subwindow))

    def _build_actions(self) -> None:
        file_menu = self.menuBar().addMenu("文件(&F)")
        edit_menu = self.menuBar().addMenu("编辑(&E)")
        connection_menu = self.menuBar().addMenu("连接(&C)")
        setup_menu = self.menuBar().addMenu("设置(&S)")
        functions_menu = self.menuBar().addMenu("功能(&U)")
        display_menu = self.menuBar().addMenu("显示(&D)")
        window_menu = self.menuBar().addMenu("窗口(&W)")
        help_menu = self.menuBar().addMenu("帮助(&H)")

        self.action_new = QAction("主站数据窗", self)
        self.action_new.triggered.connect(lambda: self._switch_mode(0))
        self.action_open_workspace = QAction("打开工作区…", self)
        self.action_open_workspace.setShortcut(QKeySequence.StandardKey.Open)
        self.action_open_workspace.triggered.connect(self._open_workspace)
        self.action_save_workspace = QAction("保存工作区…", self)
        self.action_save_workspace.setShortcut(QKeySequence.StandardKey.Save)
        self.action_save_workspace.triggered.connect(self._save_workspace)
        self.action_export = QAction("导出通信日志 CSV…", self)
        self.action_export.triggered.connect(self._export_log)
        self.action_exit = QAction("退出", self)
        self.action_exit.setShortcut(QKeySequence.StandardKey.Quit)
        self.action_exit.triggered.connect(self.close)
        file_menu.addAction(self.action_new)
        file_menu.addSeparator()
        file_menu.addAction(self.action_open_workspace)
        file_menu.addAction(self.action_save_workspace)
        file_menu.addSeparator()
        file_menu.addAction(self.action_export)
        file_menu.addSeparator()
        file_menu.addAction(self.action_exit)

        self.action_copy_data = QAction("复制所选数据", self)
        self.action_copy_data.setShortcut(QKeySequence.StandardKey.Copy)
        self.action_copy_data.triggered.connect(self._copy_selected_data)
        self.action_clear_log = QAction("清空通信记录", self)
        self.action_clear_log.triggered.connect(self._clear_log)
        edit_menu.addAction(self.action_copy_data)
        edit_menu.addAction(self.action_clear_log)

        self.action_read = QAction("单次读取", self)
        self.action_read.setShortcut("F5")
        self.action_read.triggered.connect(self._read_once)
        self.action_poll = QAction("开始轮询", self)
        self.action_poll.setShortcut("F6")
        self.action_poll.triggered.connect(self._toggle_polling)
        self.action_connect = QAction("连接并自动轮询", self)
        self.action_connect.setShortcut("F3")
        self.action_connect.triggered.connect(self._toggle_connection)
        self.action_disconnect = QAction("断开连接", self)
        self.action_disconnect.triggered.connect(self._toggle_connection)
        self.action_disconnect.setEnabled(False)
        connection_menu.addAction(self.action_connect)
        connection_menu.addAction(self.action_disconnect)
        connection_menu.addSeparator()
        connection_menu.addAction(self.action_read)
        connection_menu.addAction(self.action_poll)

        self.action_write = QAction("手动写入…", self)
        self.action_write.triggered.connect(self._focus_write_controls)
        self.action_sim_start = QAction("启动/停止从站", self)
        self.action_sim_start.triggered.connect(self._toggle_server)
        setup_menu.addAction(self.action_write)
        setup_menu.addAction(self.action_sim_start)

        self.action_master = QAction("主站轮询", self)
        self.action_master.setShortcut("Ctrl+1")
        self.action_master.triggered.connect(lambda: self._switch_mode(0))
        self.action_slave = QAction("从站模拟", self)
        self.action_slave.setShortcut("Ctrl+2")
        self.action_slave.triggered.connect(lambda: self._switch_mode(1))
        functions_menu.addAction(self.action_master)
        functions_menu.addAction(self.action_slave)
        self.action_refresh_ports = QAction("刷新串口列表", self)
        self.action_refresh_ports.triggered.connect(self._refresh_serial_ports)
        functions_menu.addAction(self.action_refresh_ports)

        self.action_controls = self.control_dock.toggleViewAction()
        self.action_controls.setText("显示连接与轮询面板")
        display_menu.addAction(self.action_controls)
        self.action_cascade = QAction("层叠排列", self)
        self.action_cascade.triggered.connect(self.mdi_area.cascadeSubWindows)
        self.action_tile = QAction("平铺排列", self)
        self.action_tile.triggered.connect(self.mdi_area.tileSubWindows)
        self.action_master_window = QAction("主站数据窗", self)
        self.action_master_window.triggered.connect(lambda: self._switch_mode(0))
        self.action_slave_window = QAction("从站模拟窗", self)
        self.action_slave_window.triggered.connect(lambda: self._switch_mode(1))
        window_menu.addAction(self.action_master_window)
        window_menu.addAction(self.action_slave_window)
        window_menu.addSeparator()
        window_menu.addAction(self.action_cascade)
        window_menu.addAction(self.action_tile)
        about = QAction("关于奶蛙 Modbus", self)
        about.triggered.connect(lambda: QMessageBox.about(self, "关于", "奶蛙 Modbus 工作台\nModbus 主站轮询与 TCP 从站模拟"))
        help_menu.addAction(about)

        toolbar = QToolBar("常用操作", self)
        toolbar.setObjectName("mainToolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        toolbar.addAction(self.action_connect)
        toolbar.addAction(self.action_disconnect)
        toolbar.addSeparator()
        toolbar.addAction(self.action_read)
        toolbar.addAction(self.action_poll)
        toolbar.addSeparator()
        toolbar.addWidget(self.master_mode_button)
        toolbar.addWidget(self.slave_mode_button)
        toolbar.addWidget(self.mode_hint)
        toolbar.addSeparator()
        toolbar.addAction(self.action_controls)

    def _focus_write_controls(self) -> None:
        self._switch_mode(0)
        self.control_dock.show()
        self.write_value.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def _fit_subwindow(self, subwindow: QMdiSubWindow) -> None:
        area = self.mdi_area.viewport().rect().adjusted(6, 6, -6, -6)
        width = max(subwindow.minimumWidth(), area.width())
        height = max(subwindow.minimumHeight(), area.height())
        subwindow.setGeometry(area.x(), area.y(), width, height)
        subwindow.showNormal()
        if subwindow is self.master_subwindow:
            self._master_fitted = True
        elif subwindow is self.slave_subwindow:
            self._slave_fitted = True

    def _workspace_values(self) -> dict[str, Any]:
        return {
            "version": 1,
            "master": {
                "protocol": self.protocol_combo.currentText(),
                "host": self.host_input.text(),
                "tcp_port": self.tcp_port_input.value(),
                "serial_port": self.com_combo.currentText(),
                "baudrate": self.baud_combo.currentText(),
                "parity": self.parity_combo.currentText(),
                "stopbits": self.stopbits_combo.currentText(),
                "unit_id": self.unit_id_input.value(),
                "function": int(self.function_combo.currentData()),
                "address_base": int(self.address_base_combo.currentData()),
                "address": self.address_input.value(),
                "count": self.count_input.value(),
                "interval_ms": self.interval_input.value(),
                "timeout_ms": self.timeout_input.value(),
                "retries": self.retries_input.value(),
                "value_type": self.value_type_combo.currentData(),
                "word_order": self.word_order_combo.currentData(),
            },
            "slave": {
                "host": self.listen_host.text(),
                "port": self.listen_port.value(),
                "unit_id": self.listen_unit.value(),
            },
        }

    def _save_workspace(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "保存工作区", "naiwa_workspace.json", "奶蛙工作区 (*.json)")
        if not path:
            return
        if not path.lower().endswith(".json"):
            path += ".json"
        try:
            Path(path).write_text(
                json.dumps(self._workspace_values(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except (OSError, TypeError, ValueError) as exc:
            QMessageBox.warning(self, "保存工作区失败", str(exc))
            return
        self.statusBar().showMessage(f"工作区已保存：{path}", 5000)

    def _open_workspace(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "打开工作区", "", "奶蛙工作区 (*.json);;所有文件 (*.*)")
        if not path:
            return
        try:
            workspace = json.loads(Path(path).read_text(encoding="utf-8"))
            master = workspace["master"]
            slave = workspace.get("slave", {})
            if workspace.get("version") != 1:
                raise ValueError("此工作区版本不受支持。")
            self.protocol_combo.setCurrentText(master["protocol"])
            self.host_input.setText(master["host"])
            self.tcp_port_input.setValue(int(master["tcp_port"]))
            self.com_combo.setCurrentText(master["serial_port"])
            self.baud_combo.setCurrentText(master["baudrate"])
            self.parity_combo.setCurrentText(master["parity"])
            self.stopbits_combo.setCurrentText(master["stopbits"])
            self.unit_id_input.setValue(int(master["unit_id"]))
            self.function_combo.setCurrentIndex(max(0, self.function_combo.findData(int(master["function"]))))
            self.address_base_combo.setCurrentIndex(max(0, self.address_base_combo.findData(int(master.get("address_base", 0)))))
            self.address_input.setValue(int(master["address"]))
            self.count_input.setValue(int(master["count"]))
            self.interval_input.setValue(int(master["interval_ms"]))
            self.timeout_input.setValue(int(master.get("timeout_ms", 1200)))
            self.retries_input.setValue(int(master.get("retries", 0)))
            self.value_type_combo.setCurrentIndex(max(0, self.value_type_combo.findData(master["value_type"])))
            self.word_order_combo.setCurrentIndex(max(0, self.word_order_combo.findData(master["word_order"])))
            if slave:
                self.listen_host.setText(slave["host"])
                self.listen_port.setValue(int(slave["port"]))
                self.listen_unit.setValue(int(slave["unit_id"]))
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            QMessageBox.warning(self, "打开工作区失败", f"工作区内容无效：{exc}")
            return
        self._refresh_status_line()
        self.statusBar().showMessage(f"工作区已打开：{Path(path).name}", 5000)

    def _build_master_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("mainPage")
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setMinimumWidth(320)
        scroll.setMaximumWidth(392)
        controls = QWidget()
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 4, 0)
        controls_layout.setSpacing(10)

        conn_frame, conn_layout = card("设备连接")
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setHorizontalSpacing(9)
        form.setVerticalSpacing(9)
        self.protocol_combo = WheelGuardComboBox()
        self.protocol_combo.addItems(["Modbus TCP", "Modbus RTU"])
        self.host_input = QLineEdit("192.168.1.10")
        self.host_input.setPlaceholderText("例如 192.168.1.10")
        self.tcp_port_input = WheelGuardSpinBox()
        self.tcp_port_input.setRange(1, 65535)
        self.tcp_port_input.setValue(502)
        self.com_combo = WheelGuardComboBox()
        self.com_combo.setEditable(True)
        self.com_combo.setCurrentText("COM1")
        self.baud_combo = WheelGuardComboBox()
        self.baud_combo.setEditable(True)
        self.baud_combo.addItems(["300", "600", "1200", "2400", "4800", "9600", "14400", "19200", "38400", "56000", "57600", "115200", "128000", "153600", "230400", "256000", "460800", "921600"])
        self.baud_combo.setCurrentText("9600")
        self.parity_combo = WheelGuardComboBox()
        self.parity_combo.addItems(["N", "E", "O"])
        self.stopbits_combo = WheelGuardComboBox()
        self.stopbits_combo.addItems(["1", "2"])
        self.unit_id_input = WheelGuardSpinBox()
        self.unit_id_input.setRange(1, 247)
        self.unit_id_input.setValue(1)

        self.host_label = form_label("主机 IP")
        self.port_label = form_label("TCP 端口")
        self.com_label = form_label("串口")
        self.baud_label = form_label("波特率")
        self.parity_label = form_label("校验")
        self.stopbits_label = form_label("停止位")
        form.addRow(form_label("协议"), self.protocol_combo)
        form.addRow(self.host_label, self.host_input)
        form.addRow(self.port_label, self.tcp_port_input)
        form.addRow(self.com_label, self.com_combo)
        form.addRow(self.baud_label, self.baud_combo)
        form.addRow(self.parity_label, self.parity_combo)
        form.addRow(self.stopbits_label, self.stopbits_combo)
        form.addRow(form_label("从站 ID"), self.unit_id_input)
        conn_layout.addLayout(form)

        conn_buttons = QHBoxLayout()
        self.connect_button = QPushButton("连接并自动轮询")
        self.connect_button.setObjectName("primaryButton")
        self.refresh_ports_button = QPushButton("刷新串口")
        conn_buttons.addWidget(self.connect_button, 1)
        conn_buttons.addWidget(self.refresh_ports_button)
        conn_layout.addLayout(conn_buttons)
        controls_layout.addWidget(conn_frame)

        poll_frame, poll_layout = card("轮询参数")
        poll_form = QFormLayout()
        self.function_combo = WheelGuardComboBox()
        for text, code in [
            ("01 · 线圈", 1),
            ("02 · 离散输入", 2),
            ("03 · 保持寄存器", 3),
            ("04 · 输入寄存器", 4),
        ]:
            self.function_combo.addItem(text, code)
        self.address_input = WheelGuardSpinBox()
        self.address_input.setRange(0, 65535)
        self.address_input.setValue(0)
        self.count_input = WheelGuardSpinBox()
        self.count_input.setRange(1, 125)
        self.count_input.setValue(8)
        self.address_base_combo = WheelGuardComboBox()
        self.address_base_combo.addItem("0 起始（协议地址）", 0)
        self.address_base_combo.addItem("1 起始（设备地址）", 1)
        self.interval_input = WheelGuardSpinBox()
        self.interval_input.setRange(100, 60000)
        self.interval_input.setSingleStep(100)
        self.interval_input.setValue(1000)
        self.interval_input.setSuffix(" ms")
        self.timeout_input = WheelGuardSpinBox()
        self.timeout_input.setRange(100, 60000)
        self.timeout_input.setSingleStep(100)
        self.timeout_input.setValue(1200)
        self.timeout_input.setSuffix(" ms")
        self.retries_input = WheelGuardSpinBox()
        self.retries_input.setRange(0, 5)
        self.retries_input.setValue(0)
        poll_form.addRow(form_label("功能码"), self.function_combo)
        poll_form.addRow(form_label("地址基准"), self.address_base_combo)
        poll_form.addRow(form_label("起始地址"), self.address_input)
        poll_form.addRow(form_label("读取数量"), self.count_input)
        poll_form.addRow(form_label("轮询间隔"), self.interval_input)
        poll_form.addRow(form_label("响应超时"), self.timeout_input)
        poll_form.addRow(form_label("失败重试"), self.retries_input)
        poll_layout.addLayout(poll_form)

        read_buttons = QHBoxLayout()
        self.read_once_button = QPushButton("单次读取")
        self.read_once_button.setEnabled(False)
        self.poll_button = QPushButton("开始轮询")
        self.poll_button.setObjectName("primaryButton")
        self.poll_button.setEnabled(False)
        read_buttons.addWidget(self.read_once_button)
        read_buttons.addWidget(self.poll_button)
        poll_layout.addLayout(read_buttons)
        self.sound_checkbox = QCheckBox("收到数据时播放奶蛙齁笑")
        self.sound_checkbox.setChecked(self.audio.enabled)
        self.sound_button = QPushButton("试听 / 选择音效")
        poll_layout.addWidget(self.sound_checkbox)
        poll_layout.addWidget(self.sound_button)
        data_log_row = QHBoxLayout()
        self.data_log_checkbox = QCheckBox("实时记录轮询数值")
        self.data_log_checkbox.setEnabled(bool(self._data_log_path))
        self.data_log_checkbox.setChecked(self._data_log_enabled)
        self.data_log_button = QPushButton("选择 CSV…")
        data_log_row.addWidget(self.data_log_checkbox, 1)
        data_log_row.addWidget(self.data_log_button)
        poll_layout.addLayout(data_log_row)
        self.data_log_path_label = QLabel(Path(self._data_log_path).name if self._data_log_path else "未选择记录文件")
        self.data_log_path_label.setObjectName("muted")
        self.data_log_path_label.setToolTip(self._data_log_path or "选择 CSV 文件后可记录实时轮询值")
        poll_layout.addWidget(self.data_log_path_label)
        controls_layout.addWidget(poll_frame)

        write_frame, write_layout = card("手动写入")
        self.write_enable = QCheckBox("我已确认正在连接可安全写入的设备")
        self.write_enable.setChecked(False)
        self.write_function = WheelGuardComboBox()
        self.write_function.addItem("05 · 写单线圈", 5)
        self.write_function.addItem("06 · 写保持寄存器", 6)
        self.write_function.addItem("15 · 写多个线圈", 15)
        self.write_function.addItem("16 · 写多个保持寄存器", 16)
        self.write_address = WheelGuardSpinBox()
        self.write_address.setRange(0, 65535)
        self.write_value = QLineEdit("0")
        self.write_value.setPlaceholderText("线圈填 0/1；寄存器填 0–65535")
        self.write_button = QPushButton("写入设备")
        self.write_button.setObjectName("writeButton")
        write_form = QFormLayout()
        write_form.addRow(form_label("功能码"), self.write_function)
        write_form.addRow(form_label("地址"), self.write_address)
        write_form.addRow(form_label("写入值"), self.write_value)
        write_layout.addWidget(self.write_enable)
        write_layout.addLayout(write_form)
        write_layout.addWidget(self.write_button)
        controls_layout.addWidget(write_frame)
        controls_layout.addStretch(1)
        scroll.setWidget(controls)
        layout.addWidget(scroll)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)

        stats_card = QFrame()
        stats_card.setObjectName("statusStrip")
        stats_layout = QHBoxLayout(stats_card)
        stats_layout.setContentsMargins(8, 4, 8, 4)
        stats_layout.setSpacing(14)
        stats_row = QHBoxLayout()
        self.hero_status = QLabel("● 未连接")
        self.hero_status.setObjectName("connectionStatusOff")
        self.stat_device = self._stat_block("目标设备", "未连接")
        self.stat_data = self._stat_block("最近数据", "—")
        self.stat_latency = self._stat_block("往返延迟", "—")
        self.stat_device_value, self.stat_device_caption = self.stat_device
        self.stat_data_value, self.stat_data_caption = self.stat_data
        self.stat_latency_value, self.stat_latency_caption = self.stat_latency
        stats_row.addWidget(self.hero_status)
        for block in (self.stat_device, self.stat_data, self.stat_latency):
            item = QVBoxLayout()
            item.addWidget(block[0])
            item.addWidget(block[1])
            stats_row.addLayout(item, 1)
        stats_row.addWidget(self._mascot_card())
        stats_layout.addLayout(stats_row)
        right_layout.addWidget(stats_card)

        data_frame = QFrame()
        data_frame.setObjectName("dataView")
        data_layout = QVBoxLayout(data_frame)
        data_layout.setContentsMargins(5, 3, 5, 4)
        data_layout.setSpacing(5)
        table_header = QHBoxLayout()
        table_title = QLabel("数据监视")
        table_title.setObjectName("sectionTitle")
        self.value_type_combo = WheelGuardComboBox()
        for label, code in [
            ("UInt16", "u16"),
            ("Int16", "s16"),
            ("Hex 16", "hex16"),
            ("Binary 16", "bin16"),
            ("UInt32", "u32"),
            ("Int32", "s32"),
            ("Float32", "f32"),
            ("UInt64", "u64"),
            ("Int64", "s64"),
            ("Float64", "f64"),
        ]:
            self.value_type_combo.addItem(label, code)
        self.word_order_combo = WheelGuardComboBox()
        self.word_order_combo.addItem("ABCD · 标准", "ABCD")
        self.word_order_combo.addItem("CDAB · 字交换", "CDAB")
        self.word_order_combo.addItem("BADC · 字节交换", "BADC")
        self.word_order_combo.addItem("DCBA · 字节+字交换", "DCBA")
        self.export_button = QPushButton("导出日志 CSV")
        table_header.addWidget(table_title)
        table_header.addStretch(1)
        table_header.addWidget(form_label("数值解释"))
        table_header.addWidget(self.value_type_combo)
        table_header.addWidget(self.word_order_combo)
        table_header.addWidget(self.export_button)
        data_layout.addLayout(table_header)
        self.data_table = QTableWidget(0, 5)
        self.data_table.setHorizontalHeaderLabels(["地址", "信号", "原始值", "十六进制", "解释值"])
        self.data_table.setAlternatingRowColors(True)
        self.data_table.verticalHeader().setVisible(False)
        self.data_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.data_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.data_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.data_table.horizontalHeader().setStretchLastSection(True)
        self.data_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.data_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.data_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.data_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        data_layout.addWidget(self.data_table, 1)
        right_layout.addWidget(data_frame, 1)

        log_frame, log_layout = card("通信记录")
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(500)
        self.log_view.setMinimumHeight(128)
        log_layout.addWidget(self.log_view)
        right_layout.addWidget(log_frame)
        self.master_data_widget = right

        self.protocol_combo.currentIndexChanged.connect(self._update_protocol_fields)
        self.function_combo.currentIndexChanged.connect(self._update_count_limit)
        self.connect_button.clicked.connect(self._toggle_connection)
        self.refresh_ports_button.clicked.connect(self._refresh_serial_ports)
        self.read_once_button.clicked.connect(self._read_once)
        self.poll_button.clicked.connect(self._toggle_polling)
        self.sound_checkbox.toggled.connect(self._set_sound_enabled)
        self.sound_button.clicked.connect(self._select_audio)
        self.data_log_checkbox.toggled.connect(self._set_data_logging)
        self.data_log_button.clicked.connect(self._select_data_log_file)
        self.write_enable.toggled.connect(self._update_write_controls)
        self.write_function.currentIndexChanged.connect(self._update_write_controls)
        self.write_button.clicked.connect(self._write_value)
        self.export_button.clicked.connect(self._export_log)
        self.value_type_combo.currentIndexChanged.connect(self._render_current_values)
        self.word_order_combo.currentIndexChanged.connect(self._render_current_values)
        self.address_base_combo.currentIndexChanged.connect(self._update_address_base)
        self.address_base_combo.currentIndexChanged.connect(self._render_current_values)
        self.data_table.cellDoubleClicked.connect(self._quick_write_cell)
        return page

    @staticmethod
    def _stat_block(title: str, value: str) -> tuple[QLabel, QLabel]:
        value_label = QLabel(value)
        value_label.setObjectName("statusCompactValue")
        caption = QLabel(title)
        caption.setObjectName("statusCaption")
        return value_label, caption

    def _mascot_card(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("mascotStatus")
        row = QHBoxLayout(frame)
        row.setContentsMargins(3, 0, 6, 0)
        self.master_mascot = MascotWidget()
        self.master_mascot.setFixedSize(52, 48)
        self.hero_mascot = self.master_mascot
        label_col = QVBoxLayout()
        self.mascot_caption = QLabel("盯着数据中")
        self.mascot_caption.setStyleSheet("color:#62584A; font-weight:750; font-size:11px;")
        mini = QLabel("读到数据就笑")
        mini.setObjectName("muted")
        mini.setStyleSheet("color:#847C71; font-size:9px;")
        label_col.addWidget(self.mascot_caption)
        label_col.addWidget(mini)
        row.addWidget(self.master_mascot)
        row.addLayout(label_col)
        return frame

    def _build_slave_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("mainPage")
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        settings_frame, settings_layout = card("从站网络")
        settings_form = QFormLayout()
        self.listen_host = QLineEdit("127.0.0.1")
        self.listen_port = WheelGuardSpinBox()
        self.listen_port.setRange(1, 65535)
        self.listen_port.setValue(1502)
        self.listen_unit = WheelGuardSpinBox()
        self.listen_unit.setRange(1, 247)
        self.listen_unit.setValue(1)
        settings_form.addRow(form_label("监听地址"), self.listen_host)
        settings_form.addRow(form_label("TCP 端口"), self.listen_port)
        settings_form.addRow(form_label("从站 ID"), self.listen_unit)
        settings_layout.addLayout(settings_form)
        self.listen_hint = QLabel("127.0.0.1 仅允许本机连接；局域网联调可填 0.0.0.0")
        self.listen_hint.setWordWrap(True)
        self.listen_hint.setObjectName("muted")
        settings_layout.addWidget(self.listen_hint)
        self.server_toggle = QPushButton("启动从站")
        self.server_toggle.setObjectName("darkButton")
        settings_layout.addWidget(self.server_toggle)
        self.server_status = QLabel("● 已停止")
        self.server_status.setObjectName("pillOff")
        settings_layout.addWidget(self.server_status)
        self.server_target = QLabel("主站连接：127.0.0.1:1502 · Unit 1")
        self.server_target.setWordWrap(True)
        self.server_target.setStyleSheet("color:#81796F; font-family:Consolas, monospace; font-size:11px;")
        settings_layout.addWidget(self.server_target)
        self.local_test_button = QPushButton("用本机主站读一次")
        self.local_test_button.setObjectName("primaryButton")
        settings_layout.addWidget(self.local_test_button)
        settings_layout.addStretch(1)

        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setFrameShape(QFrame.Shape.NoFrame)
        settings_scroll.setMinimumWidth(320)
        settings_scroll.setMaximumWidth(392)
        settings_scroll.setWidget(settings_frame)
        layout.addWidget(settings_scroll)

        data_frame, data_layout = card("模拟数据区")
        toolbar = QHBoxLayout()
        self.sim_area_combo = WheelGuardComboBox()
        self.sim_area_combo.addItem("保持寄存器 · FC03", (3, "HR"))
        self.sim_area_combo.addItem("输入寄存器 · FC04", (4, "IR"))
        self.sim_area_combo.addItem("线圈 · FC01", (1, "CO"))
        self.sim_area_combo.addItem("离散输入 · FC02", (2, "DI"))
        self.sim_address_input = WheelGuardSpinBox()
        self.sim_address_input.setRange(0, 65520)
        self.sim_address_input.setValue(0)
        self.sim_address_input.setPrefix("起始地址 ")
        self.sim_apply_button = QPushButton("应用 16 项")
        self.sim_apply_button.setObjectName("primaryButton")
        self.sim_reset_button = QPushButton("恢复示例值")
        toolbar.addWidget(self.sim_area_combo)
        toolbar.addWidget(self.sim_address_input)
        toolbar.addStretch(1)
        toolbar.addWidget(self.sim_reset_button)
        toolbar.addWidget(self.sim_apply_button)
        data_layout.addLayout(toolbar)
        self.sim_table = QTableWidget(16, 2)
        self.sim_table.setHorizontalHeaderLabels(["地址", "模拟值（可编辑）"])
        self.sim_table.verticalHeader().setVisible(False)
        self.sim_table.horizontalHeader().setStretchLastSection(True)
        self.sim_table.setAlternatingRowColors(True)
        self.sim_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.sim_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for row in range(16):
            address_item = QTableWidgetItem(str(row))
            address_item.setFlags(address_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.sim_table.setItem(row, 0, address_item)
            self.sim_table.setItem(row, 1, QTableWidgetItem("0"))
        data_layout.addWidget(self.sim_table, 1)
        self.sim_hint = QLabel("主站写入保持寄存器或线圈后，点击“读取当前值”刷新表格。")
        self.sim_hint.setObjectName("muted")
        data_layout.addWidget(self.sim_hint)
        refresh_row = QHBoxLayout()
        self.sim_read_button = QPushButton("读取当前值")
        self.sim_read_button.setObjectName("darkButton")
        refresh_row.addWidget(self.sim_read_button)
        refresh_row.addStretch(1)
        data_layout.addLayout(refresh_row)
        layout.addWidget(data_frame, 1)

        self.server_toggle.clicked.connect(self._toggle_server)
        self.local_test_button.clicked.connect(self._local_test_read)
        self.sim_area_combo.currentIndexChanged.connect(self._load_sim_values)
        self.sim_address_input.valueChanged.connect(self._load_sim_values)
        self.sim_apply_button.clicked.connect(self._apply_sim_values)
        self.sim_reset_button.clicked.connect(self._reset_sim_values)
        self.sim_read_button.clicked.connect(self._load_sim_values)
        self.listen_host.textChanged.connect(self._update_server_target)
        self.listen_port.valueChanged.connect(self._update_server_target)
        self.listen_unit.valueChanged.connect(self._update_server_target)
        self._set_sim_example_values()
        self._update_server_target()
        return page

    def _switch_mode(self, index: int) -> None:
        master = index == 0
        if master:
            self.master_subwindow.show()
            if not getattr(self, "_master_fitted", False):
                self._fit_subwindow(self.master_subwindow)
            self.mdi_area.setActiveSubWindow(self.master_subwindow)
            self.control_dock.show()
        else:
            self.slave_subwindow.show()
            if not getattr(self, "_slave_fitted", False):
                area = self.mdi_area.viewport().rect().adjusted(28, 28, -28, -28)
                self.slave_subwindow.setGeometry(
                    area.x(), area.y(),
                    max(self.slave_subwindow.minimumWidth(), area.width()),
                    max(self.slave_subwindow.minimumHeight(), area.height()),
                )
                self.slave_subwindow.showNormal()
                self._slave_fitted = True
            self.mdi_area.setActiveSubWindow(self.slave_subwindow)
            self.control_dock.hide()
        self.master_mode_button.setObjectName("primaryButton" if master else "")
        self.slave_mode_button.setObjectName("" if master else "primaryButton")
        self.master_mode_button.style().unpolish(self.master_mode_button)
        self.master_mode_button.style().polish(self.master_mode_button)
        self.slave_mode_button.style().unpolish(self.slave_mode_button)
        self.slave_mode_button.style().polish(self.slave_mode_button)
        self.mode_hint.setText("主站 · 读取真实设备并自动轮询" if master else "从站 · 让 PLC 或其他主站连接本机")
        self.statusBar().showMessage(self.mode_hint.text())

    def _refresh_serial_ports(self) -> None:
        try:
            from serial.tools import list_ports

            selected = self.com_combo.currentText() if hasattr(self, "com_combo") else "COM1"
            available = [port.device for port in list_ports.comports()]
            if hasattr(self, "com_combo"):
                self.com_combo.clear()
                self.com_combo.addItems(available or [selected or "COM1"])
                self.com_combo.setCurrentText(selected if selected in available else (available[0] if available else selected or "COM1"))
        except Exception:
            pass

    def _update_protocol_fields(self, *_args) -> None:
        is_tcp = self.protocol_combo.currentText() == "Modbus TCP"
        for widget in (self.host_label, self.host_input, self.port_label, self.tcp_port_input):
            widget.setVisible(is_tcp)
        for widget in (
            self.com_label,
            self.com_combo,
            self.baud_label,
            self.baud_combo,
            self.parity_label,
            self.parity_combo,
            self.stopbits_label,
            self.stopbits_combo,
        ):
            widget.setVisible(not is_tcp)

    def _update_count_limit(self, *_args) -> None:
        function = int(self.function_combo.currentData())
        max_count = 2000 if function in (1, 2) else 125
        self.count_input.setMaximum(max_count)
        self.count_input.setToolTip(f"FC{function:02d} 单次最多读取 {max_count} 项")

    def _update_address_base(self, *_args) -> None:
        base = int(self.address_base_combo.currentData())
        for widget in (self.address_input, self.write_address):
            widget.setRange(base, 65535 + base)

    def _connection_config(self) -> dict[str, Any]:
        protocol = self.protocol_combo.currentText()
        config: dict[str, Any] = {
            "protocol": protocol,
            "unit_id": self.unit_id_input.value(),
            "function": int(self.function_combo.currentData()),
            "address": self.address_input.value() - int(self.address_base_combo.currentData()),
            "address_base": int(self.address_base_combo.currentData()),
            "count": self.count_input.value(),
            "timeout": self.timeout_input.value() / 1000.0,
            "retries": self.retries_input.value(),
        }
        max_count = 2000 if config["function"] in (1, 2) else 125
        if not 1 <= config["count"] <= max_count:
            raise ValueError(f"FC{config['function']:02d} 数量必须在 1–{max_count} 范围内。")
        if config["address"] + config["count"] > 65536:
            raise ValueError("起始地址与读取数量超出 Modbus 0–65535 地址范围。")
        if protocol == "Modbus TCP":
            config.update({"host": self.host_input.text().strip(), "port": self.tcp_port_input.value()})
            if not config["host"]:
                raise ValueError("请填写设备 IP 地址。")
        else:
            config.update({
                "port_name": self.com_combo.currentText().strip(),
                "baudrate": int(self.baud_combo.currentText()),
                "parity": self.parity_combo.currentText(),
                "stopbits": int(self.stopbits_combo.currentText()),
            })
            if not config["port_name"]:
                raise ValueError("请选择串口。")
        return config

    def _toggle_connection(self) -> None:
        if self._connected:
            self._auto_poll_after_connect = False
            self.worker.disconnect_requested.emit()
            self._set_polling_state(False)
            return
        if self._connecting:
            return
        try:
            self._connecting = True
            self._auto_poll_after_connect = True
            self.connect_button.setEnabled(False)
            self.action_connect.setEnabled(False)
            self.worker.connect_requested.emit(self._connection_config())
        except ValueError as exc:
            self._connecting = False
            self.connect_button.setEnabled(True)
            self.action_connect.setEnabled(True)
            self._auto_poll_after_connect = False
            QMessageBox.information(self, "连接参数", str(exc))

    def _read_once(self) -> None:
        try:
            self.worker.read_once_requested.emit(self._connection_config())
        except (ValueError, TypeError) as exc:
            QMessageBox.information(self, "读取参数", str(exc))

    def _toggle_polling(self) -> None:
        if self._polling:
            self.worker.stop_poll_requested.emit()
            self._set_polling_state(False)
        else:
            try:
                config = self._connection_config()
                self.worker.start_poll_requested.emit(config, self.interval_input.value())
                self._set_polling_state(True)
            except (ValueError, TypeError) as exc:
                QMessageBox.information(self, "轮询参数", str(exc))

    def _set_polling_state(self, running: bool) -> None:
        self._polling = running
        self.poll_button.setText("停止轮询" if running else "开始轮询")
        self.action_poll.setText("停止轮询" if running else "开始轮询")
        self.poll_button.setObjectName("writeButton" if running else "primaryButton")
        self.poll_button.style().unpolish(self.poll_button)
        self.poll_button.style().polish(self.poll_button)

    def _on_connection_changed(self, success: bool, message: str) -> None:
        self._connected = success
        self._connecting = False
        self.connect_button.setEnabled(True)
        self.action_connect.setEnabled(not success)
        self.action_disconnect.setEnabled(success)
        if not success:
            self._auto_poll_after_connect = False
            self._set_polling_state(False)
        self.connect_button.setText("断开连接" if success else "连接并自动轮询")
        self.connect_button.setObjectName("writeButton" if success else "primaryButton")
        self.hero_status.setText(f"● 已连接 · {message}" if success else f"● 未连接 · {message}")
        self.hero_status.setObjectName("connectionStatusOn" if success else "connectionStatusOff")
        self.hero_status.style().unpolish(self.hero_status)
        self.hero_status.style().polish(self.hero_status)
        self.statusBar().showMessage(message if success else f"未连接 · {message}")
        self._refresh_status_line()
        self.connect_button.style().unpolish(self.connect_button)
        self.connect_button.style().polish(self.connect_button)
        self.read_once_button.setEnabled(success)
        self.poll_button.setEnabled(success)
        self._set_connection_inputs_enabled(not success)
        self.stat_device_value.setText(message.split("·")[0].strip() if success else "未连接")
        self.stat_device_caption.setText("在线" if success else "等待连接")
        if success:
            self.mascot_caption.setText("连上啦，挥手！")
            self.master_mascot.wave()
            self.hero_mascot.wave()
        elif hasattr(self, "mascot_caption"):
            self.mascot_caption.setText("等你连接")
        self._update_write_controls()
        if success and self._auto_poll_after_connect:
            self._auto_poll_after_connect = False
            self._toggle_polling()

    def _set_connection_inputs_enabled(self, enabled: bool) -> None:
        for widget in (
            self.protocol_combo,
            self.host_input,
            self.tcp_port_input,
            self.com_combo,
            self.baud_combo,
            self.parity_combo,
            self.stopbits_combo,
            self.unit_id_input,
            self.timeout_input,
            self.retries_input,
            self.refresh_ports_button,
        ):
            widget.setEnabled(enabled)

    def _on_data_received(self, result: dict[str, Any]) -> None:
        self._latest_values = result["values"]
        self._latest_address = result["address"]
        self._latest_function = result["function"]
        self._render_current_values()
        self._record_data_sample(result)
        self.stat_data_value.setText(result["timestamp"])
        self.stat_data_caption.setText(f"FC{result['function']:02d} · {len(result['values'])} 项")
        self.stat_latency_value.setText(f"{result['latency_ms']:.1f} ms")
        self._latencies.append(float(result["latency_ms"]))
        if len(self._latencies) > 100:
            self._latencies = self._latencies[-100:]
        average_ms = sum(self._latencies) / len(self._latencies)
        self.stat_latency_caption.setText(
            f"最近 {len(self._latencies)} 次均值 {average_ms:.1f} ms · Unit {result['unit_id']}"
        )
        self.statusBar().showMessage(
            f"RX · Unit {result['unit_id']} · FC{result['function']:02d} · {len(result['values'])} 项 · {result['latency_ms']:.2f} ms"
        )
        self.mascot_caption.setText("哈哈哈哈！")
        self.master_mascot.laugh()
        self.hero_mascot.laugh()
        self.audio.play()

    def _record_data_sample(self, result: dict[str, Any]) -> None:
        if not self._data_log_enabled or not self._data_log_path:
            return
        path = Path(self._data_log_path)
        function = int(result["function"])
        values = result["values"]
        dtype = self.value_type_combo.currentData()
        word_order = self.word_order_combo.currentData()
        decoded = (
            self._decode_registers(values, dtype, word_order)
            if function in (3, 4)
            else ["ON" if value else "OFF" for value in values]
        )
        protocol = self.protocol_combo.currentText()
        target = (
            f"{self.host_input.text().strip()}:{self.tcp_port_input.value()}"
            if protocol == "Modbus TCP"
            else self.com_combo.currentText().strip()
        )
        try:
            needs_header = not path.is_file() or path.stat().st_size == 0
            encoding = "utf-8-sig" if needs_header else "utf-8"
            with path.open("a", newline="", encoding=encoding) as stream:
                writer = csv.writer(stream)
                if needs_header:
                    writer.writerow(["时间", "协议", "设备", "Unit ID", "功能码", "协议地址(0起始)", "类型", "原始值", "十六进制", "解析值", "延迟(ms)"])
                for index, value in enumerate(values):
                    address = int(result["address"]) + index
                    is_bit = isinstance(value, bool)
                    raw_text = ("ON" if value else "OFF") if is_bit else str(int(value))
                    hex_text = "—" if is_bit else f"0x{int(value):04X}"
                    writer.writerow([
                        result["timestamp"], protocol, target, result["unit_id"], function,
                        address, "位" if is_bit else "寄存器", raw_text, hex_text, decoded[index],
                        f"{result['latency_ms']:.1f}",
                    ])
        except (OSError, csv.Error, ValueError) as exc:
            self.data_log_checkbox.setChecked(False)
            self._set_data_logging(False)
            self._append_log("ERR", f"实时 CSV 记录已停止：{exc}")

    def _render_current_values(self, *_args) -> None:
        if not hasattr(self, "data_table"):
            return
        function = self._latest_function
        values = self._latest_values
        if self.data_table.rowCount() != len(values):
            self.data_table.setRowCount(len(values))
        dtype = self.value_type_combo.currentData()
        word_order = self.word_order_combo.currentData()
        decoded = self._decode_registers(values, dtype, word_order) if function in (3, 4) else ["ON" if value else "OFF" for value in values]
        self.data_table.setUpdatesEnabled(False)
        try:
            for index, value in enumerate(values):
                address = self._latest_address + index
                raw_text = ("ON" if value else "OFF") if isinstance(value, bool) else str(int(value))
                hex_text = "—" if isinstance(value, bool) else f"0x{int(value):04X}"
                address += int(self.address_base_combo.currentData())
                fields = [str(address).zfill(5), "位" if function in (1, 2) else "寄存器", raw_text, hex_text, decoded[index]]
                for column, text in enumerate(fields):
                    cell = self.data_table.item(index, column)
                    if cell is None:
                        cell = QTableWidgetItem(text)
                        if column in (0, 2, 3, 4):
                            cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        if column == 0:
                            cell.setForeground(QColor("#847C71"))
                        self.data_table.setItem(index, column, cell)
                    elif cell.text() != text:
                        cell.setText(text)
        finally:
            self.data_table.setUpdatesEnabled(True)

    @staticmethod
    def _decode_registers(values: list[int | bool], dtype: str, word_order: str) -> list[str]:
        result = ["—"] * len(values)
        if dtype in ("u16", "s16", "hex16", "bin16"):
            for i, raw in enumerate(values):
                value = int(raw) & 0xFFFF
                if dtype == "s16" and value >= 0x8000:
                    value -= 0x10000
                if dtype == "hex16":
                    result[i] = f"0x{value:04X}"
                elif dtype == "bin16":
                    result[i] = f"{value:016b}"
                else:
                    result[i] = str(value)
            return result
        formats = {
            "u32": (2, ">I", str),
            "s32": (2, ">i", str),
            "f32": (2, ">f", lambda value: format(value, ".9g")),
            "u64": (4, ">Q", str),
            "s64": (4, ">q", str),
            "f64": (4, ">d", lambda value: format(value, ".17g")),
        }
        spec = formats.get(dtype)
        if spec is None:
            return result
        group_size, format_code, formatter = spec
        for i in range(0, len(values) - group_size + 1, group_size):
            words = [int(value) & 0xFFFF for value in values[i : i + group_size]]
            if word_order in ("CDAB", "DCBA"):
                words.reverse()
            if word_order in ("BADC", "DCBA"):
                words = [((word & 0xFF) << 8) | (word >> 8) for word in words]
            packed = b"".join(struct.pack(">H", word) for word in words)
            decoded_value = struct.unpack(format_code, packed)[0]
            result[i] = formatter(decoded_value)
            for part in range(1, group_size):
                result[i + part] = f"({part + 1}/{group_size})"
        return result

    def _quick_write_cell(self, row: int, column: int) -> None:
        if column not in (2, 4) or row >= len(self._latest_values):
            return
        if self._latest_function in (1, 2):
            function = 5
            value = 1 if bool(self._latest_values[row]) else 0
        elif self._latest_function in (3, 4):
            function = 6
            value = int(self._latest_values[row])
        else:
            return
        self._switch_mode(0)
        self.control_dock.show()
        self.write_function.setCurrentIndex(max(0, self.write_function.findData(function)))
        self.write_address.setValue(self._latest_address + row + int(self.address_base_combo.currentData()))
        self.write_value.setText(str(value))
        if not self.write_enable.isChecked():
            self.write_enable.setFocus(Qt.FocusReason.MouseFocusReason)
            self.statusBar().showMessage("已填入选中值；勾选写入确认后再执行写入。")
            return
        self._write_value()

    def _set_sound_enabled(self, enabled: bool) -> None:
        self.audio.enabled = enabled
        self.settings.setValue("sound_enabled", enabled)

    def _set_data_logging(self, enabled: bool) -> None:
        self._data_log_enabled = bool(enabled and self._data_log_path)
        self.settings.setValue("data_log_enabled", self._data_log_enabled)

    def _select_data_log_file(self) -> None:
        suggested = self._data_log_path or "modbus_readings.csv"
        path, _ = QFileDialog.getSaveFileName(self, "选择实时数据 CSV", suggested, "CSV 文件 (*.csv)")
        if not path:
            return
        if not path.lower().endswith(".csv"):
            path += ".csv"
        self._data_log_path = path
        self.settings.setValue("data_log_path", path)
        self.data_log_path_label.setText(Path(path).name)
        self.data_log_path_label.setToolTip(path)
        self.data_log_checkbox.setEnabled(True)
        self.data_log_checkbox.setChecked(True)
        self._set_data_logging(True)
        self._append_log("INFO", f"实时读数将写入：{path}")

    def _select_audio(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择奶蛙音效", "", "WAV 音频 (*.wav)")
        if path:
            self.audio.custom_path = path
            self.settings.setValue("custom_audio", path)
            self.audio.play(force=True)
            self._append_log("INFO", f"已载入本地音效：{Path(path).name}")
        elif self.audio.custom_path:
            self.audio.play(force=True)
        else:
            self.audio.play(force=True)

    def _update_write_controls(self, *_args) -> None:
        enabled = self.write_enable.isChecked() and self._connected
        self.write_function.setEnabled(enabled)
        self.write_address.setEnabled(enabled)
        self.write_value.setEnabled(enabled)
        self.write_button.setEnabled(enabled)
        function = int(self.write_function.currentData())
        if function == 5:
            self.write_value.setPlaceholderText("填写 0 或 1")
        elif function == 15:
            self.write_value.setPlaceholderText("输入多个 0/1，用逗号分隔，如 1,0,1")
        elif function == 16:
            self.write_value.setPlaceholderText("输入多个 0–65535 数值，用逗号分隔")
        else:
            self.write_value.setPlaceholderText("填写 0–65535，可使用 0x 前缀")

    def _write_value(self) -> None:
        if not self.write_enable.isChecked() or not self._connected:
            return
        function = int(self.write_function.currentData())
        raw = self.write_value.text().strip().lower()
        tokens = [item.strip() for item in raw.split(",")]
        if not raw or any(not item for item in tokens):
            QMessageBox.information(self, "写入值", "请填写一个值；批量写入时使用逗号分隔。")
            return

        if function in (5, 15):
            allowed = {"0", "1", "false", "true", "off", "on"}
            if any(item not in allowed for item in tokens):
                QMessageBox.information(self, "写入值", "线圈值请使用 0、1、OFF 或 ON，并用逗号分隔。")
                return
            coils = [item in {"1", "true", "on"} for item in tokens]
            if function == 5 and len(coils) != 1:
                QMessageBox.information(self, "写入值", "FC05 只能填写一个线圈值。")
                return
            if function == 15 and len(coils) > 1968:
                QMessageBox.information(self, "写入值", "FC15 每次最多写入 1968 个线圈。")
                return
            value: int | bool | list[bool] | list[int] = coils[0] if function == 5 else coils
        else:
            try:
                registers = [parse_integer(item) for item in tokens]
            except ValueError:
                QMessageBox.information(self, "写入值", "寄存器值需为 0 到 65535 的整数，可使用 0x 前缀并用逗号分隔。")
                return
            if any(not 0 <= item <= 65535 for item in registers):
                QMessageBox.information(self, "写入值", "寄存器值超出范围（0–65535）。")
                return
            if function == 6 and len(registers) != 1:
                QMessageBox.information(self, "写入值", "FC06 只能填写一个寄存器值。")
                return
            if function == 16 and len(registers) > 123:
                QMessageBox.information(self, "写入值", "FC16 每次最多写入 123 个寄存器。")
                return
            value = registers[0] if function == 6 else registers

        display_address = self.write_address.value()
        address = display_address - int(self.address_base_combo.currentData())
        values = value if isinstance(value, list) else [value]
        if address < 0 or address + len(values) > 65536:
            QMessageBox.information(self, "写入地址", "写入地址超出 Modbus 0–65535 协议地址范围。")
            return
        shown_values = ["ON" if item is True else ("OFF" if item is False else str(item)) for item in values]
        shown = ", ".join(shown_values[:8])
        if len(shown_values) > 8:
            shown += f", …（共 {len(shown_values)} 项）"
        quantity = len(values)
        area = "线圈" if function in (5, 15) else "保持寄存器"
        answer = QMessageBox.warning(
            self,
            "确认写入设备",
            f"即将向 Unit {self.unit_id_input.value()} 的地址 {display_address} 写入 {quantity} 个{area}（协议地址 {address}）：{shown}。\n请再次核对设备和地址。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Yes:
            try:
                self.worker.write_requested.emit(self._connection_config(), function, address, value)
            except ValueError as exc:
                QMessageBox.information(self, "连接参数", str(exc))

    def _on_operation_finished(self, success: bool, message: str) -> None:
        if success:
            self.mascot_caption.setText("写入成功，打拳！")
            self.master_mascot.punch()
            self.hero_mascot.punch()
        else:
            self.stat_latency_value.setText("错误")
            self.stat_latency_caption.setText(message[:42])

    def _append_log(self, level: str, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        line = f"{timestamp}  {level:<5}  {message}"
        if hasattr(self, "log_view"):
            self.log_view.appendPlainText(line)
        self._records.append((timestamp, level, message))
        if level == "TX":
            self._tx_count += 1
        elif level == "RX":
            self._rx_count += 1
        elif level == "ERR":
            self._error_count += 1
        self._refresh_status_line()
        if len(self._records) > 2000:
            self._records = self._records[-1500:]

    def _refresh_status_line(self, *_args) -> None:
        if not hasattr(self, "protocol_status_label"):
            return
        unit = self.unit_id_input.value() if hasattr(self, "unit_id_input") else 1
        function = int(self.function_combo.currentData()) if hasattr(self, "function_combo") else 3
        interval = self.interval_input.value() if hasattr(self, "interval_input") else 1000
        self.protocol_status_label.setText(
            f"TX={self._tx_count}  RX={self._rx_count}  ERR={self._error_count}  ID={unit}  F={function:02d}  SR={interval}ms"
        )

    def _export_log(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "导出通信记录", "naiwa_modbus_log.csv", "CSV 文件 (*.csv)")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.writer(stream)
            writer.writerow(["时间", "类型", "记录"])
            writer.writerows(self._records)
        self._append_log("INFO", f"日志已导出：{path}")

    def _copy_selected_data(self) -> None:
        selected = self.data_table.selectedItems()
        if selected:
            QApplication.clipboard().setText("\t".join(item.text() for item in selected))

    def _clear_log(self) -> None:
        self.log_view.clear()
        self._records.clear()

    def _toggle_server(self) -> None:
        if self._simulator is not None and self._simulator.isRunning():
            self._simulator.request_stop()
            self.server_toggle.setEnabled(False)
            self.server_toggle.setText("正在停止…")
            return
        host = self.listen_host.text().strip()
        if not host:
            QMessageBox.information(self, "监听地址", "请填写监听 IP。")
            return
        try:
            unit_id = self.listen_unit.value()
            reuse_context = (
                self._simulator.context
                if self._simulator is not None
                and not self._simulator.isRunning()
                and self._simulator.unit_id == unit_id
                else None
            )
            simulator = TcpSimulatorThread(host, self.listen_port.value(), unit_id, context=reuse_context)
        except Exception as exc:
            QMessageBox.critical(self, "从站模拟", f"无法创建模拟数据区：{exc}")
            return
        self._simulator = simulator
        if reuse_context is None:
            for function, values in self._sim_values.items():
                self._simulator.context.set_local_values(function, 0, values)
        self._simulator.started_server.connect(self._on_server_started)
        self._simulator.stopped_server.connect(self._on_server_stopped)
        self._simulator.failed.connect(self._on_server_failed)
        self._simulator.start()
        self.server_toggle.setText("启动中…")
        self.server_toggle.setEnabled(False)

    def _on_server_started(self, message: str) -> None:
        self.server_status.setText("● 运行中")
        self.server_status.setObjectName("pillOn")
        self.server_status.style().unpolish(self.server_status)
        self.server_status.style().polish(self.server_status)
        self.server_toggle.setText("停止从站")
        self.server_toggle.setObjectName("writeButton")
        self.server_toggle.setEnabled(True)
        self.server_toggle.style().unpolish(self.server_toggle)
        self.server_toggle.style().polish(self.server_toggle)
        self._append_log("SERVER", message)
        self._load_sim_values()

    def _on_server_stopped(self) -> None:
        self.server_status.setText("● 已停止")
        self.server_status.setObjectName("pillOff")
        self.server_status.style().unpolish(self.server_status)
        self.server_status.style().polish(self.server_status)
        self.server_toggle.setText("启动从站")
        self.server_toggle.setObjectName("darkButton")
        self.server_toggle.setEnabled(True)
        self.server_toggle.style().unpolish(self.server_toggle)
        self.server_toggle.style().polish(self.server_toggle)
        self._append_log("SERVER", "TCP 从站已停止")

    def _on_server_failed(self, message: str) -> None:
        self._append_log("ERR", f"从站启动失败：{message}")
        QMessageBox.warning(self, "从站模拟启动失败", f"{message}\n请检查监听地址、端口是否被占用。")

    def _update_server_target(self, *_args) -> None:
        self.server_target.setText(
            f"主站连接：{self.listen_host.text().strip()}:{self.listen_port.value()} · Unit {self.listen_unit.value()}"
        )

    def _current_sim_area(self) -> tuple[int, str]:
        return self.sim_area_combo.currentData()

    def _set_sim_example_values(self) -> None:
        code, area = self._current_sim_area()
        values = self._sim_values[code]
        if self._simulator and self._simulator.isRunning():
            self._simulator.context.set_local_values(code, 0, values)
        self._load_sim_values()

    def _reset_sim_values(self) -> None:
        self._sim_values = {
            1: [True, False, True, True, False, False, True, False, True, False, False, True, False, True, True, False],
            2: [False, True, False, False, True, True, False, True, False, True, True, False, True, False, False, True],
            3: [0, 123, 250, 1000, 0, 1, 42, 65535, 12, 34, 56, 78, 90, 120, 300, 600],
            4: [220, 231, 228, 240, 235, 233, 229, 222, 218, 225, 237, 241, 232, 226, 219, 230],
        }
        if self._simulator and self._simulator.isRunning():
            for function, values in self._sim_values.items():
                self._simulator.context.set_local_values(function, 0, values)
        self._set_sim_example_values()
        self._append_log("SERVER", "已恢复四类数据区的示例值")

    def _apply_sim_values(self) -> None:
        code, area = self._current_sim_area()
        values: list[int | bool] = []
        start_address = self.sim_address_input.value()
        for row in range(16):
            raw = self.sim_table.item(row, 1).text().strip().lower()
            if area in ("CO", "DI"):
                if raw not in {"0", "1", "true", "false", "on", "off"}:
                    QMessageBox.information(self, "模拟数据", f"地址 {start_address + row} 的位值请填写 0/1、ON/OFF。")
                    return
                values.append(raw in {"1", "true", "on"})
            else:
                try:
                    value = parse_integer(raw)
                except ValueError:
                    QMessageBox.information(self, "模拟数据", f"地址 {start_address + row} 不是有效的 16 位整数。")
                    return
                if not 0 <= value <= 65535:
                    QMessageBox.information(self, "模拟数据", f"地址 {start_address + row} 的值需在 0–65535 范围内。")
                    return
                values.append(value)
        if self._simulator and self._simulator.isRunning():
            self._simulator.context.set_local_values(code, start_address, values)
        if start_address == 0:
            self._sim_values[code] = list(values)
        self._append_log("SERVER", f"已应用 {area} 地址 {start_address}–{start_address + 15} 的模拟数据")

    def _load_sim_values(self, *_args) -> None:
        simulator = self._simulator
        code, area = self._current_sim_area()
        start_address = self.sim_address_input.value()
        values = self._sim_values[code] if start_address == 0 else [False if area in ("CO", "DI") else 0] * 16
        if simulator and simulator.isRunning():
            try:
                values = simulator.context.get_local_values(code, start_address, 16)
                if start_address == 0:
                    self._sim_values[code] = list(values)
            except Exception as exc:
                self._append_log("ERR", f"读取模拟数据失败：{exc}")
        for row, value in enumerate(values):
            display = str(bool(value)) if area in ("CO", "DI") else str(int(value))
            self.sim_table.item(row, 0).setText(str(start_address + row))
            self.sim_table.item(row, 1).setText(display)

    def _local_test_read(self) -> None:
        if not self._simulator or not self._simulator.isRunning():
            QMessageBox.information(self, "本机测试", "请先启动从站模拟。")
            return
        self._switch_mode(0)
        self.protocol_combo.setCurrentText("Modbus TCP")
        self.host_input.setText("127.0.0.1")
        self.tcp_port_input.setValue(self.listen_port.value())
        self.unit_id_input.setValue(self.listen_unit.value())
        self.function_combo.setCurrentIndex(2)
        self.address_base_combo.setCurrentIndex(0)
        self.address_input.setValue(0)
        self.count_input.setValue(8)
        self._read_once()

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt event naming.
        self.audio.stop()
        if self._simulator and self._simulator.isRunning():
            self._simulator.request_stop()
            self._simulator.wait(2500)
        if self.worker_thread.isRunning():
            self.worker.shutdown_requested.emit()
            if not self.worker_thread.wait(2500):
                self.worker_thread.quit()
                self.worker_thread.wait(1000)
        event.accept()

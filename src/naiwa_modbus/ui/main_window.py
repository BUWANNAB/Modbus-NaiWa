from __future__ import annotations

import csv
import struct
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QThread, QSettings
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHeaderView,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
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


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("奶蛙 Modbus 数据站")
        self.resize(1320, 850)
        self.setMinimumSize(1040, 700)
        self.settings = QSettings("BUWANNAB", "NaiWaModbus")
        self.audio = LaughPlayer()
        self.audio.enabled = self.settings.value("sound_enabled", True, type=bool)
        self.audio.custom_path = self.settings.value("custom_audio", "", type=str) or None
        self._records: list[tuple[str, str, str]] = []
        self._connected = False
        self._polling = False
        self._latest_values: list[int | bool] = []
        self._latest_address = 0
        self._latest_function = 3
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
        self.worker.closed.connect(self.worker_thread.quit)
        self.worker_thread.start()

    def _build_ui(self) -> None:
        root = QWidget()
        outer = QVBoxLayout(root)
        outer.setContentsMargins(18, 16, 18, 16)
        outer.setSpacing(12)
        outer.addWidget(self._build_hero())

        mode_row = QHBoxLayout()
        mode_row.setSpacing(8)
        self.master_mode_button = QPushButton("主站轮询")
        self.master_mode_button.setObjectName("primaryButton")
        self.slave_mode_button = QPushButton("从站模拟")
        self.mode_hint = QLabel("笔记本作为主站，读取真实设备")
        self.mode_hint.setObjectName("muted")
        mode_row.addWidget(self.master_mode_button)
        mode_row.addWidget(self.slave_mode_button)
        mode_row.addSpacing(8)
        mode_row.addWidget(self.mode_hint)
        mode_row.addStretch(1)
        outer.addLayout(mode_row)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_master_page())
        self.pages.addWidget(self._build_slave_page())
        outer.addWidget(self.pages, 1)
        self.setCentralWidget(root)

        self.master_mode_button.clicked.connect(lambda: self._switch_mode(0))
        self.slave_mode_button.clicked.connect(lambda: self._switch_mode(1))

    def _build_hero(self) -> QFrame:
        hero = QFrame()
        hero.setObjectName("hero")
        row = QHBoxLayout(hero)
        row.setContentsMargins(20, 13, 18, 12)
        row.setSpacing(14)
        text = QVBoxLayout()
        eyebrow = QLabel("NAIWA · MODBUS WORKBENCH")
        eyebrow.setObjectName("brandEyebrow")
        title = QLabel("奶蛙数据站")
        title.setObjectName("brandTitle")
        subtitle = QLabel("把寄存器读明白 · 把通信状态看清楚")
        subtitle.setObjectName("heroSub")
        text.addWidget(eyebrow)
        text.addWidget(title)
        text.addWidget(subtitle)
        row.addLayout(text, 1)

        self.hero_status = QLabel("○  未连接")
        self.hero_status.setObjectName("heroBadge")
        row.addWidget(self.hero_status, 0, Qt.AlignmentFlag.AlignVCenter)
        self.hero_mascot = MascotWidget()
        self.hero_mascot.setFixedSize(94, 84)
        row.addWidget(self.hero_mascot)
        return hero

    def _build_master_page(self) -> QWidget:
        page = QWidget()
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
        self.protocol_combo = QComboBox()
        self.protocol_combo.addItems(["Modbus TCP", "Modbus RTU"])
        self.host_input = QLineEdit("192.168.1.10")
        self.host_input.setPlaceholderText("例如 192.168.1.10")
        self.tcp_port_input = QSpinBox()
        self.tcp_port_input.setRange(1, 65535)
        self.tcp_port_input.setValue(502)
        self.com_combo = QComboBox()
        self.com_combo.setEditable(True)
        self.com_combo.setCurrentText("COM1")
        self.baud_combo = QComboBox()
        self.baud_combo.setEditable(True)
        self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200", "230400"])
        self.baud_combo.setCurrentText("9600")
        self.parity_combo = QComboBox()
        self.parity_combo.addItems(["N", "E", "O"])
        self.stopbits_combo = QComboBox()
        self.stopbits_combo.addItems(["1", "2"])
        self.unit_id_input = QSpinBox()
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
        self.connect_button = QPushButton("连接设备")
        self.connect_button.setObjectName("darkButton")
        self.refresh_ports_button = QPushButton("刷新串口")
        conn_buttons.addWidget(self.connect_button, 1)
        conn_buttons.addWidget(self.refresh_ports_button)
        conn_layout.addLayout(conn_buttons)
        controls_layout.addWidget(conn_frame)

        poll_frame, poll_layout = card("轮询参数")
        poll_form = QFormLayout()
        self.function_combo = QComboBox()
        for text, code in [
            ("01 · 线圈", 1),
            ("02 · 离散输入", 2),
            ("03 · 保持寄存器", 3),
            ("04 · 输入寄存器", 4),
        ]:
            self.function_combo.addItem(text, code)
        self.address_input = QSpinBox()
        self.address_input.setRange(0, 65535)
        self.address_input.setValue(0)
        self.count_input = QSpinBox()
        self.count_input.setRange(1, 125)
        self.count_input.setValue(8)
        self.interval_input = QSpinBox()
        self.interval_input.setRange(100, 60000)
        self.interval_input.setSingleStep(100)
        self.interval_input.setValue(1000)
        self.interval_input.setSuffix(" ms")
        poll_form.addRow(form_label("功能码"), self.function_combo)
        poll_form.addRow(form_label("起始地址"), self.address_input)
        poll_form.addRow(form_label("读取数量"), self.count_input)
        poll_form.addRow(form_label("轮询间隔"), self.interval_input)
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
        controls_layout.addWidget(poll_frame)

        write_frame, write_layout = card("手动写入")
        self.write_enable = QCheckBox("我已确认正在连接可安全写入的设备")
        self.write_enable.setChecked(False)
        self.write_function = QComboBox()
        self.write_function.addItem("05 · 写单线圈", 5)
        self.write_function.addItem("06 · 写保持寄存器", 6)
        self.write_address = QSpinBox()
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
        right_layout.setSpacing(10)

        stats_card, stats_layout = card()
        stats_row = QHBoxLayout()
        self.stat_device = self._stat_block("目标设备", "未连接")
        self.stat_data = self._stat_block("最近数据", "—")
        self.stat_latency = self._stat_block("往返延迟", "—")
        self.stat_device_value, self.stat_device_caption = self.stat_device
        self.stat_data_value, self.stat_data_caption = self.stat_data
        self.stat_latency_value, self.stat_latency_caption = self.stat_latency
        for block in (self.stat_device, self.stat_data, self.stat_latency):
            item = QVBoxLayout()
            item.addWidget(block[0])
            item.addWidget(block[1])
            stats_row.addLayout(item, 1)
        stats_row.addWidget(self._mascot_card())
        stats_layout.addLayout(stats_row)
        right_layout.addWidget(stats_card)

        data_frame, data_layout = card()
        table_header = QHBoxLayout()
        table_title = QLabel("实时数据")
        table_title.setObjectName("sectionTitle")
        self.value_type_combo = QComboBox()
        self.value_type_combo.addItem("UInt16", "u16")
        self.value_type_combo.addItem("Int16", "s16")
        self.value_type_combo.addItem("UInt32", "u32")
        self.value_type_combo.addItem("Int32", "s32")
        self.value_type_combo.addItem("Float32", "f32")
        self.word_order_combo = QComboBox()
        self.word_order_combo.addItem("高位字在前", "big")
        self.word_order_combo.addItem("低位字在前", "little")
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
        layout.addWidget(right, 1)

        self.protocol_combo.currentIndexChanged.connect(self._update_protocol_fields)
        self.function_combo.currentIndexChanged.connect(self._update_count_limit)
        self.connect_button.clicked.connect(self._toggle_connection)
        self.refresh_ports_button.clicked.connect(self._refresh_serial_ports)
        self.read_once_button.clicked.connect(self._read_once)
        self.poll_button.clicked.connect(self._toggle_polling)
        self.sound_checkbox.toggled.connect(self._set_sound_enabled)
        self.sound_button.clicked.connect(self._select_audio)
        self.write_enable.toggled.connect(self._update_write_controls)
        self.write_button.clicked.connect(self._write_value)
        self.export_button.clicked.connect(self._export_log)
        self.value_type_combo.currentIndexChanged.connect(self._render_current_values)
        self.word_order_combo.currentIndexChanged.connect(self._render_current_values)
        return page

    @staticmethod
    def _stat_block(title: str, value: str) -> tuple[QLabel, QLabel]:
        value_label = QLabel(value)
        value_label.setObjectName("statusValue")
        caption = QLabel(title)
        caption.setObjectName("statusCaption")
        return value_label, caption

    def _mascot_card(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("QFrame { background: #edf2dc; border: 1px solid #d9e3c5; border-radius: 13px; }")
        row = QHBoxLayout(frame)
        row.setContentsMargins(7, 1, 10, 1)
        self.master_mascot = MascotWidget()
        self.master_mascot.setFixedSize(76, 70)
        label_col = QVBoxLayout()
        self.mascot_caption = QLabel("盯着数据中")
        self.mascot_caption.setStyleSheet("color:#294b35; font-weight:800; font-size:12px;")
        mini = QLabel("读到数据就笑")
        mini.setObjectName("muted")
        mini.setStyleSheet("color:#72816b; font-size:10px;")
        label_col.addWidget(self.mascot_caption)
        label_col.addWidget(mini)
        row.addWidget(self.master_mascot)
        row.addLayout(label_col)
        return frame

    def _build_slave_page(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        settings_frame, settings_layout = card("从站网络")
        settings_form = QFormLayout()
        self.listen_host = QLineEdit("127.0.0.1")
        self.listen_port = QSpinBox()
        self.listen_port.setRange(1, 65535)
        self.listen_port.setValue(1502)
        self.listen_unit = QSpinBox()
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
        self.server_target.setStyleSheet("color:#5c715f; font-family:Consolas, monospace; font-size:11px;")
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
        self.sim_area_combo = QComboBox()
        self.sim_area_combo.addItem("保持寄存器 · FC03", (3, "HR"))
        self.sim_area_combo.addItem("输入寄存器 · FC04", (4, "IR"))
        self.sim_area_combo.addItem("线圈 · FC01", (1, "CO"))
        self.sim_area_combo.addItem("离散输入 · FC02", (2, "DI"))
        self.sim_apply_button = QPushButton("应用 16 项")
        self.sim_apply_button.setObjectName("primaryButton")
        self.sim_reset_button = QPushButton("恢复示例值")
        toolbar.addWidget(self.sim_area_combo)
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
        self.pages.setCurrentIndex(index)
        master = index == 0
        self.master_mode_button.setObjectName("primaryButton" if master else "")
        self.slave_mode_button.setObjectName("" if master else "primaryButton")
        self.master_mode_button.style().unpolish(self.master_mode_button)
        self.master_mode_button.style().polish(self.master_mode_button)
        self.slave_mode_button.style().unpolish(self.slave_mode_button)
        self.slave_mode_button.style().polish(self.slave_mode_button)
        self.mode_hint.setText("笔记本作为主站，读取真实设备" if master else "让 PLC 或其他主站连接笔记本")

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
        self.count_input.setMaximum(2000 if int(self.function_combo.currentData()) in (1, 2) else 125)

    def _connection_config(self) -> dict[str, Any]:
        protocol = self.protocol_combo.currentText()
        config: dict[str, Any] = {
            "protocol": protocol,
            "unit_id": self.unit_id_input.value(),
            "function": int(self.function_combo.currentData()),
            "address": self.address_input.value(),
            "count": self.count_input.value(),
            "timeout": 1.2,
        }
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
            self.worker.disconnect_requested.emit()
            self._polling = False
            self.poll_button.setText("开始轮询")
            return
        try:
            self.worker.connect_requested.emit(self._connection_config())
        except ValueError as exc:
            QMessageBox.information(self, "连接参数", str(exc))

    def _read_once(self) -> None:
        try:
            self.worker.read_once_requested.emit(self._connection_config())
        except (ValueError, TypeError) as exc:
            QMessageBox.information(self, "读取参数", str(exc))

    def _toggle_polling(self) -> None:
        if self._polling:
            self.worker.stop_poll_requested.emit()
            self._polling = False
            self.poll_button.setText("开始轮询")
            self.poll_button.setObjectName("primaryButton")
        else:
            try:
                config = self._connection_config()
                self.worker.start_poll_requested.emit(config, self.interval_input.value())
                self._polling = True
                self.poll_button.setText("停止轮询")
                self.poll_button.setObjectName("writeButton")
            except (ValueError, TypeError) as exc:
                QMessageBox.information(self, "轮询参数", str(exc))
        self.poll_button.style().unpolish(self.poll_button)
        self.poll_button.style().polish(self.poll_button)

    def _on_connection_changed(self, success: bool, message: str) -> None:
        self._connected = success
        if not success and self._polling:
            self._polling = False
            self.poll_button.setText("开始轮询")
            self.poll_button.setObjectName("primaryButton")
            self.poll_button.style().unpolish(self.poll_button)
            self.poll_button.style().polish(self.poll_button)
        self.connect_button.setText("断开连接" if success else "连接设备")
        self.connect_button.setObjectName("writeButton" if success else "darkButton")
        self.connect_button.style().unpolish(self.connect_button)
        self.connect_button.style().polish(self.connect_button)
        self.read_once_button.setEnabled(success)
        self.poll_button.setEnabled(success)
        self.hero_status.setText(f"●  {message}" if success else f"○  {message}")
        self.stat_device_value.setText(message.split("·")[0].strip() if success else "未连接")
        self.stat_device_caption.setText("在线" if success else "等待连接")
        self._update_write_controls()

    def _on_data_received(self, result: dict[str, Any]) -> None:
        self._latest_values = result["values"]
        self._latest_address = result["address"]
        self._latest_function = result["function"]
        self._render_current_values()
        self.stat_data_value.setText(result["timestamp"])
        self.stat_data_caption.setText(f"FC{result['function']:02d} · {len(result['values'])} 项")
        self.stat_latency_value.setText(f"{result['latency_ms']:.1f} ms")
        self.stat_latency_caption.setText(f"Unit {result['unit_id']}")
        self.mascot_caption.setText("哈哈哈哈！")
        self.master_mascot.laugh()
        self.hero_mascot.laugh()
        self.audio.play()

    def _render_current_values(self, *_args) -> None:
        if not hasattr(self, "data_table"):
            return
        function = self._latest_function
        values = self._latest_values
        self.data_table.setRowCount(len(values))
        dtype = self.value_type_combo.currentData()
        word_order = self.word_order_combo.currentData()
        decoded = self._decode_registers(values, dtype, word_order) if function in (3, 4) else ["ON" if value else "OFF" for value in values]
        for index, value in enumerate(values):
            address = self._latest_address + index
            raw_text = str(value) if isinstance(value, bool) else str(int(value))
            hex_text = "—" if isinstance(value, bool) else f"0x{int(value):04X}"
            fields = [f"{address:05d}", "位" if function in (1, 2) else "寄存器", raw_text, hex_text, decoded[index]]
            for column, text in enumerate(fields):
                cell = QTableWidgetItem(text)
                if column in (0, 2, 3, 4):
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if column == 0:
                    cell.setForeground(QColor("#748078"))
                self.data_table.setItem(index, column, cell)

    @staticmethod
    def _decode_registers(values: list[int | bool], dtype: str, word_order: str) -> list[str]:
        result = ["—"] * len(values)
        if dtype in ("u16", "s16"):
            for i, raw in enumerate(values):
                value = int(raw)
                if dtype == "s16" and value >= 0x8000:
                    value -= 0x10000
                result[i] = str(value)
            return result
        for i in range(0, len(values) - 1, 2):
            first, second = int(values[i]), int(values[i + 1])
            words = (first, second) if word_order == "big" else (second, first)
            packed = struct.pack(">HH", *words)
            if dtype == "u32":
                decoded: str = str(struct.unpack(">I", packed)[0])
            elif dtype == "s32":
                decoded = str(struct.unpack(">i", packed)[0])
            else:
                decoded = f"{struct.unpack('>f', packed)[0]:.6g}"
            result[i] = decoded
            result[i + 1] = "(2/2)"
        return result

    def _set_sound_enabled(self, enabled: bool) -> None:
        self.audio.enabled = enabled
        self.settings.setValue("sound_enabled", enabled)

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

    def _write_value(self) -> None:
        if not self.write_enable.isChecked() or not self._connected:
            return
        function = int(self.write_function.currentData())
        raw = self.write_value.text().strip().lower()
        if function == 5:
            if raw not in {"0", "1", "false", "true", "off", "on"}:
                QMessageBox.information(self, "写入值", "线圈值请填写 0、1、OFF 或 ON。")
                return
            value: int | bool = raw in {"1", "true", "on"}
        else:
            try:
                value = int(raw, 0)
            except ValueError:
                QMessageBox.information(self, "写入值", "寄存器值需为 0 到 65535 的整数，可使用 0x 前缀。")
                return
            if not 0 <= value <= 65535:
                QMessageBox.information(self, "写入值", "寄存器值超出范围（0–65535）。")
                return
        address = self.write_address.value()
        shown = "ON" if value is True else ("OFF" if value is False else str(value))
        answer = QMessageBox.warning(
            self,
            "确认写入设备",
            f"即将向 Unit {self.unit_id_input.value()} 的地址 {address} 写入 {shown}。\n请再次核对设备和地址。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Yes:
            try:
                self.worker.write_requested.emit(self._connection_config(), function, address, value)
            except ValueError as exc:
                QMessageBox.information(self, "连接参数", str(exc))

    def _on_operation_finished(self, success: bool, message: str) -> None:
        if not success:
            self.stat_latency_value.setText("错误")
            self.stat_latency_caption.setText(message[:42])

    def _append_log(self, level: str, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        line = f"{timestamp}  {level:<5}  {message}"
        if hasattr(self, "log_view"):
            self.log_view.appendPlainText(line)
        self._records.append((timestamp, level, message))
        if len(self._records) > 2000:
            self._records = self._records[-1500:]

    def _export_log(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "导出通信记录", "naiwa_modbus_log.csv", "CSV 文件 (*.csv)")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.writer(stream)
            writer.writerow(["时间", "类型", "记录"])
            writer.writerows(self._records)
        self._append_log("INFO", f"日志已导出：{path}")

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
            simulator = TcpSimulatorThread(host, self.listen_port.value(), self.listen_unit.value())
        except Exception as exc:
            QMessageBox.critical(self, "从站模拟", f"无法创建模拟数据区：{exc}")
            return
        self._simulator = simulator
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
        for row, value in enumerate(values):
            self.sim_table.item(row, 1).setText(str(bool(value) if area in ("CO", "DI") else value))
        if self._simulator and self._simulator.isRunning():
            self._simulator.context.set_local_values(code, 0, values)

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
        for row in range(16):
            raw = self.sim_table.item(row, 1).text().strip().lower()
            if area in ("CO", "DI"):
                if raw not in {"0", "1", "true", "false", "on", "off"}:
                    QMessageBox.information(self, "模拟数据", f"地址 {row} 的位值请填写 0/1、ON/OFF。")
                    return
                values.append(raw in {"1", "true", "on"})
            else:
                try:
                    value = int(raw, 0)
                except ValueError:
                    QMessageBox.information(self, "模拟数据", f"地址 {row} 不是有效的 16 位整数。")
                    return
                if not 0 <= value <= 65535:
                    QMessageBox.information(self, "模拟数据", f"地址 {row} 的值需在 0–65535 范围内。")
                    return
                values.append(value)
        if self._simulator and self._simulator.isRunning():
            self._simulator.context.set_local_values(code, 0, values)
        self._sim_values[code] = list(values)
        self._append_log("SERVER", f"已应用 {area} 地址 0–15 的模拟数据")

    def _load_sim_values(self, *_args) -> None:
        simulator = self._simulator
        code, area = self._current_sim_area()
        values = self._sim_values[code]
        if simulator and simulator.isRunning():
            try:
                values = simulator.context.get_local_values(code, 0, 16)
                self._sim_values[code] = list(values)
            except Exception as exc:
                self._append_log("ERR", f"读取模拟数据失败：{exc}")
        for row, value in enumerate(values):
            display = str(bool(value)) if area in ("CO", "DI") else str(int(value))
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

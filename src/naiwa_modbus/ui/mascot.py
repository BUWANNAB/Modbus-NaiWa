from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QWidget

from naiwa_modbus.services.audio import resource_path


class MascotWidget(QWidget):
    """Animated Douyin Naiwa character using the repository's sprite frames."""

    ACTIONS = (
        ("待机摇晃", "idle"),
        ("收到数据 · 大笑", "laugh"),
        ("连接成功 · 挥手", "wave"),
        ("写入成功 · 打拳", "punch"),
        ("睡觉", "sleep"),
        ("八卦", "gossip"),
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(44, 60)
        self.setMaximumSize(156, 132)
        self.setStyleSheet("background: transparent;")
        self.setToolTip("右键切换奶蛙动作")
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_action_menu)

        self._frames = {
            action: self._load_frames(action)
            for _, action in self.ACTIONS
        }
        self._action = "idle"
        self._frame_index = 0
        self._loop_action = True
        self._timer = QTimer(self)
        self._timer.setInterval(95)
        self._timer.timeout.connect(self._advance_frame)
        self.play_action("idle")

    @staticmethod
    def _load_frames(action: str) -> list[QPixmap]:
        folder = resource_path(f"assets/mascot/{action}")
        return [
            pixmap
            for path in sorted(Path(folder).glob("*.png"))
            if not (pixmap := QPixmap(str(path))).isNull()
        ]

    def play_action(self, action: str, *, loop: bool | None = None) -> None:
        frames = self._frames.get(action)
        if not frames:
            return
        self._action = action
        self._frame_index = 0
        self._loop_action = action == "idle" if loop is None else loop
        if len(frames) > 1:
            self._timer.start()
        else:
            self._timer.stop()
        self.update()

    def laugh(self) -> None:
        self.play_action("laugh")

    def wave(self) -> None:
        self.play_action("wave")

    def punch(self) -> None:
        self.play_action("punch")

    def _advance_frame(self) -> None:
        frames = self._frames[self._action]
        if self._frame_index + 1 < len(frames):
            self._frame_index += 1
        elif self._loop_action:
            self._frame_index = 0
        else:
            self.play_action("idle")
            return
        self.update()

    def _show_action_menu(self, position) -> None:
        menu = QMenu(self)
        for label, action in self.ACTIONS:
            item = menu.addAction(label)
            item.triggered.connect(lambda _checked=False, value=action: self.play_action(value))
        menu.exec(self.mapToGlobal(position))

    def paintEvent(self, _event) -> None:  # noqa: N802 - Qt event naming.
        frames = self._frames[self._action]
        if not frames:
            return
        pixmap = frames[self._frame_index]
        scaled = pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawPixmap(x, y, scaled)

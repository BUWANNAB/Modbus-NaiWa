from __future__ import annotations

import math
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class MascotWidget(QWidget):
    """Original vector mascot: round milk body, frog eyes, and a big meme grin."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(112, 104)
        self.setMaximumSize(156, 132)
        self._laugh_until = 0.0
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(45)
        self._timer.timeout.connect(self._animate)

    def laugh(self) -> None:
        self._laugh_until = time.monotonic() + 1.25
        if not self._timer.isActive():
            self._timer.start()
        self.update()

    def _animate(self) -> None:
        self._phase += 0.34
        if time.monotonic() >= self._laugh_until:
            self._timer.stop()
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802 - Qt event naming.
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        active = time.monotonic() < self._laugh_until
        painter.save()
        if active:
            painter.translate(math.sin(self._phase) * 2.2, abs(math.cos(self._phase * 1.2)) * 1.5)

        # Tiny shadow anchors the character without turning it into a sticker.
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#d9dfce"))
        painter.drawEllipse(int(w * .21), int(h * .83), int(w * .58), int(h * .10))

        # Slim frog arms and legs.
        limb_pen = QPen(QColor("#91ad5e"), max(3, int(w * .035)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(limb_pen)
        painter.drawLine(int(w * .30), int(h * .66), int(w * .15), int(h * .78))
        painter.drawLine(int(w * .70), int(h * .66), int(w * .85), int(h * .77))
        painter.drawLine(int(w * .39), int(h * .78), int(w * .31), int(h * .86))
        painter.drawLine(int(w * .61), int(h * .78), int(w * .69), int(h * .86))

        # Round milk-colored body.
        body = QPainterPath()
        body.moveTo(w * .50, h * .29)
        body.cubicTo(w * .80, h * .27, w * .87, h * .45, w * .82, h * .68)
        body.cubicTo(w * .78, h * .84, w * .64, h * .85, w * .49, h * .84)
        body.cubicTo(w * .31, h * .85, w * .17, h * .79, w * .16, h * .62)
        body.cubicTo(w * .14, h * .42, w * .24, h * .30, w * .50, h * .29)
        painter.setPen(QPen(QColor("#d8cda9"), 1.3))
        painter.setBrush(QColor("#f1e4bf"))
        painter.drawPath(body)

        # Big green frog eye caps and wide, dark pupils.
        painter.setPen(QPen(QColor("#557947"), 1.2))
        painter.setBrush(QColor("#9dc45c"))
        painter.drawEllipse(int(w * .25), int(h * .13), int(w * .24), int(h * .31))
        painter.drawEllipse(int(w * .51), int(h * .13), int(w * .24), int(h * .31))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#fdfdf4"))
        painter.drawEllipse(int(w * .30), int(h * .19), int(w * .15), int(h * .18))
        painter.drawEllipse(int(w * .55), int(h * .19), int(w * .15), int(h * .18))
        painter.setBrush(QColor("#18362e"))
        painter.drawEllipse(int(w * .355), int(h * .235), int(w * .073), int(h * .105))
        painter.drawEllipse(int(w * .575), int(h * .235), int(w * .073), int(h * .105))
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(int(w * .37), int(h * .25), int(w * .023), int(h * .032))
        painter.drawEllipse(int(w * .59), int(h * .25), int(w * .023), int(h * .032))

        # The wide, slightly crooked laugh is the signature expression.
        mouth = QPainterPath()
        if active:
            mouth.moveTo(w * .35, h * .53)
            mouth.cubicTo(w * .40, h * .70, w * .63, h * .70, w * .68, h * .52)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#244037"))
            painter.drawPath(mouth)
            painter.setBrush(QColor("#d98268"))
            painter.drawEllipse(int(w * .43), int(h * .62), int(w * .17), int(h * .055))
        else:
            mouth.moveTo(w * .37, h * .57)
            mouth.cubicTo(w * .46, h * .65, w * .57, h * .64, w * .65, h * .55)
            painter.setPen(QPen(QColor("#5a5545"), max(2, int(w * .025)), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(mouth)

        painter.restore()

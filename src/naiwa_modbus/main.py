from __future__ import annotations

import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from naiwa_modbus.ui.main_window import MainWindow
from naiwa_modbus.ui.theme import APP_STYLE


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("奶蛙 Modbus 数据站")
    app.setOrganizationName("BUWANNAB")
    app.setFont(QFont("Microsoft YaHei UI", 9))
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLE)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

APP_STYLE = """
QWidget {
    color: #19382f;
    background: #f1efe5;
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 13px;
}
QFrame#hero {
    background: #17392f;
    border: 1px solid #21493d;
    border-radius: 18px;
}
QLabel#brandTitle { color: #fffaf0; font-size: 23px; font-weight: 800; }
QLabel#brandEyebrow { color: #b8d289; font-size: 10px; font-weight: 700; letter-spacing: 2px; }
QLabel#heroSub { color: #c7d4c8; font-size: 12px; }
QLabel#heroBadge {
    color: #eaf4d2;
    background: #295644;
    border: 1px solid #4b745d;
    border-radius: 11px;
    padding: 7px 11px;
    font-weight: 700;
}
QFrame#card {
    background: #fffdf7;
    border: 1px solid #deddd1;
    border-radius: 15px;
}
QLabel#sectionTitle { color: #19382f; font-size: 15px; font-weight: 800; }
QLabel#muted { color: #75847a; }
QLabel#statusValue { color: #19382f; font-size: 22px; font-weight: 800; }
QLabel#statusCaption { color: #718077; font-size: 11px; }
QLabel#pill {
    color: #426247;
    background: #e9efd9;
    border-radius: 9px;
    padding: 5px 9px;
    font-size: 11px;
    font-weight: 700;
}
QLabel#pillOn, QLabel#pillOff, QLabel#pillError {
    border-radius: 9px; padding: 5px 9px; font-size: 11px; font-weight: 700;
}
QLabel#pillOn { color: #21472f; background: #d6e8a6; }
QLabel#pillOff { color: #61716a; background: #e9e8df; }
QLabel#pillError { color: #963f2f; background: #f5ded6; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background: #fffefa;
    color: #19382f;
    border: 1px solid #d2d5c8;
    border-radius: 8px;
    padding: 7px 9px;
    selection-background-color: #9bb95c;
    min-height: 18px;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #719b48;
}
QComboBox::drop-down { border: 0; width: 24px; }
QComboBox QAbstractItemView {
    background: #fffefa;
    border: 1px solid #d2d5c8;
    selection-background-color: #e5edcf;
    color: #19382f;
}
QPushButton {
    color: #2c4b3b;
    background: #e7e8dc;
    border: 1px solid #d2d7c6;
    border-radius: 9px;
    padding: 8px 13px;
    font-weight: 700;
}
QPushButton:hover { background: #dfe7ce; border-color: #b7c79a; }
QPushButton:pressed { background: #d1ddba; }
QPushButton:disabled { color: #a5aaa0; background: #ecebe4; border-color: #e0dfd7; }
QPushButton#primaryButton {
    color: #17392f;
    background: #a9ce63;
    border: 1px solid #9abe58;
}
QPushButton#primaryButton:hover { background: #b8d977; }
QPushButton#darkButton {
    color: #f8f7ed;
    background: #254b3e;
    border: 1px solid #315c4b;
}
QPushButton#darkButton:hover { background: #30614e; }
QPushButton#writeButton {
    color: #8c4431;
    background: #f7ebe5;
    border: 1px solid #e9c8bc;
}
QPushButton#writeButton:hover { background: #f3ded4; }
QCheckBox { spacing: 8px; color: #334e42; }
QCheckBox::indicator {
    width: 16px; height: 16px; border-radius: 5px;
    border: 1px solid #bdc8b5; background: #fffefa;
}
QCheckBox::indicator:checked { background: #a9ce63; border-color: #89ab4c; }
QTableWidget {
    color: #1d3a31;
    background: #fffefa;
    alternate-background-color: #f7f6ee;
    border: 1px solid #e2e1d7;
    border-radius: 10px;
    gridline-color: #efeee7;
    selection-background-color: #e7edda;
    selection-color: #18382e;
}
QHeaderView::section {
    color: #66796c;
    background: #f4f3eb;
    border: 0;
    border-bottom: 1px solid #e4e3d9;
    padding: 8px 7px;
    font-size: 11px;
    font-weight: 800;
}
QPlainTextEdit {
    color: #d8e2d4;
    background: #1d302a;
    border: 1px solid #2c4238;
    border-radius: 10px;
    padding: 7px;
    font-family: Consolas, "Cascadia Mono", monospace;
    font-size: 11px;
}
QSplitter::handle { background: #e2e0d6; width: 1px; }
QScrollBar:vertical { width: 10px; background: transparent; margin: 2px; }
QScrollBar::handle:vertical { background: #cbd2c2; border-radius: 4px; min-height: 24px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QToolTip { color: #fffdf7; background: #24453a; border: 0; padding: 5px 7px; }
"""

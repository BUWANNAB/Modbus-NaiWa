APP_STYLE = """
QWidget {
    color: #4d5247;
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 13px;
}
QMainWindow, QWidget#root, QWidget#mainPage { background: #f5f3eb; }
QStackedWidget, QScrollArea { background: transparent; border: 0; }
QFrame#hero {
    background: #eee7d2;
    border: 1px solid #e4dcc4;
    border-radius: 18px;
}
QLabel#brandTitle { color: #514d40; font-size: 23px; font-weight: 800; }
QLabel#brandEyebrow { color: #8c805d; font-size: 10px; font-weight: 700; letter-spacing: 2px; }
QLabel#heroSub { color: #777563; font-size: 12px; }
QLabel#heroBadge {
    color: #687052;
    background: #f8f5e9;
    border: 1px solid #ded7c2;
    border-radius: 11px;
    padding: 7px 11px;
    font-weight: 700;
}
QFrame#card {
    background: #fffefa;
    border: 1px solid #e8e4d8;
    border-radius: 15px;
}
QLabel#sectionTitle { color: #53574b; font-size: 15px; font-weight: 800; }
QLabel#muted { color: #898a7d; }
QLabel#statusValue { color: #565b4d; font-size: 22px; font-weight: 800; }
QLabel#statusCaption { color: #8a8a7c; font-size: 11px; }
QLabel#pill {
    color: #73775f;
    background: #f0efdf;
    border-radius: 9px;
    padding: 5px 9px;
    font-size: 11px;
    font-weight: 700;
}
QLabel#pillOn, QLabel#pillOff, QLabel#pillError {
    border-radius: 9px; padding: 5px 9px; font-size: 11px; font-weight: 700;
}
QLabel#pillOn { color: #657452; background: #e8eedc; }
QLabel#pillOff { color: #85867b; background: #efeee8; }
QLabel#pillError { color: #a46754; background: #f5e8e1; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background: #fffefb;
    color: #4d5247;
    border: 1px solid #deddd2;
    border-radius: 8px;
    padding: 7px 9px;
    selection-background-color: #dce4c7;
    min-height: 18px;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #a8ad84;
}
QComboBox::drop-down { border: 0; width: 24px; }
QComboBox QAbstractItemView {
    background: #fffefb;
    border: 1px solid #deddd2;
    selection-background-color: #e9ecd9;
    color: #4d5247;
}
QPushButton {
    color: #666a5a;
    background: #f0eee5;
    border: 1px solid #e2dfd2;
    border-radius: 9px;
    padding: 8px 13px;
    font-weight: 700;
}
QPushButton:hover { background: #e9e7dc; border-color: #d5d2c2; }
QPushButton:pressed { background: #e1e2d4; }
QPushButton:disabled { color: #aaa99f; background: #f1f0eb; border-color: #e8e6df; }
QPushButton#primaryButton {
    color: #5c5438;
    background: #f0e2b5;
    border: 1px solid #e4d59f;
}
QPushButton#primaryButton:hover { background: #ecdda9; }
QPushButton#darkButton {
    color: #f8f6ec;
    background: #858b70;
    border: 1px solid #7d846a;
}
QPushButton#darkButton:hover { background: #787f66; }
QPushButton#writeButton {
    color: #94614f;
    background: #f4e7df;
    border: 1px solid #ead5c9;
}
QPushButton#writeButton:hover { background: #eedfd6; }
QCheckBox { spacing: 8px; color: #636858; }
QCheckBox::indicator {
    width: 16px; height: 16px; border-radius: 5px;
    border: 1px solid #d3d1c4; background: #fffefa;
}
QCheckBox::indicator:checked { background: #dce4c7; border-color: #b8c39c; }
QTableWidget {
    color: #555b50;
    background: #fffefa;
    alternate-background-color: #faf8f1;
    border: 1px solid #e9e6dc;
    border-radius: 10px;
    gridline-color: #f0eee7;
    selection-background-color: #e9ecd9;
    selection-color: #4e5845;
}
QHeaderView::section {
    color: #818274;
    background: #f7f5ed;
    border: 0;
    border-bottom: 1px solid #ebe8df;
    padding: 8px 7px;
    font-size: 11px;
    font-weight: 800;
}
QPlainTextEdit {
    color: #626858;
    background: #f5f3eb;
    border: 1px solid #e4e1d6;
    border-radius: 10px;
    padding: 7px;
    font-family: Consolas, "Cascadia Mono", monospace;
    font-size: 11px;
}
QSplitter::handle { background: #e9e6dc; width: 1px; }
QScrollBar:vertical { width: 10px; background: transparent; margin: 2px; }
QScrollBar::handle:vertical { background: #d8d7ca; border-radius: 4px; min-height: 24px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QToolTip { color: #5e604f; background: #f8f5e9; border: 1px solid #e4dfcf; padding: 5px 7px; }
"""

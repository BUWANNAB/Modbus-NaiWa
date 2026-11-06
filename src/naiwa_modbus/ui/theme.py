APP_STYLE = """
QWidget {
    color: #403B35;
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 12px;
}
QMainWindow { background: #F2EFE8; }
QMenuBar {
    color: #403B35;
    background: #F8F6F0;
    border-bottom: 1px solid #D9D4CA;
    padding: 3px 4px;
}
QMenuBar::item { padding: 5px 9px; background: transparent; }
QMenuBar::item:selected { background: #EEE7D6; border-radius: 4px; }
QMenu {
    color: #403B35;
    background: #FFFEFA;
    border: 1px solid #D8D2C7;
    padding: 4px;
}
QMenu::item { padding: 6px 26px 6px 22px; }
QMenu::item:selected { color: #403B35; background: #F2E5BD; }
QToolBar {
    spacing: 5px;
    padding: 5px 7px;
    background: #F8F6F0;
    border: 0;
    border-bottom: 1px solid #D9D4CA;
}
QToolBar::separator { width: 1px; margin: 3px 5px; background: #D8D2C7; }
QToolBar QToolButton {
    color: #4B443C;
    background: transparent;
    border: 1px solid transparent;
    border-radius: 5px;
    padding: 6px 9px;
    font-weight: 650;
}
QToolBar QToolButton:hover { background: #EEE9DF; border-color: #DCD5C8; }
QToolBar QToolButton:pressed { background: #E5DCCB; }
QDockWidget {
    color: #403B35;
    font-weight: 700;
    titlebar-close-icon: none;
    titlebar-normal-icon: none;
}
QDockWidget::title {
    text-align: left;
    background: #E8E2D7;
    padding: 8px 10px;
    border: 1px solid #D2CCC1;
}
QDockWidget QWidget#mainPage { background: #F2EFE8; }
QDockWidget::close-button, QDockWidget::float-button { width: 16px; height: 16px; }
QMdiArea { background: #D7D3CB; }
QMdiSubWindow {
    background: #FFFEFA;
    border: 1px solid #AFA99F;
}
QMdiSubWindow::title { background: #E8C66B; color: #443A29; }
QFrame#hero {
    background: #EEE7D8;
    border: 1px solid #DED5C5;
    border-radius: 10px;
}
QLabel#brandTitle { color: #453F37; font-size: 22px; font-weight: 800; }
QLabel#brandEyebrow { color: #8A7552; font-size: 10px; font-weight: 700; letter-spacing: 2px; }
QLabel#heroSub { color: #797166; font-size: 12px; }
QLabel#heroBadge {
    color: #6E5630;
    background: #F8F1DE;
    border: 1px solid #E4D5AF;
    border-radius: 8px;
    padding: 6px 10px;
    font-weight: 700;
}
QFrame#card {
    background: #FFFEFA;
    border: 1px solid #E2DED5;
    border-radius: 8px;
}
QFrame#statusStrip {
    background: #FFFEFA;
    border-bottom: 1px solid #D9D4CA;
}
QLabel#protocolStatus {
    color: #514A42;
    font-family: Consolas, "Cascadia Mono", monospace;
    font-size: 12px;
    font-weight: 700;
}
QTableWidget#pollDataTable {
    font-family: "Segoe UI", "Microsoft YaHei UI", sans-serif;
    font-size: 13px;
}
QFrame#dataView { background: #FFFEFA; }
QFrame#mascotStatus {
    background: #F8F2E3;
    border: 1px solid #E8DDBF;
    border-radius: 5px;
}
QLabel#sectionTitle { color: #4D463E; font-size: 14px; font-weight: 750; }
QLabel#muted { color: #847C71; }
QLabel#statusValue { color: #4B443C; font-size: 20px; font-weight: 800; }
QLabel#statusCaption { color: #81796F; font-size: 11px; }
QLabel#statusCompactValue { color: #4B443C; font-size: 13px; font-weight: 750; }
QLabel#pill {
    color: #675638;
    background: #F3ECD9;
    border-radius: 6px;
    padding: 5px 8px;
    font-size: 11px;
    font-weight: 700;
}
QLabel#pillOn, QLabel#pillOff, QLabel#pillError {
    border-radius: 6px; padding: 5px 8px; font-size: 11px; font-weight: 700;
}
QLabel#pillOn { color: #76571F; background: #F5EACB; }
QLabel#pillOff { color: #756F66; background: #ECEAE5; }
QLabel#pillError { color: #A14E41; background: #F6E6E0; }
QLabel#connectionStatusOn {
    color: #7C5822;
    background: #F7ECCD;
    border: 1px solid #E8D8AE;
    border-radius: 5px;
    padding: 4px 7px;
    font-family: Consolas, "Microsoft YaHei UI", monospace;
    font-weight: 700;
}
QLabel#connectionStatusOff {
    color: #A44F43;
    background: #F7E8E3;
    border: 1px solid #EED3CA;
    border-radius: 5px;
    padding: 4px 7px;
    font-family: Consolas, "Microsoft YaHei UI", monospace;
    font-weight: 700;
}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background: #FFFEFB;
    color: #403B35;
    border: 1px solid #D8D3C9;
    border-radius: 5px;
    padding: 6px 8px;
    selection-background-color: #EBD89B;
    min-height: 18px;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #C7A94E;
}
QComboBox::drop-down { border: 0; width: 22px; }
QComboBox QAbstractItemView {
    background: #FFFEFB;
    border: 1px solid #D8D3C9;
    selection-background-color: #F2E5BD;
    color: #403B35;
}
QPushButton {
    color: #514A42;
    background: #F1EEE8;
    border: 1px solid #D9D4CA;
    border-radius: 6px;
    padding: 7px 11px;
    font-weight: 650;
}
QPushButton:hover { background: #EAE5DB; border-color: #CEC7BA; }
QPushButton:pressed { background: #E0D9CD; }
QPushButton:disabled { color: #AAA49A; background: #F2F0EB; border-color: #E7E3DB; }
QPushButton#primaryButton, QPushButton#modeButtonActive {
    color: #483B20;
    background: #E9CB72;
    border: 1px solid #D8B95A;
}
QPushButton#primaryButton:hover, QPushButton#modeButtonActive:hover { background: #E3C15F; }
QPushButton#darkButton {
    color: #FFFCF4;
    background: #65594C;
    border: 1px solid #574C40;
}
QPushButton#darkButton:hover { background: #574C40; }
QPushButton#writeButton {
    color: #8E483A;
    background: #F5E5DE;
    border: 1px solid #E7CFC4;
}
QPushButton#writeButton:hover { background: #EFD9D0; }
QCheckBox { spacing: 7px; color: #514A42; }
QCheckBox::indicator {
    width: 15px; height: 15px; border-radius: 3px;
    border: 1px solid #CBC5BA; background: #FFFEFA;
}
QCheckBox::indicator:checked { background: #E8C66B; border-color: #CCAD55; }
QTableWidget {
    color: #49433C;
    background: #FFFEFA;
    alternate-background-color: #F8F6F0;
    border: 1px solid #DEDAD1;
    gridline-color: #EAE6DE;
    selection-background-color: #F2E5BD;
    selection-color: #3F382E;
}
QHeaderView::section {
    color: #70685D;
    background: #F0EDE6;
    border: 0;
    border-right: 1px solid #E1DCD2;
    border-bottom: 1px solid #DCD7CD;
    padding: 7px 7px;
    font-size: 11px;
    font-weight: 750;
}
QPlainTextEdit {
    color: #514B43;
    background: #F8F6F0;
    border: 1px solid #DEDAD1;
    border-radius: 5px;
    padding: 6px;
    font-family: Consolas, "Cascadia Mono", monospace;
    font-size: 11px;
}
QSplitter::handle { background: #D8D3CA; width: 1px; }
QScrollBar:vertical { width: 10px; background: transparent; margin: 2px; }
QScrollBar::handle:vertical { background: #CCC6BA; border-radius: 4px; min-height: 24px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QStatusBar { color: #6F675D; background: #F4F1EA; border-top: 1px solid #D9D4CA; }
QToolTip { color: #49433C; background: #FFF9E9; border: 1px solid #D8CBAA; padding: 5px 7px; }
"""

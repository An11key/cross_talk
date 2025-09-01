"""CSS стили для приложения Cross Talk."""

DARK_THEME = """
QMainWindow {
    background-color: #2b2b2b;
    color: #ffffff;
}
QWidget {
    background-color: #2b2b2b;
    color: #ffffff;
}
QListWidget {
    background-color: #3c3c3c;
    color: #ffffff;
    border: 1px solid #555555;
    selection-background-color: #094771;
}
QListWidget::item {
    padding: 5px;
    border-bottom: 1px solid #555555;
}
QListWidget::item:hover {
    background-color: #404040;
}
QListWidget::item:selected {
    background-color: #094771;
}
QTabWidget::pane {
    border: 1px solid #555555;
    background-color: #3c3c3c;
}
QTabBar::tab {
    background-color: #404040;
    color: #ffffff;
    padding: 8px 16px;
    margin-right: 2px;
    border: 1px solid #555555;
    border-bottom: none;
}
QTabBar::tab:selected {
    background-color: #094771;
}
QTabBar::tab:hover {
    background-color: #505050;
}
QMenuBar {
    background-color: #2b2b2b;
    color: #ffffff;
    border-bottom: 1px solid #555555;
}
QMenuBar::item {
    background-color: transparent;
    padding: 6px 12px;
}
QMenuBar::item:selected {
    background-color: #404040;
}
QMenu {
    background-color: #3c3c3c;
    color: #ffffff;
    border: 1px solid #555555;
}
QMenu::item {
    padding: 6px 20px;
}
QMenu::item:selected {
    background-color: #094771;
}
QSplitter::handle {
    background-color: #555555;
}
QSplitter::handle:horizontal {
    width: 3px;
}
QSplitter::handle:vertical {
    height: 3px;
}
"""

LIGHT_THEME = """
QMainWindow {
    background-color: #f0f0f0;
    color: #000000;
}
QWidget {
    background-color: #f0f0f0;
    color: #000000;
}
QListWidget {
    background-color: #ffffff;
    color: #000000;
    border: 1px solid #cccccc;
    selection-background-color: #0078d4;
}
QListWidget::item {
    padding: 5px;
    border-bottom: 1px solid #e0e0e0;
}
QListWidget::item:hover {
    background-color: #f5f5f5;
}
QListWidget::item:selected {
    background-color: #0078d4;
    color: #ffffff;
}
QTabWidget::pane {
    border: 1px solid #cccccc;
    background-color: #ffffff;
}
QTabBar::tab {
    background-color: #e8e8e8;
    color: #000000;
    padding: 8px 16px;
    margin-right: 2px;
    border: 1px solid #cccccc;
    border-bottom: none;
}
QTabBar::tab:selected {
    background-color: #0078d4;
    color: #ffffff;
}
QTabBar::tab:hover {
    background-color: #d0d0d0;
}
QMenuBar {
    background-color: #f0f0f0;
    color: #000000;
    border-bottom: 1px solid #cccccc;
}
QMenuBar::item {
    background-color: transparent;
    padding: 6px 12px;
}
QMenuBar::item:selected {
    background-color: #e0e0e0;
}
QMenu {
    background-color: #ffffff;
    color: #000000;
    border: 1px solid #cccccc;
}
QMenu::item {
    padding: 6px 20px;
}
QMenu::item:selected {
    background-color: #0078d4;
    color: #ffffff;
}
QSplitter::handle {
    background-color: #cccccc;
}
QSplitter::handle:horizontal {
    width: 3px;
}
QSplitter::handle:vertical {
    height: 3px;
}
"""

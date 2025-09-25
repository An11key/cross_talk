import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PySide6.QtWidgets import QApplication
from app.ui.main_window import MyMenu


def main() -> None:
    app = QApplication(sys.argv)
    menu = MyMenu()
    menu.show()
    app.exec()


if __name__ == "__main__":
    main()

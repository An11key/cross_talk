"""
Виджет для отображения матрицы кросс-помех.

Отображает матрицу перекрестных помех 4x4 в виде таблицы
с форматированными значениями и заголовками каналов.
Поддерживает отображение двух матриц для .srd файлов.
"""

import numpy as np
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QLabel,
    QHeaderView,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class MatrixWidget(QWidget):
    """Виджет для отображения матрицы кросс-помех."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.current_matrix = None
        self.original_matrix = None
        self.is_dark_theme = False

        self._init_ui()

    def _init_ui(self):
        """Инициализация пользовательского интерфейса."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Заголовок
        self.title_label = QLabel("Матрица кросс-помех (Crosstalk Matrix)")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)

        # Описание
        self.description_label = QLabel(
            "W[i,j] показывает влияние канала j на канал i\n"
            "Сумма по каждому столбцу = 1.0"
        )
        self.description_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.description_label)

        # Контейнер для матриц (горизонтальное расположение)
        matrices_container = QWidget()
        matrices_layout = QHBoxLayout(matrices_container)
        matrices_layout.setContentsMargins(0, 0, 0, 0)

        # Левая часть - вычисленная матрица
        computed_container = QWidget()
        computed_layout = QVBoxLayout(computed_container)
        computed_layout.setContentsMargins(0, 0, 0, 0)

        self.computed_title = QLabel("Вычисленная матрица")
        computed_title_font = QFont()
        computed_title_font.setBold(True)
        self.computed_title.setFont(computed_title_font)
        self.computed_title.setAlignment(Qt.AlignCenter)
        computed_layout.addWidget(self.computed_title)

        # Таблица для вычисленной матрицы
        self.table = QTableWidget()
        self.table.setRowCount(4)
        self.table.setColumnCount(4)

        # Устанавливаем заголовки
        channel_names = ["A", "G", "C", "T"]
        self.table.setHorizontalHeaderLabels(channel_names)
        self.table.setVerticalHeaderLabels(channel_names)

        # Настройка внешнего вида таблицы
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(
            QTableWidget.NoEditTriggers
        )  # Запрещаем редактирование
        self.table.setSelectionMode(QTableWidget.NoSelection)  # Отключаем выделение

        computed_layout.addWidget(self.table)

        # Дополнительная информация для вычисленной матрицы
        self.info_label = QLabel("Нет данных")
        self.info_label.setAlignment(Qt.AlignCenter)
        computed_layout.addWidget(self.info_label)

        matrices_layout.addWidget(computed_container)

        # Правая часть - оригинальная матрица (для .srd файлов)
        self.original_container = QWidget()
        original_layout = QVBoxLayout(self.original_container)
        original_layout.setContentsMargins(0, 0, 0, 0)

        self.original_title = QLabel("Оригинальная матрица (.srd)")
        original_title_font = QFont()
        original_title_font.setBold(True)
        self.original_title.setFont(original_title_font)
        self.original_title.setAlignment(Qt.AlignCenter)
        original_layout.addWidget(self.original_title)

        # Таблица для оригинальной матрицы
        self.original_table = QTableWidget()
        self.original_table.setRowCount(4)
        self.original_table.setColumnCount(4)

        self.original_table.setHorizontalHeaderLabels(channel_names)
        self.original_table.setVerticalHeaderLabels(channel_names)

        self.original_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.original_table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.original_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.original_table.setSelectionMode(QTableWidget.NoSelection)

        original_layout.addWidget(self.original_table)

        # Дополнительная информация для оригинальной матрицы
        self.original_info_label = QLabel("Нет данных")
        self.original_info_label.setAlignment(Qt.AlignCenter)
        original_layout.addWidget(self.original_info_label)

        matrices_layout.addWidget(self.original_container)

        # Скрываем оригинальную матрицу по умолчанию
        self.original_container.hide()

        layout.addWidget(matrices_container)

    def set_matrix(self, matrix: np.ndarray, original_matrix: np.ndarray = None):
        """
        Устанавливает матрицу для отображения.

        Args:
            matrix: Вычисленная матрица кросс-помех 4x4
            original_matrix: Оригинальная матрица из .srd файла (опционально)
        """
        if matrix is None or matrix.shape != (4, 4):
            self.info_label.setText("Ошибка: неверный размер матрицы")
            return

        self.current_matrix = matrix
        self.original_matrix = original_matrix

        # Заполняем таблицу вычисленной матрицы
        self._fill_table(self.table, matrix)

        # Обновляем информацию для вычисленной матрицы
        self.info_label.setText(
            f"Определитель: {np.linalg.det(matrix):.6f} | "
            f"След: {np.trace(matrix):.6f}"
        )

        # Если есть оригинальная матрица, показываем и заполняем её
        if original_matrix is not None and original_matrix.shape == (4, 4):
            self.original_container.show()
            self._fill_table(self.original_table, original_matrix)
            self.original_info_label.setText(
                f"Определитель: {np.linalg.det(original_matrix):.6f} | "
                f"След: {np.trace(original_matrix):.6f}"
            )
        else:
            self.original_container.hide()

    def _fill_table(self, table: QTableWidget, matrix: np.ndarray):
        """
        Заполняет таблицу значениями матрицы.

        Args:
            table: Таблица для заполнения
            matrix: Матрица 4x4 с данными
        """
        for i in range(4):
            for j in range(4):
                value = matrix[i, j]
                item = QTableWidgetItem(f"{value:.6f}")

                # Выделяем диагональные элементы жирным шрифтом
                if i == j:
                    font = QFont()
                    font.setBold(True)
                    item.setFont(font)

                # Центрируем текст
                item.setTextAlignment(Qt.AlignCenter)

                table.setItem(i, j, item)

    def clear(self):
        """Очищает виджет."""
        self.current_matrix = None
        self.original_matrix = None

        # Очищаем вычисленную матрицу
        for i in range(4):
            for j in range(4):
                self.table.setItem(i, j, QTableWidgetItem(""))
                self.original_table.setItem(i, j, QTableWidgetItem(""))

        self.info_label.setText("Нет данных")
        self.original_info_label.setText("Нет данных")
        self.original_container.hide()

    def apply_theme(self, theme: str):
        """
        Применяет тему оформления к виджету.

        Args:
            theme: "dark" или "white"
        """
        self.is_dark_theme = theme == "dark"

        if theme == "dark":
            # Тёмная тема
            self.setStyleSheet(
                """
                QWidget {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QTableWidget {
                    background-color: #353535;
                    color: #ffffff;
                    gridline-color: #555555;
                    border: 1px solid #555555;
                }
                QTableWidget::item {
                    padding: 5px;
                }
                QHeaderView::section {
                    background-color: #404040;
                    color: #ffffff;
                    padding: 5px;
                    border: 1px solid #555555;
                    font-weight: bold;
                }
                QLabel {
                    color: #ffffff;
                }
            """
            )
        else:
            # Светлая тема
            self.setStyleSheet(
                """
                QWidget {
                    background-color: #ffffff;
                    color: #000000;
                }
                QTableWidget {
                    background-color: #ffffff;
                    color: #000000;
                    gridline-color: #d0d0d0;
                    border: 1px solid #d0d0d0;
                }
                QTableWidget::item {
                    padding: 5px;
                }
                QHeaderView::section {
                    background-color: #f0f0f0;
                    color: #000000;
                    padding: 5px;
                    border: 1px solid #d0d0d0;
                    font-weight: bold;
                }
                QLabel {
                    color: #000000;
                }
            """
            )

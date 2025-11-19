"""
Виджет для отображения информации о последовательности.

Показывает различные параметры и характеристики последовательности:
- Количество точек данных
- Реагенты (красители)
- Разницу между матрицами после обработки
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QGroupBox,
    QScrollArea,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class SequenceInfoWidget(QWidget):
    """Виджет для отображения информации о последовательности."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.is_dark_theme = False

        self._init_ui()

    def _init_ui(self):
        """Инициализация пользовательского интерфейса."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Создаем область прокрутки
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Основной виджет для содержимого
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(5, 5, 5, 5)
        content_layout.setSpacing(15)

        # Заголовок
        self.title_label = QLabel("Информация о последовательности")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(self.title_label)

        # Группа: Основная информация
        basic_info_group = QGroupBox("Основная информация")
        basic_info_layout = QVBoxLayout()

        self.file_name_label = QLabel("Файл: не загружен")
        self.file_name_label.setWordWrap(True)
        basic_info_layout.addWidget(self.file_name_label)

        self.data_points_label = QLabel("Количество точек: —")
        basic_info_layout.addWidget(self.data_points_label)

        basic_info_group.setLayout(basic_info_layout)
        content_layout.addWidget(basic_info_group)

        # Группа: Реагенты (красители)
        dyes_group = QGroupBox("Реагенты (красители)")
        dyes_layout = QVBoxLayout()

        self.dyes_label = QLabel("Информация недоступна")
        self.dyes_label.setWordWrap(True)
        dyes_layout.addWidget(self.dyes_label)

        dyes_group.setLayout(dyes_layout)
        content_layout.addWidget(dyes_group)

        # Группа: Результаты обработки
        self.processing_group = QGroupBox("Результаты обработки")
        processing_layout = QVBoxLayout()

        self.matrix_difference_label = QLabel("Данные не обработаны")
        self.matrix_difference_label.setWordWrap(True)
        processing_layout.addWidget(self.matrix_difference_label)

        # Параметры обработки
        self.processing_params_label = QLabel("")
        self.processing_params_label.setWordWrap(True)
        processing_layout.addWidget(self.processing_params_label)

        self.processing_group.setLayout(processing_layout)
        content_layout.addWidget(self.processing_group)

        # Скрываем группу обработки по умолчанию
        self.processing_group.hide()

        # Добавляем растягивающийся элемент внизу
        content_layout.addStretch()

        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

    def set_file_info(self, file_name: str, data_points: int, dye_names: list = None):
        """
        Устанавливает основную информацию о файле.

        Args:
            file_name: Имя файла
            data_points: Количество точек данных
            dye_names: Список названий красителей (опционально)
        """
        self.file_name_label.setText(f"Файл: {file_name}")
        self.data_points_label.setText(f"Количество точек: {data_points:,}")

        if dye_names and len(dye_names) > 0:
            dyes_text = "\n".join([f"  {i+1}. {dye}" for i, dye in enumerate(dye_names)])
            self.dyes_label.setText(dyes_text)
        else:
            self.dyes_label.setText("Информация о реагентах недоступна")

    def set_processing_results(self, matrix_difference: float = None, 
                                smooth_data: bool = None, remove_baseline: bool = None, 
                                algorithm: str = None,
                                results_by_algorithm: dict = None):
        """
        Устанавливает результаты обработки.

        Args:
            matrix_difference: Разница между матрицами (среднее абсолютное отклонение) - для одиночного алгоритма
            smooth_data: Было ли применено сглаживание - для одиночного алгоритма
            remove_baseline: Было ли удаление базовой линии - для одиночного алгоритма
            algorithm: Используемый алгоритм оценки кросс-помех - для одиночного алгоритма
            results_by_algorithm: Словарь результатов по алгоритмам {algorithm: {matrix_difference, smooth_data, ...}}
        """
        # Если есть результаты для нескольких алгоритмов
        if results_by_algorithm and len(results_by_algorithm) > 0:
            self.processing_group.show()
            
            # Формируем текст для отображения разницы матриц для каждого алгоритма
            difference_parts = []
            params_parts = []
            
            # Берем параметры обработки из первого алгоритма (они одинаковы)
            first_algo_info = next(iter(results_by_algorithm.values()))
            smooth_data_multi = first_algo_info.get("smooth_data", None)
            remove_baseline_multi = first_algo_info.get("remove_baseline", None)
            
            for algo, info in results_by_algorithm.items():
                algo_name = "Метод 1 (старый)" if algo == "estimate_crosstalk" else "Метод 2 (новый)"
                matrix_diff = info.get("matrix_difference", None)
                
                if matrix_diff is not None:
                    difference_parts.append(
                        f"{algo_name}:\n"
                        f"  Среднее абсолютное отклонение: {matrix_diff:.6f}"
                    )
            
            if difference_parts:
                difference_text = (
                    "Разница между матрицами:\n\n" +
                    "\n\n".join(difference_parts) +
                    "\n\nЭто значение показывает, насколько вычисленная матрица "
                    "отличается от оригинальной матрицы из .srd файла."
                )
                self.matrix_difference_label.setText(difference_text)
            else:
                self.matrix_difference_label.setText("Данные обработаны, но разница матриц не вычислена")
            
            # Отображаем параметры обработки
            if smooth_data_multi is not None:
                params_parts.append(f"Сглаживание: {'Да' if smooth_data_multi else 'Нет'}")
            if remove_baseline_multi is not None:
                params_parts.append(f"Удаление базовой линии: {'Да' if remove_baseline_multi else 'Нет'}")
            
            # Перечисляем использованные алгоритмы
            algo_names = []
            for algo in results_by_algorithm.keys():
                algo_name = "Метод 1 (старый)" if algo == "estimate_crosstalk" else "Метод 2 (новый)"
                algo_names.append(algo_name)
            params_parts.append(f"Алгоритмы: {', '.join(algo_names)}")
            
            if params_parts:
                params_text = "\n\nПараметры обработки:\n" + "\n".join([f"  {part}" for part in params_parts])
                self.processing_params_label.setText(params_text)
            else:
                self.processing_params_label.setText("")
            
        # Иначе используем старый формат для одиночного алгоритма
        elif matrix_difference is not None or algorithm is not None:
            self.processing_group.show()
            
            if matrix_difference is not None:
                difference_text = (
                    f"Разница между матрицами:\n"
                    f"  Среднее абсолютное отклонение: {matrix_difference:.6f}\n\n"
                    f"Это значение показывает, насколько вычисленная матрица "
                    f"отличается от оригинальной матрицы из .srd файла."
                )
                self.matrix_difference_label.setText(difference_text)
            else:
                self.matrix_difference_label.setText("Данные обработаны")
            
            # Отображаем параметры обработки
            params_parts = []
            if smooth_data is not None:
                params_parts.append(f"Сглаживание: {'Да' if smooth_data else 'Нет'}")
            if remove_baseline is not None:
                params_parts.append(f"Удаление базовой линии: {'Да' if remove_baseline else 'Нет'}")
            if algorithm is not None:
                algorithm_name = "Метод 2 (новый)" if algorithm == "estimate_crosstalk_2" else "Метод 1 (старый)"
                params_parts.append(f"Алгоритм: {algorithm_name}")
            
            if params_parts:
                params_text = "\n\nПараметры обработки:\n" + "\n".join([f"  {part}" for part in params_parts])
                self.processing_params_label.setText(params_text)
            else:
                self.processing_params_label.setText("")
        else:
            self.processing_group.hide()
            self.matrix_difference_label.setText("Данные не обработаны")
            self.processing_params_label.setText("")

    def clear(self):
        """Очищает виджет."""
        self.file_name_label.setText("Файл: не загружен")
        self.data_points_label.setText("Количество точек: —")
        self.dyes_label.setText("Информация недоступна")
        self.matrix_difference_label.setText("Данные не обработаны")
        self.processing_params_label.setText("")
        self.processing_group.hide()

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
                QGroupBox {
                    border: 1px solid #555555;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 10px;
                    font-weight: bold;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                }
                QLabel {
                    color: #ffffff;
                    padding: 3px;
                }
                QScrollArea {
                    border: none;
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
                QGroupBox {
                    border: 1px solid #d0d0d0;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 10px;
                    font-weight: bold;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                }
                QLabel {
                    color: #000000;
                    padding: 3px;
                }
                QScrollArea {
                    border: none;
                }
            """
            )


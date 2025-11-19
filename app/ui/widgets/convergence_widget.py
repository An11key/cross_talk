"""
Виджет для отображения сходимости max(slopes) в процессе итераций.

Этот модуль содержит компонент для визуализации сходимости алгоритма
estimate_crosstalk, показывая график изменения максимального значения slopes
по итерациям.
"""

from typing import Dict, List, Optional
import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class ConvergenceWidget(QWidget):
    """Виджет для отображения графика сходимости max(slopes)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent

        # Данные сходимости: {iteration_num: max_slope_value}
        self.convergence_data: Dict[int, float] = {}

        # Пороговое значение epsilon для отображения линии сходимости
        self.epsilon = 0.05

        # Создаем UI
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Настройка пользовательского интерфейса."""
        layout = QVBoxLayout(self)

        # Заголовок
        header = self._create_header()
        layout.addWidget(header)

        # Разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)

        # График сходимости
        self.plot_widget = self._create_plot()
        layout.addWidget(self.plot_widget)

        # Устанавливаем пропорции
        layout.setStretchFactor(header, 0)
        layout.setStretchFactor(self.plot_widget, 1)

    def _create_header(self) -> QWidget:
        """Создает заголовок виджета."""
        header = QWidget()
        layout = QHBoxLayout(header)

        # Заголовок
        title_label = QLabel("Сходимость max(slopes)")
        title_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setBold(True)
        font.setPointSize(14)
        title_label.setFont(font)

        # Информационная метка
        self.info_label = QLabel("Нет данных")
        self.info_label.setAlignment(Qt.AlignCenter)
        info_font = QFont()
        info_font.setPointSize(10)
        self.info_label.setFont(info_font)

        layout.addStretch()
        layout.addWidget(title_label)
        layout.addStretch()

        # Добавляем информационную метку под заголовком
        header_layout = QVBoxLayout()
        header_layout.addWidget(title_label)
        header_layout.addWidget(self.info_label)

        header_widget = QWidget()
        header_widget.setLayout(header_layout)

        return header_widget

    def _create_plot(self) -> pg.PlotWidget:
        """Создает график для отображения сходимости."""
        plot_widget = pg.PlotWidget()

        # Настраиваем оси
        plot_widget.setLabel("left", "max(|slopes|)")
        plot_widget.setLabel("bottom", "Итерация")
        plot_widget.showGrid(x=True, y=True)
        plot_widget.enableAutoRange()

        # Настраиваем заголовок
        plot_widget.setTitle("График сходимости алгоритма")

        return plot_widget

    def set_convergence_data(self, iteration_data: Dict[int, Dict]) -> None:
        """
        Устанавливает данные итераций и вычисляет сходимость.

        Args:
            iteration_data: Словарь {iteration_num: iteration_results}
                где iteration_results содержит данные для анализа пар каналов
        """
        self.convergence_data.clear()

        if not iteration_data:
            self._update_info_label()
            self._plot_convergence()
            return

        # Вычисляем max(|slopes|) для каждой итерации
        for iteration_num, iteration_results in iteration_data.items():
            slopes = []

            # Собираем все slopes из всех пар каналов
            for (i, j), data_dict in iteration_results.items():
                slope = data_dict.get("slope", 0)
                if slope is not None:
                    slopes.append(abs(slope))

            # Находим максимальное значение
            if slopes:
                max_slope = max(slopes)
                self.convergence_data[iteration_num] = max_slope

        self._update_info_label()
        self._plot_convergence()

    def _update_info_label(self) -> None:
        """Обновляет информационную метку."""
        if not self.convergence_data:
            self.info_label.setText("Нет данных")
            return

        max_iteration = max(self.convergence_data.keys())
        final_value = self.convergence_data[max_iteration]

        # Проверяем, достигнута ли сходимость
        converged = final_value < self.epsilon
        convergence_status = "достигнута" if converged else "не достигнута"

        # Находим итерацию, на которой достигнута сходимость (если достигнута)
        convergence_iteration = None
        if converged:
            for iteration in sorted(self.convergence_data.keys()):
                if self.convergence_data[iteration] < self.epsilon:
                    convergence_iteration = iteration
                    break

        if convergence_iteration is not None:
            self.info_label.setText(
                f"Сходимость {convergence_status} на итерации {convergence_iteration} "
                f"(финальное значение: {final_value:.6f}, порог: {self.epsilon})"
            )
        else:
            self.info_label.setText(
                f"Сходимость {convergence_status} "
                f"(финальное значение: {final_value:.6f}, порог: {self.epsilon})"
            )

    def _plot_convergence(self) -> None:
        """Отображает график сходимости."""
        self.plot_widget.clear()

        if not self.convergence_data:
            return

        # Подготавливаем данные для графика
        iterations = sorted(self.convergence_data.keys())
        values = [self.convergence_data[i] for i in iterations]

        # Получаем текущую тему
        theme = self._get_current_theme()

        # Выбираем цвета в зависимости от темы
        if theme == "white":
            line_color = "#0066CC"  # Синий для светлой темы
            point_color = "#0066CC"
            epsilon_color = "#CC0000"  # Красный для линии epsilon
        else:
            line_color = "#66AAFF"  # Светло-синий для темной темы
            point_color = "#66AAFF"
            epsilon_color = "#FF6666"  # Светло-красный для линии epsilon

        # Строим основной график
        self.plot_widget.plot(
            iterations,
            values,
            pen=pg.mkPen(color=line_color, width=2),
            symbol="o",
            symbolBrush=point_color,
            symbolSize=6,
            symbolPen=pg.mkPen(color=line_color, width=1),
            name="max(|slopes|)",
        )

        # Добавляем горизонтальную линию epsilon
        if iterations:
            min_iter = min(iterations)
            max_iter = max(iterations)

            self.plot_widget.plot(
                [min_iter, max_iter],
                [self.epsilon, self.epsilon],
                pen=pg.mkPen(color=epsilon_color, width=2, style=Qt.DashLine),
                name=f"Порог сходимости (ε = {self.epsilon})",
            )

        # Настраиваем диапазон по Y для лучшего отображения
        if values:
            max_value = max(values)
            y_range_max = max(
                max_value * 1.1, self.epsilon * 2
            )  # Показываем немного выше максимума или epsilon
            self.plot_widget.setYRange(0, y_range_max)

        # Включаем легенду
        self.plot_widget.addLegend()

    def _get_current_theme(self) -> str:
        """Получает текущую тему из родительского окна."""
        if hasattr(self.parent_window, "theme_manager"):
            return (
                "white"
                if not self.parent_window.theme_manager.is_dark_theme
                else "dark"
            )
        return "dark"

    def clear_data(self) -> None:
        """Очищает все данные и график."""
        self.convergence_data.clear()
        self.plot_widget.clear()
        self._update_info_label()

    def apply_theme(self, theme: str) -> None:
        """Применяет тему к графику."""
        if theme == "white":
            self.plot_widget.setBackground("white")
        else:
            self.plot_widget.setBackground("default")

        # Перерисовываем график с новой темой
        self._plot_convergence()

    def set_epsilon(self, epsilon: float) -> None:
        """
        Устанавливает новое значение порога сходимости.

        Args:
            epsilon: Новое значение порога сходимости
        """
        self.epsilon = epsilon
        self._update_info_label()
        self._plot_convergence()

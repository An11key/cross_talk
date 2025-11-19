"""
Виджет для отображения результатов итераций обработки перекрестных помех.

Этот модуль содержит компонент для визуализации промежуточных результатов
алгоритма estimate_crosstalk, показывая графики зависимостей между каналами
для каждой итерации с возможностью навигации.
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
import pyqtgraph as pg
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QGridLayout,
    QFrame,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont


class IterationResultsWidget(QWidget):
    """Виджет для отображения результатов итераций с навигацией."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent

        # Данные итераций: {iteration_num: {(i,j): (x_data, y_data)}}
        self.iteration_data: Dict[
            int, Dict[Tuple[int, int], Tuple[np.ndarray, np.ndarray]]
        ] = {}
        self.current_iteration = 0
        self.max_iterations = 0

        # Названия каналов
        self.channel_names = ["A", "C", "G", "T"]

        # Пороговые размеры для адаптивного интерфейса
        self.compact_width_threshold = 800  # Ширина окна для компактного режима
        self.compact_height_threshold = 600  # Высота окна для компактного режима

        # Таймер для дебаунса изменения размера
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self._update_labels_visibility)

        # Создаем UI
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Настройка пользовательского интерфейса."""
        layout = QVBoxLayout(self)

        # Панель навигации
        nav_panel = self._create_navigation_panel()
        layout.addWidget(nav_panel)

        # Разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)

        # Сетка графиков (2x3 для 6 графиков)
        self.plots_grid = self._create_plots_grid()
        layout.addWidget(self.plots_grid)

        # Устанавливаем пропорции
        layout.setStretchFactor(nav_panel, 0)
        layout.setStretchFactor(self.plots_grid, 1)

        # Инициализируем видимость меток
        self._update_labels_visibility()

    def _create_navigation_panel(self) -> QWidget:
        """Создает панель навигации между итерациями."""
        panel = QWidget()
        layout = QHBoxLayout(panel)

        # Кнопка "Назад"
        self.prev_button = QPushButton("◀ Предыдущая")
        self.prev_button.clicked.connect(self._prev_iteration)
        self.prev_button.setEnabled(False)

        # Метка текущей итерации
        self.iteration_label = QLabel("Нет данных")
        self.iteration_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        self.iteration_label.setFont(font)

        # Кнопка "Вперед"
        self.next_button = QPushButton("Следующая ▶")
        self.next_button.clicked.connect(self._next_iteration)
        self.next_button.setEnabled(False)

        # Добавляем в layout
        layout.addWidget(self.prev_button)
        layout.addStretch()
        layout.addWidget(self.iteration_label)
        layout.addStretch()
        layout.addWidget(self.next_button)

        return panel

    def _create_plots_grid(self) -> QWidget:
        """Создает сетку графиков 2x3."""
        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)

        # Устанавливаем минимальные отступы
        grid_layout.setContentsMargins(5, 5, 5, 5)
        grid_layout.setSpacing(5)

        # Создаем 6 графиков в сетке 2x3
        self.plot_widgets = []

        for row in range(2):
            for col in range(3):
                plot_widget = pg.PlotWidget()
                plot_widget.setLabel("left", "Интенсивность")
                plot_widget.setLabel("bottom", "Интенсивность")
                plot_widget.showGrid(x=True, y=True)
                plot_widget.enableAutoRange()

                # Настраиваем минимальные отступы для компактного отображения
                plot_item = plot_widget.getPlotItem()
                plot_item.setContentsMargins(5, 5, 5, 5)  # left, top, right, bottom

                # Настраиваем оси для компактного отображения
                plot_item.showAxis("left", True)
                plot_item.showAxis("bottom", True)
                plot_item.showAxis("top", False)
                plot_item.showAxis("right", False)

                # Уменьшаем размер шрифта для меток осей
                axis_font = plot_widget.getAxis("left").label.font()
                axis_font.setPointSize(8)
                plot_widget.getAxis("left").label.setFont(axis_font)
                plot_widget.getAxis("bottom").label.setFont(axis_font)

                # Настраиваем стиль тиков
                plot_widget.getAxis("left").setTickFont(axis_font)
                plot_widget.getAxis("bottom").setTickFont(axis_font)

                self.plot_widgets.append(plot_widget)
                grid_layout.addWidget(plot_widget, row, col)

        # Устанавливаем равномерное распределение пространства
        for col in range(3):
            grid_layout.setColumnStretch(col, 1)
        for row in range(2):
            grid_layout.setRowStretch(row, 1)

        return grid_widget

    def set_iteration_data(self, iteration_data: Dict[int, Dict]) -> None:
        """
        Устанавливает данные итераций для отображения.

        Args:
            iteration_data: Словарь {iteration_num: iteration_results}
                где iteration_results содержит данные для анализа пар каналов
        """
        self.iteration_data = iteration_data
        self.max_iterations = max(iteration_data.keys()) if iteration_data else 0
        self.current_iteration = 1 if iteration_data else 0

        self._update_ui_state()
        self._display_current_iteration()

    def _update_ui_state(self) -> None:
        """Обновляет состояние элементов UI."""
        has_data = bool(self.iteration_data)

        self.prev_button.setEnabled(has_data and self.current_iteration > 1)
        self.next_button.setEnabled(
            has_data and self.current_iteration < self.max_iterations
        )

        if has_data:
            self.iteration_label.setText(
                f"Итерация {self.current_iteration} из {self.max_iterations}"
            )
        else:
            self.iteration_label.setText("Нет данных")

    def _prev_iteration(self) -> None:
        """Переходит к предыдущей итерации."""
        if self.current_iteration > 1:
            self.current_iteration -= 1
            self._update_ui_state()
            self._display_current_iteration()

    def _next_iteration(self) -> None:
        """Переходит к следующей итерации."""
        if self.current_iteration < self.max_iterations:
            self.current_iteration += 1
            self._update_ui_state()
            self._display_current_iteration()

    def _display_current_iteration(self) -> None:
        """Отображает графики для текущей итерации."""
        # Очищаем все графики
        for plot_widget in self.plot_widgets:
            plot_widget.clear()

        if not self.iteration_data or self.current_iteration not in self.iteration_data:
            return

        current_data = self.iteration_data[self.current_iteration]

        # Определяем уникальные пары каналов (без повторений)
        # A vs C, A vs G, A vs T, C vs G, C vs T, G vs T
        plot_pairs = [
            (0, 1),  # A vs C
            (0, 2),  # A vs G
            (0, 3),  # A vs T
            (1, 2),  # C vs G
            (1, 3),  # C vs T
            (2, 3),  # G vs T
        ]

        for idx, (i, j) in enumerate(plot_pairs):
            if idx >= len(self.plot_widgets):
                break

            plot_widget = self.plot_widgets[idx]

            # Получаем данные для этой пары каналов
            # Ищем данные как для (i,j), так и для (j,i)
            x_data, y_data, slope, intercept = None, None, None, None
            x_regression, y_regression = None, None
            swap_axes = False

            if (i, j) in current_data:
                data_dict = current_data[(i, j)]
                x_data = data_dict["x_data"]
                y_data = data_dict["y_data"]
                slope = data_dict["slope"]
                intercept = data_dict["intercept"]
                # Извлекаем точки регрессии если есть
                x_regression = data_dict.get("x_regression_points", None)
                y_regression = data_dict.get("y_regression_points", None)
            elif (j, i) in current_data:
                # Если есть обратная пара, меняем местами x и y
                data_dict = current_data[(j, i)]
                x_data = data_dict["y_data"]
                y_data = data_dict["x_data"]
                # Для обратной пары slope нужно пересчитать (обратная зависимость)
                if data_dict["slope"] != 0:
                    slope = 1.0 / data_dict["slope"]  # Обратный slope
                    intercept = -data_dict["intercept"] / data_dict["slope"]
                else:
                    slope = 0
                    intercept = data_dict["intercept"]
                # Меняем местами точки регрессии тоже
                x_regression = data_dict.get("y_regression_points", None)
                y_regression = data_dict.get("x_regression_points", None)
                swap_axes = True

            if x_data is not None and y_data is not None:
                # Настраиваем график
                channel_i = self.channel_names[i]
                channel_j = self.channel_names[j]

                # Устанавливаем компактный заголовок
                plot_widget.setTitle(f"{channel_i} vs {channel_j}")

                # Устанавливаем метки осей в зависимости от размера окна
                size = self.size()
                is_compact = (
                    size.width() < self.compact_width_threshold
                    or size.height() < self.compact_height_threshold
                )

                if is_compact:
                    # В компактном режиме убираем подписи осей
                    plot_widget.setLabel("left", "")
                    plot_widget.setLabel("bottom", "")
                else:
                    # В обычном режиме показываем подписи
                    plot_widget.setLabel("left", f"{channel_j}")
                    plot_widget.setLabel("bottom", f"{channel_i}")

                # Настраиваем размер шрифта заголовка
                title_item = plot_widget.getPlotItem().titleLabel
                title_item.setMaximumHeight(20)  # Ограничиваем высоту заголовка

                # Применяем тему
                theme = self._get_current_theme()
                color = self._get_color_for_pair(i, j, theme)

                # Оптимизируем количество точек для отображения
                x_plot, y_plot = self._optimize_points_for_display(x_data, y_data)

                # Строим график с меньшими точками, поскольку их много
                plot_widget.plot(
                    x_plot,
                    y_plot,
                    pen=None,
                    symbol="o",
                    symbolBrush=color,
                    symbolSize=2,  # Уменьшили размер точек
                    symbolPen=None,  # Убираем обводку для лучшего вида
                    name=f"{channel_i} vs {channel_j}",
                )

                # Отображаем точки регрессии отдельно, если они есть
                if (
                    x_regression is not None
                    and y_regression is not None
                    and len(x_regression) > 0
                    and len(y_regression) > 0
                ):
                    # Используем яркий цвет для точек регрессии в зависимости от пары каналов
                    regression_color = self._get_regression_color(i, j, theme)
                    plot_widget.plot(
                        x_regression,
                        y_regression,
                        pen=None,
                        symbol="s",  # Квадратные символы для точек регрессии
                        symbolBrush=regression_color,
                        symbolSize=4,  # Больше размер для лучшей видимости
                        symbolPen=pg.mkPen(color="white", width=1),  # Белая обводка
                        name=f"{channel_i} vs {channel_j} (регрессия)",
                    )

                # Для регрессии используем рассчитанные коэффициенты из L1 регрессии
                if slope is not None and intercept is not None:
                    # Используем тот же яркий цвет для линии регрессии
                    regression_color = self._get_regression_color(i, j, theme)
                    self._add_regression_line_with_coeffs(
                        plot_widget, x_data, y_data, regression_color, slope, intercept
                    )
            else:
                # Если данных нет, показываем компактный заголовок
                channel_i = self.channel_names[i]
                channel_j = self.channel_names[j]
                plot_widget.setTitle(f"{channel_i} vs {channel_j} (нет данных)")

                # Настраиваем размер шрифта заголовка
                title_item = plot_widget.getPlotItem().titleLabel
                title_item.setMaximumHeight(20)

    def _get_current_theme(self) -> str:
        """Получает текущую тему из родительского окна."""
        if hasattr(self.parent_window, "theme_manager"):
            return (
                "white"
                if not self.parent_window.theme_manager.is_dark_theme
                else "dark"
            )
        return "dark"

    def _get_color_for_pair(self, i: int, j: int, theme: str) -> str:
        """Получает нейтральный светло-серый цвет для всех точек."""
        # Используем светло-серый цвет для всех точек независимо от темы
        if theme == "white":
            return "#B0B0B0"  # Светло-серый для светлой темы
        else:
            return "#808080"  # Средне-серый для темной темы

    def _get_regression_color(self, i: int, j: int, theme: str) -> str:
        """Получает яркий цвет для точек регрессии в зависимости от пары каналов."""
        if theme == "white":
            # Яркие цвета для светлой темы
            colors = [
                "#FF0000",
                "#00AA00",
                "#0066FF",
                "#FF8800",
            ]  # Красный, Зеленый, Синий, Оранжевый
        else:
            # Яркие цвета для темной темы
            colors = [
                "#FF6666",
                "#66FF66",
                "#6666FF",
                "#FFFF66",
            ]  # Светло-красный, Светло-зеленый, Светло-синий, Светло-желтый

        # Используем цвет первого канала (i)
        return colors[i % len(colors)]

    def _add_regression_line_with_coeffs(
        self,
        plot_widget: pg.PlotWidget,
        x_data: np.ndarray,
        y_data: np.ndarray,
        color: str,
        slope: float,
        intercept: float,
    ) -> None:
        """Добавляет линию регрессии на график используя предвычисленные коэффициенты из L1 регрессии."""
        try:
            if len(x_data) > 1:
                x_line = np.linspace(x_data.min(), x_data.max(), 100)
                y_line = slope * x_line + intercept

                # Делаем линию чуть темнее точек
                line_color = color if isinstance(color, str) else "white"

                plot_widget.plot(
                    x_line,
                    y_line,
                    pen=pg.mkPen(color=line_color, width=2, style=Qt.DashLine),
                    name=f"L1 Регрессия (slope={slope:.4f})",
                )
        except Exception:
            # Если не удалось построить регрессию, просто игнорируем
            pass

    def _add_regression_line(
        self,
        plot_widget: pg.PlotWidget,
        x_data: np.ndarray,
        y_data: np.ndarray,
        color: str,
    ) -> None:
        """Добавляет линию регрессии на график (устаревшая функция, использует простую регрессию)."""
        try:
            # Простая линейная регрессия
            if len(x_data) > 1:
                coeffs = np.polyfit(x_data, y_data, 1)
                poly_fn = np.poly1d(coeffs)

                x_line = np.linspace(x_data.min(), x_data.max(), 100)
                y_line = poly_fn(x_line)

                # Делаем линию чуть темнее точек
                line_color = color if isinstance(color, str) else "white"

                plot_widget.plot(
                    x_line,
                    y_line,
                    pen=pg.mkPen(color=line_color, width=2, style=Qt.DashLine),
                    name="Регрессия",
                )
        except Exception:
            # Если не удалось построить регрессию, просто игнорируем
            pass

    def clear_data(self) -> None:
        """Очищает все данные и графики."""
        self.iteration_data.clear()
        self.current_iteration = 0
        self.max_iterations = 0

        for plot_widget in self.plot_widgets:
            plot_widget.clear()

        self._update_ui_state()

    def apply_theme(self, theme: str) -> None:
        """Применяет тему к графикам."""
        for plot_widget in self.plot_widgets:
            if theme == "white":
                plot_widget.setBackground("white")
            else:
                plot_widget.setBackground("default")

        # Перерисовываем текущую итерацию с новой темой
        self._display_current_iteration()

    def _optimize_points_for_display(
        self, x_data: np.ndarray, y_data: np.ndarray, max_points: int = 5000
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Оптимизирует количество точек для отображения без потери визуальной информации.

        Args:
            x_data: Данные по оси X
            y_data: Данные по оси Y
            max_points: Максимальное количество точек для отображения

        Returns:
            Оптимизированные массивы (x, y)
        """
        if len(x_data) <= max_points:
            return x_data, y_data

        # Если точек слишком много, используем равномерное прореживание
        step = len(x_data) // max_points
        indices = np.arange(0, len(x_data), step)

        return x_data[indices], y_data[indices]

    def resizeEvent(self, event) -> None:
        """Обработчик изменения размера виджета."""
        super().resizeEvent(event)
        # Используем таймер для дебаунса, чтобы избежать слишком частых обновлений
        self.resize_timer.start(100)  # Задержка 100мс

    def _update_labels_visibility(self) -> None:
        """Обновляет видимость меток осей в зависимости от размера окна."""
        if not hasattr(self, "plot_widgets"):
            return

        size = self.size()
        is_compact = (
            size.width() < self.compact_width_threshold
            or size.height() < self.compact_height_threshold
        )

        for plot_widget in self.plot_widgets:
            if is_compact:
                # В компактном режиме убираем подписи осей
                plot_widget.setLabel("left", "")
                plot_widget.setLabel("bottom", "")
                # Делаем тики меньше
                plot_widget.getAxis("left").setStyle(tickLength=3)
                plot_widget.getAxis("bottom").setStyle(tickLength=3)
            else:
                # В обычном режиме восстанавливаем подписи
                # Подписи будут установлены при следующем обновлении данных
                plot_widget.getAxis("left").setStyle(tickLength=5)
                plot_widget.getAxis("bottom").setStyle(tickLength=5)

        # Перерисовываем текущую итерацию с правильными подписями
        self._display_current_iteration()

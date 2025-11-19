"""
Модуль отрисовки графиков и оптимизации производительности.

Содержит класс PlotRenderer для управления рендерингом графиков,
кешированием данных и оптимизацией производительности.
"""

import numpy as np
import pandas as pd
import pyqtgraph as pg
from typing import Optional, Tuple


class PlotRenderer:
    """Класс для отрисовки графиков и управления производительностью."""

    # Настройки производительности
    MAX_POINTS_FOR_SMOOTH_RENDERING = 400000  # Максимум точек для плавного рендеринга
    DOWNSAMPLE_FACTOR = 10  # Коэффициент прореживания для больших датасетов

    def __init__(self, parent_window):
        """
        Инициализация рендерера графиков.

        Args:
            parent_window: Родительское окно (экземпляр MyMenu)
        """
        self.parent = parent_window
        self.plot_cache = {}  # Кеш для графиков
        self.current_downsample_factor = 1
        self.lazy_load_cache = {}  # Кеш для ленивой загрузки
        self.max_cache_size = 10  # Максимум файлов в кеше
        self.manual_downsample_mode = False  # Режим ручного прореживания
        self.current_data_cache = {}  # Кеш текущих данных для быстрой перерисовки
        self.disable_downsample = False  # Полное отключение прореживания

    def should_downsample(self, data: pd.DataFrame) -> bool:
        """Проверяет, нужно ли прореживать данные для оптимизации."""
        total_points = len(data) * len(data.columns)
        return total_points > self.MAX_POINTS_FOR_SMOOTH_RENDERING

    def downsample_data(
        self, data: pd.DataFrame, factor: int = None
    ) -> Tuple[pd.DataFrame, int]:
        """
        Прореживает данные для оптимизации отображения.

        Args:
            data: Исходные данные
            factor: Коэффициент прореживания (если None, рассчитывается автоматически)

        Returns:
            Кортеж (прореженные_данные, коэффициент_прореживания)
        """
        if factor is None:
            total_points = len(data) * len(data.columns)
            if total_points <= self.MAX_POINTS_FOR_SMOOTH_RENDERING:
                return data, 1

            # Рассчитываем оптимальный коэффициент прореживания
            factor = max(1, total_points // self.MAX_POINTS_FOR_SMOOTH_RENDERING)
            factor = min(
                factor, self.DOWNSAMPLE_FACTOR
            )  # Не прореживаем слишком сильно

        if factor <= 1:
            return data, 1

        # Прореживаем данные
        downsampled = data.iloc[::factor].copy()
        return downsampled, factor

    def get_optimal_downsample_factor(self, data: pd.DataFrame) -> int:
        """
        Рассчитывает оптимальный коэффициент прореживания для данных.

        Args:
            data: Исходные данные

        Returns:
            Рекомендуемый коэффициент прореживания
        """
        total_points = len(data) * len(data.columns)
        if total_points <= self.MAX_POINTS_FOR_SMOOTH_RENDERING:
            return 1

        factor = max(1, total_points // self.MAX_POINTS_FOR_SMOOTH_RENDERING)
        return min(factor, self.DOWNSAMPLE_FACTOR)

    def optimize_plot_settings(self, plot_widget: pg.PlotWidget):
        """Оптимизирует настройки pyqtgraph для лучшей производительности."""
        # Отключаем авто-обновление во время построения
        plot_widget.setUpdatesEnabled(False)

        # Оптимизируем настройки рендеринга
        plot_widget.setClipToView(True)
        plot_widget.setDownsampling(auto=True, mode="peak")

        # Включаем обратно обновление
        plot_widget.setUpdatesEnabled(True)

    def plot_data(self, plot_widget: pg.PlotWidget, data: pd.DataFrame):
        """Адаптер к helper-функции отрисовки датафреймов с учётом темы."""
        self.plot_dataframe_with_theme(
            plot_widget, data, self.parent.theme_manager.current_plot_theme
        )

    def plot_dataframe_with_theme(
        self, plot_widget: pg.PlotWidget, data: pd.DataFrame, theme: str
    ) -> None:
        """Отрисовывает датафрейм с цветами, подходящими для текущей темы и оптимизациями."""
        # Оптимизируем настройки виджета
        self.optimize_plot_settings(plot_widget)

        # Очищаем график и легенду
        plot_widget.clear()

        # Удаляем старую легенду, если она есть
        if hasattr(plot_widget, "legend") and plot_widget.legend is not None:
            plot_widget.legend.scene().removeItem(plot_widget.legend)
            plot_widget.legend = None

        # Определяем коэффициент прореживания
        if self.disable_downsample:
            # Полное отключение прореживания - данные не проходят через downsample_data
            self.current_downsample_factor = 1
        elif self.manual_downsample_mode:
            # Ручной режим - используем значение ползунка
            manual_factor = self.parent.downsample_slider.value()
            if manual_factor > 1:
                data, self.current_downsample_factor = self.downsample_data(
                    data, manual_factor
                )
            else:
                self.current_downsample_factor = 1
        else:
            # Автоматический режим - как было раньше
            if self.should_downsample(data):
                data, self.current_downsample_factor = self.downsample_data(data)
            else:
                self.current_downsample_factor = 1

        # Настраиваем виджет
        plot_widget.enableAutoRange()
        plot_widget.setMouseEnabled(x=True, y=True)
        plot_widget.showGrid(x=True, y=True)

        # Выбираем цвета в зависимости от темы
        if theme == "white":
            # Тёмные цвета для светлой темы
            colors = [
                "#CC0000",
                "#006600",
                "#000080",
                "#CC6600",
            ]  # Тёмно-красный, тёмно-зелёный, тёмно-синий, тёмно-оранжевый
        else:
            # Яркие цвета для тёмной темы
            colors = ["r", "g", "b", "y"]  # Красный, зелёный, синий, жёлтый

        # Создаём легенду
        legend = plot_widget.addLegend(offset=(10, 10))

        # Оптимизированная отрисовка с использованием numpy для лучшей производительности
        for i, column in enumerate(data.columns):
            y_raw = data[column].values
            # Обрабатываем NaN значения
            y = np.nan_to_num(y_raw, nan=0.0)

            # Создаем индексы с учетом прореживания
            if self.current_downsample_factor > 1:
                x = np.arange(
                    0,
                    len(y) * self.current_downsample_factor,
                    self.current_downsample_factor,
                    dtype=float,
                )
            else:
                x = np.arange(len(y), dtype=float)

            # Используем оптимизированные настройки pyqtgraph
            plot_item = plot_widget.plot(
                x,
                y,
                pen=pg.mkPen(color=colors[i % len(colors)], width=1.5),
                name=column,
                skipFiniteCheck=True,  # Отключаем проверку на конечность для производительности
            )

            # Дополнительная оптимизация для больших датасетов
            if len(y) > 10000:
                plot_item.setSymbol(None)  # Убираем символы для линий
                plot_item.setSymbolSize(0)

    def get_cached_data(self, file_path: str) -> Optional[pd.DataFrame]:
        """Получает данные из кеша ленивой загрузки."""
        return self.lazy_load_cache.get(file_path)

    def cache_data(self, file_path: str, data: pd.DataFrame):
        """Кеширует данные для ленивой загрузки."""
        # Очищаем кеш если он переполнен
        if len(self.lazy_load_cache) >= self.max_cache_size:
            # Удаляем самый старый элемент (простая LRU реализация)
            oldest_key = next(iter(self.lazy_load_cache))
            del self.lazy_load_cache[oldest_key]

        self.lazy_load_cache[file_path] = data

    def load_data_efficiently(self, file_path: str) -> pd.DataFrame:
        """
        Эффективно загружает данные с использованием кеширования.

        Сначала проверяет кеш, затем загружает с оптимизациями.
        """
        # Проверяем кеш
        cached_data = self.get_cached_data(file_path)
        if cached_data is not None:
            return cached_data

        # Загружаем данные
        data = self.parent._load_data_by_path(file_path)

        # Кешируем для будущих использований
        self.cache_data(file_path, data)

        return data

    def preload_data_async(self, file_paths: list):
        """
        Предварительно загружает данные в фоне для улучшения UX.

        Args:
            file_paths: Список путей к файлам для предварительной загрузки
        """
        # Простая реализация предварительной загрузки
        # В реальном приложении лучше использовать QThreadPool или отдельный поток
        for file_path in file_paths[
            :3
        ]:  # Предварительно загружаем только первые 3 файла
            if file_path not in self.lazy_load_cache:
                try:
                    data = self.parent._load_data_by_path(file_path)
                    self.cache_data(file_path, data)
                except Exception:
                    # Игнорируем ошибки при предварительной загрузке
                    pass

    def update_performance_settings(
        self, max_points: int = None, downsample_factor: int = None
    ):
        """
        Обновляет настройки производительности.

        Args:
            max_points: Максимум точек для плавного рендеринга
            downsample_factor: Коэффициент прореживания
        """
        if max_points is not None:
            self.MAX_POINTS_FOR_SMOOTH_RENDERING = max_points
        if downsample_factor is not None:
            self.DOWNSAMPLE_FACTOR = downsample_factor

    def clear_cache(self):
        """Очищает кеш для освобождения памяти."""
        self.plot_cache.clear()
        self.lazy_load_cache.clear()

    def clear_cache_for_file(self, file_name: str):
        """Очищает кэши для конкретного файла."""
        import os

        # Получаем путь к файлу для очистки lazy_load_cache
        if self.parent.registry.has_file(file_name):
            file_path = self.parent.registry.get_path(file_name)
            # Удаляем из lazy_load_cache
            self.lazy_load_cache.pop(file_path, None)
            print(f"Очищен кэш для файла: {file_name}")

        # Очищаем current_data_cache для этого файла и связанных файлов
        base_name = os.path.splitext(file_name)[0]
        keys_to_remove = []
        for key in self.current_data_cache:
            if key == file_name or key.startswith(base_name):
                keys_to_remove.append(key)

        for key in keys_to_remove:
            self.current_data_cache.pop(key, None)
            print(f"Очищен data cache для ключа: {key}")

        # Очищаем plot_cache (если используется с ключами файлов)
        keys_to_remove = []
        for key in self.plot_cache:
            if isinstance(key, str) and (key == file_name or key.startswith(base_name)):
                keys_to_remove.append(key)

        for key in keys_to_remove:
            self.plot_cache.pop(key, None)
            print(f"Очищен plot cache для ключа: {key}")

    def get_performance_info(self) -> dict:
        """
        Возвращает информацию о производительности.

        Returns:
            Словарь с информацией о кеше и настройках
        """
        return {
            "cache_size": len(self.lazy_load_cache),
            "max_cache_size": self.max_cache_size,
            "downsample_factor": self.DOWNSAMPLE_FACTOR,
            "max_points": self.MAX_POINTS_FOR_SMOOTH_RENDERING,
            "current_downsample": self.current_downsample_factor,
            "manual_mode": self.manual_downsample_mode,
        }

    def set_manual_downsample_mode(self, enabled: bool):
        """
        Переключает режим ручного управления прореживанием.

        Args:
            enabled: True для ручного режима, False для автоматического
        """
        self.manual_downsample_mode = enabled

    def set_disable_downsample(self, disabled: bool):
        """
        Полностью отключает или включает прореживание данных.

        Args:
            disabled: True для полного отключения прореживания, False для обычного режима
        """
        self.disable_downsample = disabled

    def update_downsample_slider_label(self, value: int):
        """
        Обновляет метку значения ползунка прореживания.

        Args:
            value: Текущее значение ползунка
        """
        pass


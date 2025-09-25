"""
Отрисовка графиков и управление вкладками.

Этот модуль содержит всю логику отображения данных
в виде графиков и управления вкладками интерфейса.

Оптимизации производительности:
- Downsampling больших датасетов
- Кеширование графиков
- Асинхронная загрузка данных
"""

import numpy as np
import pandas as pd
import pyqtgraph as pg
from PySide6.QtWidgets import QListWidgetItem
from typing import Optional, Tuple, Dict
from app.ui.iteration_results import IterationResultsWidget


class PlottingManager:
    """Менеджер для отрисовки графиков и управления вкладками."""

    # Настройки производительности
    MAX_POINTS_FOR_SMOOTH_RENDERING = 400000  # Максимум точек для плавного рендеринга
    DOWNSAMPLE_FACTOR = 10  # Коэффициент прореживания для больших датасетов

    def __init__(self, parent_window):
        """
        Инициализация менеджера графиков.

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
        self.current_clean_file_base = (
            None  # Базовое имя файла для текущей clean вкладки
        )

        # Данные итераций для вкладки результатов по файлам
        # {file_name: {iteration_num: iteration_data}}
        self.iteration_results_data: Dict[str, Dict[int, Dict]] = {}
        self.current_iterations_file = None  # Текущий файл для вкладки итераций

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

        # Очищаем график
        plot_widget.clear()

        # Определяем коэффициент прореживания
        if self.disable_downsample:
            # Полное отключение прореживания - данные не проходят через downsample_data
            self.current_downsample_factor = 1
            plot_widget.setTitle("Полные данные (прореживание отключено)")
        elif self.manual_downsample_mode:
            # Ручной режим - используем значение ползунка
            manual_factor = self.parent.downsample_slider.value()
            if manual_factor > 1:
                data, self.current_downsample_factor = self.downsample_data(
                    data, manual_factor
                )
                plot_widget.setTitle(f"Прорежено {manual_factor}x (ручное)")
            else:
                self.current_downsample_factor = 1
                plot_widget.setTitle("Полные данные")
        else:
            # Автоматический режим - как было раньше
            if self.should_downsample(data):
                data, self.current_downsample_factor = self.downsample_data(data)
                plot_widget.setTitle(
                    f"Прорежено {self.current_downsample_factor}x (авто)"
                )
            else:
                self.current_downsample_factor = 1
                plot_widget.setTitle("Полные данные")

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
        if value == 1:
            self.parent.downsample_value_label.setText("1x (полные данные)")
        else:
            self.parent.downsample_value_label.setText(f"{value}x")

    def refresh_current_plots(self):
        """
        Перерисовывает текущие открытые графики с новыми настройками прореживания.
        """
        current_item = self.parent.list_widget.currentItem()
        if current_item:
            # Перерисовываем текущий график
            self.file_list_click(current_item)

    def ensure_clean_tab(self):
        """Создаёт вкладку Clean при первом обращении к ней."""
        if self.parent.clean_plot_widget is None:
            self.parent.clean_plot_widget = pg.PlotWidget()
            self.parent.view_tabs.addTab(self.parent.clean_plot_widget, "Clean")

            # Применяем текущую тему к новому виджету
            theme = "white" if not self.parent.theme_manager.is_dark_theme else "dark"
            if theme == "white":
                self.parent.clean_plot_widget.setBackground("white")
            else:
                self.parent.clean_plot_widget.setBackground("default")

    def remove_clean_tab(self):
        """Удаляет вкладку Clean, если очищенных данных для выбранного файла нет."""
        if self.parent.clean_plot_widget is not None:
            idx = self.parent.view_tabs.indexOf(self.parent.clean_plot_widget)
            if idx != -1:
                self.parent.view_tabs.removeTab(idx)
            self.parent.clean_plot_widget = None
            self.current_clean_file_base = None

    def remove_clean_data_for_file(self, base_name: str):
        """
        Удаляет clean данные для указанного файла из реестра и физически с диска.

        Args:
            base_name: Базовое имя файла (без _clean)
        """
        # Возможные варианты имен clean файлов
        clean_candidates = [f"{base_name}_clean.csv", f"{base_name}_clean.srd"]

        # Удаляем все найденные clean файлы из реестра
        removed_files = []
        for candidate in clean_candidates:
            if self.parent.registry.has_file(candidate):
                self.parent.registry.remove(candidate)
                removed_files.append(candidate)

        # Теперь удаляем физические clean файлы с диска
        import os

        processed_dir = "processed_sequences"
        sequence_folder = os.path.join(processed_dir, f"{base_name}_seq")

        if os.path.exists(sequence_folder):
            # Ищем и удаляем только clean файлы в папке
            deleted_count = 0
            for file_name in os.listdir(sequence_folder):
                if "_clean" in file_name and file_name.lower().endswith(
                    (".csv", ".srd")
                ):
                    clean_file_path = os.path.join(sequence_folder, file_name)
                    try:
                        os.remove(clean_file_path)
                        print(f"Удален физический файл: {clean_file_path}")
                        deleted_count += 1
                    except OSError as e:
                        print(f"Ошибка при удалении файла {clean_file_path}: {e}")

            if deleted_count > 0:
                print(f"Удалено {deleted_count} clean файлов для {base_name}")
            else:
                print(f"Не найдено clean файлов для удаления в {sequence_folder}")
        else:
            print(f"Не найдена папка: {sequence_folder}")

        # Удаляем clean вкладку
        self.remove_clean_tab()

        # Удаляем данные итераций для этого файла
        self.clear_iteration_data(base_name)

        # Обновляем список файлов в интерфейсе
        self.parent.file_manager.refresh_file_list()

        return removed_files

    def file_list_click(self, item: QListWidgetItem):
        """При клике по файлу показывает Raw и, если есть, добавляет/обновляет Clean."""
        name = item.text()

        # Используем оптимизированную загрузку данных
        if not self.parent.registry.has_df(name):
            file_path = self.parent.registry.get_path(name)
            data = self.load_data_efficiently(file_path)
            self.parent.registry.set_df(name, data)

        # Обновляем ползунок в автоматическом режиме
        if not self.manual_downsample_mode:
            data = self.parent.registry.get_df(name)
            optimal_factor = self.get_optimal_downsample_factor(data)
            self.parent.downsample_slider.setValue(optimal_factor)
            self.update_downsample_slider_label(optimal_factor)

        # Определяем, исходный это файл или очищенный
        is_clean_file = "_clean" in name
        if is_clean_file:
            # Для очищенного файла убираем "_clean" из имени
            base_no_ext = name.split("_clean")[0]
            ext = "." + name.split("_clean")[1]
        else:
            # Для исходного файла разделяем имя и расширение
            parts = name.split(".")
            base_no_ext = parts[0]
            ext = "." + parts[1] if len(parts) > 1 else ""
        base_name = base_no_ext.replace("_clean", "")
        # Варианты имён очищенного файла: такое же расширение, или csv (для исходного .srd)
        clean_candidates = [f"{base_name}_clean{ext}"]
        if ext.lower() == ".srd":
            clean_candidates.append(f"{base_name}_clean.csv")

        if is_clean_file:
            # Кликнули на очищенный файл — показываем только его
            self.plot_data(
                self.parent.raw_plot_widget, self.parent.registry.get_df(name)
            )
            self.parent.view_tabs.setCurrentWidget(self.parent.raw_plot_widget)
            self.remove_clean_tab()

            # Проверяем и показываем вкладку итераций для очищенного файла
            if self.has_iteration_data_for_file(name):
                self.show_iterations_for_file(name)
            else:
                # Убираем вкладку Iterations если нет данных для текущего файла
                self.remove_iterations_tab()
        else:
            # Кликнули на исходный файл — показываем Raw и, если есть, Clean
            self.plot_data(
                self.parent.raw_plot_widget, self.parent.registry.get_df(name)
            )
            self.parent.view_tabs.setCurrentWidget(self.parent.raw_plot_widget)

            clean_found = None
            for cand in clean_candidates:
                if self.parent.registry.has_file(cand):
                    clean_found = cand
                    break
            if clean_found is not None:
                if not self.parent.registry.has_df(clean_found):
                    clean_file_path = self.parent.registry.get_path(clean_found)
                    clean_data = self.load_data_efficiently(clean_file_path)
                    self.parent.registry.set_df(clean_found, clean_data)
                self.ensure_clean_tab()
                self.plot_data(
                    self.parent.clean_plot_widget,
                    self.parent.registry.get_df(clean_found),
                )
                # Запоминаем базовое имя файла для clean вкладки
                self.current_clean_file_base = base_name
            else:
                self.remove_clean_tab()

            # Проверяем и показываем вкладку итераций для этого файла только если есть данные
            if self.has_iteration_data_for_file(name):
                self.show_iterations_for_file(name)
            else:
                # Убираем вкладку Iterations если нет данных для текущего файла
                self.remove_iterations_tab()

    def ensure_iterations_tab(self):
        """Создаёт вкладку Iterations при первом обращении к ней."""
        if self.parent.iterations_widget is None:
            self.parent.iterations_widget = IterationResultsWidget(self.parent)
            self.parent.view_tabs.addTab(self.parent.iterations_widget, "Iterations")

            # Применяем текущую тему к новому виджету
            theme = "white" if not self.parent.theme_manager.is_dark_theme else "dark"
            self.parent.iterations_widget.apply_theme(theme)

    def remove_iterations_tab(self):
        """Удаляет вкладку Iterations."""
        if self.parent.iterations_widget is not None:
            idx = self.parent.view_tabs.indexOf(self.parent.iterations_widget)
            if idx != -1:
                self.parent.view_tabs.removeTab(idx)
            self.parent.iterations_widget = None
            self.current_iterations_file = None

    def store_iteration_data(
        self, file_name: str, iteration_num: int, iteration_data: Dict
    ) -> None:
        """
        Сохраняет данные итерации для отображения.

        Args:
            file_name: Имя файла, для которого сохраняются данные
            iteration_num: Номер итерации
            iteration_data: Данные итерации в формате {(i,j): (x_data, y_data)}
        """
        if file_name not in self.iteration_results_data:
            self.iteration_results_data[file_name] = {}

        self.iteration_results_data[file_name][iteration_num] = iteration_data

        # Если вкладка создана и отображает данные для этого файла, обновляем
        if (
            self.parent.iterations_widget is not None
            and self.current_iterations_file == file_name
        ):
            self.parent.iterations_widget.set_iteration_data(
                self.iteration_results_data[file_name]
            )

    def finalize_iteration_results(self, file_name: str) -> None:
        """
        Завершает сбор данных итераций и обеспечивает вкладку.

        Args:
            file_name: Имя файла, для которого завершается сбор данных
        """
        if (
            file_name in self.iteration_results_data
            and self.iteration_results_data[file_name]
        ):
            # Сохраняем данные итераций на диск
            self._save_iteration_results_to_disk(file_name)

            self.ensure_iterations_tab()
            self.current_iterations_file = file_name
            if self.parent.iterations_widget is not None:
                self.parent.iterations_widget.set_iteration_data(
                    self.iteration_results_data[file_name]
                )

    def clear_iteration_data(self, file_name: str = None) -> None:
        """
        Очищает данные итераций.

        Args:
            file_name: Имя файла для очистки. Если None, очищает все данные.
        """
        if file_name is None:
            self.iteration_results_data.clear()
            self.current_iterations_file = None
        else:
            self.iteration_results_data.pop(file_name, None)
            if self.current_iterations_file == file_name:
                self.current_iterations_file = None

        if self.parent.iterations_widget is not None:
            if file_name is None or self.current_iterations_file is None:
                self.parent.iterations_widget.clear_data()
                self.remove_iterations_tab()

    def has_iteration_data_for_file(self, file_name: str) -> bool:
        """
        Проверяет наличие данных итераций для указанного файла без создания/удаления вкладки.

        Args:
            file_name: Имя файла

        Returns:
            True если данные найдены, False иначе
        """
        # Получаем базовое имя файла без расширения для поиска
        base_name = self._get_base_name_from_file(file_name)

        # Ищем данные итераций для этого файла или его базового имени в памяти
        for key in self.iteration_results_data:
            if key == file_name or self._get_base_name_from_file(key) == base_name:
                return True

        # Если данных нет в памяти, проверяем наличие файла итераций на диске
        return self._check_iteration_file_exists(file_name)

    def show_iterations_for_file(self, file_name: str) -> bool:
        """
        Показывает данные итераций для указанного файла.

        Args:
            file_name: Имя файла

        Returns:
            True если данные найдены и показаны, False иначе
        """
        # Получаем базовое имя файла без расширения для поиска
        base_name = self._get_base_name_from_file(file_name)

        # Ищем данные итераций для этого файла или его базового имени
        iteration_data = None
        found_key = None

        for key in self.iteration_results_data:
            if key == file_name or self._get_base_name_from_file(key) == base_name:
                iteration_data = self.iteration_results_data[key]
                found_key = key
                break

        # Если данных нет в памяти, пытаемся загрузить с диска
        if not iteration_data:
            if self._load_iteration_results_from_disk(file_name):
                iteration_data = self.iteration_results_data.get(file_name)
                found_key = file_name
            elif self._load_iteration_results_from_disk(base_name):
                iteration_data = self.iteration_results_data.get(base_name)
                found_key = base_name

        if iteration_data:
            self.ensure_iterations_tab()
            self.current_iterations_file = found_key
            if self.parent.iterations_widget is not None:
                self.parent.iterations_widget.set_iteration_data(iteration_data)
                return True

        return False

    def _get_base_name_from_file(self, file_name: str) -> str:
        """Получает базовое имя файла без расширения и _clean."""
        if "_clean" in file_name:
            base_name = file_name.split("_clean")[0]
        else:
            parts = file_name.split(".")
            base_name = parts[0]
        return base_name

    def _save_iteration_results_to_disk(self, file_name: str) -> None:
        """Сохраняет данные итераций для файла на диск."""
        if file_name in self.iteration_results_data:
            # Получаем путь к исходному файлу
            file_path = self.parent.registry.get_path(file_name)
            if file_path:
                from app.core.processing import save_iteration_data

                try:
                    save_iteration_data(
                        file_path, self.iteration_results_data[file_name]
                    )
                    print(f"Данные итераций сохранены для файла: {file_name}")
                except Exception as e:
                    print(f"Ошибка при сохранении данных итераций для {file_name}: {e}")

    def _load_iteration_results_from_disk(self, file_name: str) -> bool:
        """Загружает данные итераций для файла с диска.

        Returns:
            True если данные были загружены, False иначе
        """
        file_path = self.parent.registry.get_path(file_name)
        if file_path:
            from app.core.processing import load_iteration_data

            try:
                exists, iteration_data = load_iteration_data(file_path)
                if exists and iteration_data:
                    self.iteration_results_data[file_name] = iteration_data
                    print(f"Данные итераций загружены для файла: {file_name}")
                    return True
            except Exception as e:
                print(f"Ошибка при загрузке данных итераций для {file_name}: {e}")
        return False

    def _check_iteration_file_exists(self, file_name: str) -> bool:
        """
        Проверяет наличие файла итераций на диске без загрузки данных.

        Args:
            file_name: Имя файла

        Returns:
            True если файл итераций существует, False иначе
        """
        try:
            file_path = self.parent.registry.get_path(file_name)
        except KeyError:
            return False

        if file_path:
            from app.core.processing import check_iteration_file_exists

            try:
                return check_iteration_file_exists(file_path)
            except Exception:
                pass
        return False

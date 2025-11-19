"""
Главный модуль управления графиками и вкладками.

Координирует работу всех подсистем отображения данных:
- PlotRenderer: отрисовка графиков и оптимизация
- TabManager: управление вкладками
- DataManager: управление данными и матрицами
- IterationManager: управление данными итераций
"""

import os
import pandas as pd
import pyqtgraph as pg
from PySide6.QtWidgets import QListWidgetItem
from typing import Optional

from app.ui.plotting.plot_renderer import PlotRenderer
from app.ui.managers.tab_manager import TabManager
from app.ui.managers.data_manager import DataManager
from app.ui.managers.iteration_manager import IterationManager
from app.utils.seq_utils import baseline_cor


class PlottingManager:
    """Главный менеджер для координации всех подсистем отображения."""

    def __init__(self, parent_window):
        """
        Инициализация главного менеджера графиков.

        Args:
            parent_window: Родительское окно (экземпляр MyMenu)
        """
        self.parent = parent_window

        # Инициализируем подсистемы
        self.renderer = PlotRenderer(parent_window)
        self.tab_manager = TabManager(parent_window)
        self.data_manager = DataManager(parent_window)
        self.iteration_manager = IterationManager(parent_window)

    # ========== Делегирование методов PlotRenderer ==========

    @property
    def MAX_POINTS_FOR_SMOOTH_RENDERING(self):
        return self.renderer.MAX_POINTS_FOR_SMOOTH_RENDERING

    @property
    def DOWNSAMPLE_FACTOR(self):
        return self.renderer.DOWNSAMPLE_FACTOR

    @property
    def current_downsample_factor(self):
        return self.renderer.current_downsample_factor

    @property
    def manual_downsample_mode(self):
        return self.renderer.manual_downsample_mode

    @property
    def disable_downsample(self):
        return self.renderer.disable_downsample

    def should_downsample(self, data: pd.DataFrame) -> bool:
        return self.renderer.should_downsample(data)

    def downsample_data(self, data: pd.DataFrame, factor: int = None):
        return self.renderer.downsample_data(data, factor)

    def get_optimal_downsample_factor(self, data: pd.DataFrame) -> int:
        return self.renderer.get_optimal_downsample_factor(data)

    def plot_data(self, plot_widget: pg.PlotWidget, data: pd.DataFrame):
        self.renderer.plot_data(plot_widget, data)

    def plot_dataframe_with_theme(
        self, plot_widget: pg.PlotWidget, data: pd.DataFrame, theme: str
    ):
        self.renderer.plot_dataframe_with_theme(plot_widget, data, theme)

    def load_data_efficiently(self, file_path: str) -> pd.DataFrame:
        return self.renderer.load_data_efficiently(file_path)

    def preload_data_async(self, file_paths: list):
        self.renderer.preload_data_async(file_paths)

    def update_performance_settings(
        self, max_points: int = None, downsample_factor: int = None
    ):
        self.renderer.update_performance_settings(max_points, downsample_factor)

    def clear_cache(self):
        self.renderer.clear_cache()

    def clear_cache_for_file(self, file_name: str):
        self.renderer.clear_cache_for_file(file_name)

    def get_performance_info(self) -> dict:
        return self.renderer.get_performance_info()

    def set_manual_downsample_mode(self, enabled: bool):
        self.renderer.set_manual_downsample_mode(enabled)

    def set_disable_downsample(self, disabled: bool):
        self.renderer.set_disable_downsample(disabled)

    def update_downsample_slider_label(self, value: int):
        pass

    # ========== Делегирование методов TabManager ==========

    @property
    def TAB_ORDER(self):
        return self.tab_manager.TAB_ORDER

    @property
    def clean_widgets_by_algorithm(self):
        return self.tab_manager.clean_widgets_by_algorithm

    def _get_tab_insert_position(self, tab_name: str) -> int:
        return self.tab_manager._get_tab_insert_position(tab_name)

    def ensure_clean_tab_for_algorithm(self, algorithm: str, algorithm_name: str):
        self.tab_manager.ensure_clean_tab_for_algorithm(algorithm, algorithm_name)

    def get_clean_widget_for_algorithm(self, algorithm: str) -> Optional[pg.PlotWidget]:
        return self.tab_manager.get_clean_widget_for_algorithm(algorithm)

    def ensure_clean_tab(self):
        self.tab_manager.ensure_clean_tab()

    def remove_clean_tab(self):
        self.tab_manager.remove_clean_tab()
        self.data_manager.current_clean_file_base = None

    def ensure_rwb_tab(self):
        self.tab_manager.ensure_rwb_tab()

    def remove_rwb_tab(self):
        self.tab_manager.remove_rwb_tab()

    def ensure_iterations_tab(self):
        self.tab_manager.ensure_iterations_tab()

    def remove_iterations_tab(self):
        self.tab_manager.remove_iterations_tab()
        self.iteration_manager.current_iterations_file = None

    def ensure_convergence_tab(self):
        self.tab_manager.ensure_convergence_tab()

    def remove_convergence_tab(self):
        self.tab_manager.remove_convergence_tab()

    def ensure_matrix_tab(self):
        self.tab_manager.ensure_matrix_tab()

    def remove_matrix_tab(self):
        self.tab_manager.remove_matrix_tab()

    def ensure_info_tab(self):
        self.tab_manager.ensure_info_tab()

    def remove_info_tab(self):
        self.tab_manager.remove_info_tab()

    # ========== Делегирование методов DataManager ==========

    @property
    def current_clean_file_base(self):
        return self.data_manager.current_clean_file_base

    @current_clean_file_base.setter
    def current_clean_file_base(self, value):
        self.data_manager.current_clean_file_base = value

    @property
    def crosstalk_matrices(self):
        return self.data_manager.crosstalk_matrices

    @property
    def crosstalk_matrices_by_algorithm(self):
        return self.data_manager.crosstalk_matrices_by_algorithm

    @property
    def original_matrices(self):
        return self.data_manager.original_matrices

    @property
    def sequence_info(self):
        return self.data_manager.sequence_info

    @property
    def sequence_info_by_algorithm(self):
        return self.data_manager.sequence_info_by_algorithm

    def store_crosstalk_matrix(self, file_name: str, matrix):
        self.data_manager.store_crosstalk_matrix(file_name, matrix)

    def store_crosstalk_matrix_for_algorithm(
        self, file_name: str, algorithm: str, matrix
    ):
        self.data_manager.store_crosstalk_matrix_for_algorithm(
            file_name, algorithm, matrix
        )

    def store_sequence_info(
        self,
        file_name: str,
        data_points: int,
        dye_names: list = None,
        smooth_data: bool = None,
        remove_baseline: bool = None,
        algorithm: str = None,
    ):
        self.data_manager.store_sequence_info(
            file_name, data_points, dye_names, smooth_data, remove_baseline, algorithm
        )

    def store_sequence_info_for_algorithm(
        self,
        file_name: str,
        algorithm: str,
        data_points: int,
        dye_names: list = None,
        smooth_data: bool = None,
        remove_baseline: bool = None,
        **kwargs,
    ):
        self.data_manager.store_sequence_info_for_algorithm(
            file_name,
            algorithm,
            data_points,
            dye_names,
            smooth_data,
            remove_baseline,
            **kwargs,
        )

    def store_matrix_difference(self, file_name: str, computed_matrix, original_matrix):
        self.data_manager.store_matrix_difference(
            file_name, computed_matrix, original_matrix
        )

    def store_matrix_difference_for_algorithm(
        self, file_name: str, algorithm: str, computed_matrix, original_matrix
    ):
        self.data_manager.store_matrix_difference_for_algorithm(
            file_name, algorithm, computed_matrix, original_matrix
        )

    # ========== Делегирование методов IterationManager ==========

    @property
    def iteration_results_data(self):
        return self.iteration_manager.iteration_results_data

    @property
    def current_iterations_file(self):
        return self.iteration_manager.current_iterations_file

    @current_iterations_file.setter
    def current_iterations_file(self, value):
        self.iteration_manager.current_iterations_file = value

    @property
    def manually_cleared_iteration_files(self):
        return self.iteration_manager.manually_cleared_iteration_files

    def store_iteration_data(
        self, file_name: str, iteration_num: int, iteration_data: dict
    ):
        self.iteration_manager.store_iteration_data(
            file_name, iteration_num, iteration_data
        )

    def finalize_iteration_results(self, file_name: str):
        self.iteration_manager.finalize_iteration_results(file_name)

    def clear_iteration_data(self, file_name: str = None):
        self.iteration_manager.clear_iteration_data(file_name)

    def has_iteration_data_for_file(self, file_name: str) -> bool:
        return self.iteration_manager.has_iteration_data_for_file(file_name)

    def show_iterations_for_file(self, file_name: str) -> bool:
        return self.iteration_manager.show_iterations_for_file(file_name)

    # ========== Комплексные методы координации ==========

    def refresh_current_plots(self):
        """Перерисовывает текущие открытые графики с новыми настройками."""
        current_item = self.parent.list_widget.currentItem()
        if current_item:
            self.file_list_click(current_item)

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

        # Удаляем clean вкладку и rwb вкладку
        self.remove_clean_tab()
        self.remove_rwb_tab()

        # Удаляем данные итераций для этого файла
        self.clear_iteration_data(base_name)

        # Удаляем данные из DataManager
        self.data_manager.remove_data_for_file(base_name)
        self.remove_matrix_tab()

        # Обновляем список файлов в интерфейсе
        self.parent.file_manager.refresh_file_list()

        return removed_files

    def show_matrix_for_file(self, file_name: str):
        """
        Показывает матрицу кросс-помех для файла, если она есть.

        Args:
            file_name: Имя файла
        """
        base_name = file_name.split(".")[0]
        print(f"[DEBUG] show_matrix_for_file вызван с file_name='{file_name}'")
        print(f"Проверка матрицы для файла: {file_name}, base_name: {base_name}")
        print(f"Доступные матрицы: {list(self.crosstalk_matrices.keys())}")
        print(f"Доступные оригинальные матрицы: {list(self.original_matrices.keys())}")

        if base_name in self.crosstalk_matrices:
            print(f"Матрица найдена для {base_name}, создаём вкладку...")
            self.ensure_matrix_tab()

            # Проверяем наличие оригинальной матрицы
            original_matrix = self.original_matrices.get(base_name, None)
            if original_matrix is None and file_name != base_name:
                original_matrix = self.original_matrices.get(file_name, None)

            if original_matrix is not None:
                print(
                    f"[DEBUG] Найдена оригинальная матрица для {base_name}, размер: {original_matrix.shape}"
                )
            else:
                print(f"[DEBUG] Оригинальная матрица НЕ найдена для {base_name}")
                print(f"[DEBUG] Пытаемся загрузить из .srd файла в реестре...")
                # Пытаемся найти и загрузить .srd файл
                for registered_file in self.parent.registry._name_to_path.keys():
                    if registered_file.startswith(
                        base_name
                    ) and registered_file.endswith(".srd"):
                        print(f"[DEBUG] Найден .srd файл в реестре: {registered_file}")
                        self.data_manager._load_original_matrix_from_srd(
                            registered_file
                        )
                        original_matrix = self.original_matrices.get(base_name, None)
                        if original_matrix is not None:
                            print(
                                f"[DEBUG] Успешно загружена оригинальная матрица из {registered_file}"
                            )
                        break

            self.parent.matrix_widget.set_matrix(
                self.crosstalk_matrices[base_name], original_matrix=original_matrix
            )
            print("Матрица установлена в виджет")
            return True
        else:
            print(f"Матрица не найдена для {base_name}")
        return False

    def show_info_for_file(self, file_name: str):
        """
        Показывает информацию о последовательности для файла.

        Args:
            file_name: Имя файла

        Returns:
            bool: True если информация найдена и показана, False иначе
        """
        base_name = file_name.split(".")[0]

        # Проверяем, есть ли информация для файла
        if base_name in self.sequence_info:
            self.ensure_info_tab()

            info = self.sequence_info[base_name]
            data_points = info.get("data_points", 0)
            dye_names = info.get("dye_names", [])
            matrix_difference = info.get("matrix_difference", None)
            smooth_data = info.get("smooth_data", None)
            remove_baseline = info.get("remove_baseline", None)
            algorithm = info.get("algorithm", None)

            # Обновляем виджет
            self.parent.info_widget.set_file_info(file_name, data_points, dye_names)
            # Всегда вызываем set_processing_results, чтобы очистить старые данные для необработанных файлов
            self.parent.info_widget.set_processing_results(
                matrix_difference, smooth_data, remove_baseline, algorithm
            )
            return True
        else:
            self.remove_info_tab()
            return False

    def file_list_click(self, item: QListWidgetItem):
        """При клике по файлу показывает Raw и, если есть, добавляет/обновляет Clean."""
        name = item.text()

        # Используем оптимизированную загрузку данных
        if not self.parent.registry.has_df(name):
            file_path = self.parent.registry.get_path(name)
            data = self.load_data_efficiently(file_path)
            self.parent.registry.set_df(name, data)

            # Загружаем информацию о последовательности при первой загрузке
            base_name = name.split(".")[0]
            if base_name not in self.sequence_info:
                # Сначала пытаемся загрузить из файла .info
                info_loaded = self.data_manager._load_sequence_info_from_file(base_name)

                # Если не удалось загрузить из файла и это .srd файл, загружаем из самого файла
                if not info_loaded and name.endswith(".srd"):
                    from app.utils.load_utils import load_dye_names_from_srd

                    try:
                        data_points = len(data)
                        dye_names = load_dye_names_from_srd(file_path)
                        self.store_sequence_info(name, data_points, dye_names)
                    except Exception as e:
                        print(
                            f"Не удалось загрузить информацию о последовательности: {e}"
                        )
                        # Сохраняем хотя бы количество точек
                        self.store_sequence_info(name, len(data), [])

            # Загружаем вычисленную матрицу из файла .matrix, если он существует
            if base_name not in self.crosstalk_matrices:
                from app.utils.load_utils import load_matrix_from_file

                matrix_file_path = os.path.splitext(file_path)[0] + ".matrix"
                if os.path.exists(matrix_file_path):
                    try:
                        computed_matrix = load_matrix_from_file(matrix_file_path)
                        print(f"Загружена вычисленная матрица из {matrix_file_path}")
                        self.store_crosstalk_matrix(name, computed_matrix)

                        # Если это .srd файл, загружаем и оригинальную матрицу для сравнения
                        if name.endswith(".srd"):
                            self.data_manager._load_original_matrix_from_srd(name)
                            original_matrix = self.original_matrices.get(
                                base_name, None
                            )
                            if original_matrix is not None:
                                print(f"Вычисляем разницу между матрицами для {name}")
                                self.store_matrix_difference(
                                    name, computed_matrix, original_matrix
                                )
                    except Exception as e:
                        print(f"Ошибка при загрузке матрицы из файла: {e}")

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
            self.remove_clean_tab()
            self.remove_rwb_tab()  # Убираем Rwb вкладку для clean файлов

            # Проверяем и показываем вкладку итераций для очищенного файла
            if self.has_iteration_data_for_file(name):
                self.show_iterations_for_file(name)
            else:
                # Убираем вкладку Iterations если нет данных для текущего файла
                self.remove_iterations_tab()
        else:
            # Кликнули на исходный файл — показываем Raw и, если есть, Clean
            raw_data = self.parent.registry.get_df(name)
            self.plot_data(self.parent.raw_plot_widget, raw_data)

            clean_found = None
            for cand in clean_candidates:
                if self.parent.registry.has_file(cand):
                    clean_found = cand
                    break
            if clean_found is not None:
                # Файл обработан - показываем Clean и Rwb
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

                # Создаем и показываем вкладку Rwb (Raw without baseline) только для обработанных файлов
                self.ensure_rwb_tab()
                # Применяем коррекцию базовой линии (функция создает копию данных автоматически)
                rwb_data = baseline_cor(raw_data)
                self.plot_data(self.parent.rwb_plot_widget, rwb_data)
            else:
                # Файл не обработан - убираем Clean и Rwb вкладки
                self.remove_clean_tab()
                self.remove_rwb_tab()

            # Проверяем и показываем вкладку итераций для этого файла только если есть данные
            if self.has_iteration_data_for_file(name):
                self.show_iterations_for_file(name)
            else:
                # Убираем вкладку Iterations если нет данных для текущего файла
                self.remove_iterations_tab()

            # Проверяем и показываем вкладку Matrix, если есть матрица для этого файла
            if not self.show_matrix_for_file(name):
                # Убираем вкладку Matrix если нет данных для текущего файла
                self.remove_matrix_tab()

        # Проверяем и показываем вкладку Info для любого файла (и исходного, и clean)
        info_shown = self.show_info_for_file(name)

        # Переключаемся на вкладку Info, если она есть, иначе на Raw
        if info_shown and self.parent.info_widget is not None:
            self.parent.view_tabs.setCurrentWidget(self.parent.info_widget)
        else:
            # Если нет info вкладки, переключаемся на Raw
            self.parent.view_tabs.setCurrentWidget(self.parent.raw_plot_widget)
            # Убираем вкладку Info если нет данных для текущего файла
            self.remove_info_tab()

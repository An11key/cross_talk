"""GUI для загрузки CSV с каналами A/G/C/T, просмотра и очистки кросс-помех.

Слева — единый список файлов. Справа — вкладки графиков:
- Raw: исходные данные;
- Clean: появляется после обработки и показывает очищенные данные.
"""

from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QListWidget,
    QFileDialog,
    QMenu,
    QTabWidget,
    QSplitter,
    QListWidgetItem,
    QApplication,
)
from PySide6.QtCore import Qt
from app.utils.generate_utils import (
    getTestData,
)
from app.utils.load_utils import load_dataframe_by_path
from app.ui.dialogs import ask_test_data_params, ask_processing_options
from app.core.processing import (
    process_and_save,
    is_file_already_processed,
    delete_processed_sequence,
)
from app.core.data_registry import DataRegistry
from app.ui.styles import DARK_THEME, LIGHT_THEME
import numpy as np
import pandas as pd
import pyqtgraph as pg
import os
import shutil


class MyMenu(QMainWindow):
    """Главное окно: список файлов слева, вкладки с графиками справа."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("My menu")

        central_widget = QSplitter()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)

        # Реестр путей и кэшей датафреймов
        self.registry = DataRegistry()

        self.create_list_widget()

        # Счётчик для автогенерации имён тестовых данных
        self.test_counter: int = 1

        # Отслеживание текущей темы (True = тёмная, False = светлая)
        self.is_dark_theme: bool = True

        # Текущая тема для графиков
        self.current_plot_theme: str = "dark"

        # Вкладки отображения над графиками
        self.view_tabs = QTabWidget()
        self.raw_plot_widget = pg.PlotWidget()
        self.view_tabs.addTab(self.raw_plot_widget, "Raw")
        self.clean_plot_widget = None  # появится после обработки

        # Слева список, справа вкладки графиков
        layout.addWidget(self.list_widget)
        layout.addWidget(self.view_tabs)

        self.create_menu_bar()

        # Применяем тёмную тему по умолчанию
        self.apply_dark_theme()

        # Автоматически загружаем файлы из processed_sequences
        self.load_processed_files()

    def _load_data_by_path(self, path: str) -> pd.DataFrame:
        """Прокси к helper-функции загрузки датафреймов по пути."""
        return load_dataframe_by_path(path)

    def load_processed_files(self):
        """Автоматически загружает последовательности из папки processed_sequences.

        Каждая папка представляет одну последовательность с исходным и clean файлами.
        В список добавляется только основной файл, но регистрируются оба.
        """
        processed_dir = "./processed_sequences"

        if not os.path.exists(processed_dir):
            return

        # Сканируем все подпапки в processed_sequences
        for folder_name in os.listdir(processed_dir):
            folder_path = os.path.join(processed_dir, folder_name)

            if not os.path.isdir(folder_path):
                continue

            # Найдём основной и clean файлы в папке
            main_file = None
            clean_file = None

            for file_name in os.listdir(folder_path):
                file_path = os.path.join(folder_path, file_name)

                if file_name.lower().endswith((".csv", ".srd")):
                    if "_clean" in file_name.lower():
                        clean_file = (file_name, file_path)
                    else:
                        main_file = (file_name, file_path)

            # Регистрируем оба файла, но в список добавляем только основной
            if main_file:
                main_name, main_path = main_file

                # Проверяем, что последовательность ещё не добавлена
                if not self.registry.has_file(main_name):
                    # Регистрируем основной файл
                    self.registry.set_file(main_name, main_path)

                    # Регистрируем clean файл, если он есть
                    if clean_file:
                        clean_name, clean_path = clean_file
                        self.registry.set_file(clean_name, clean_path)

                    # В список добавляем только основной файл
                    self.list_widget.addItem(main_name)

    def create_list_widget(self):
        """Создаёт левый список файлов и подключает события клика и ПКМ."""
        self.list_widget = QListWidget()
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)  # type: ignore
        self.list_widget.itemClicked.connect(self.file_list_click)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)

    def create_menu_bar(self):
        """Создаёт меню и действие открытия файлов."""
        menu_bar = self.menuBar()

        # Меню File
        file_menu = menu_bar.addMenu("&File")
        action1 = file_menu.addAction("Open")
        action2 = file_menu.addAction("Generate test data")
        action1.triggered.connect(self.open_action)
        action2.triggered.connect(self.generate_test_data)

        # Меню View
        view_menu = menu_bar.addMenu("&View")
        self.theme_action = view_menu.addAction("Переключить на светлую тему")
        self.theme_action.triggered.connect(self.toggle_theme)

    def open_action(self):
        """Хэндлер для File → Open."""
        self.open_file_dialog()

    def apply_dark_theme(self):
        """Применяет тёмную тему при инициализации."""
        app = QApplication.instance()
        if app is None:
            return
        app.setStyleSheet(DARK_THEME)

    def toggle_theme(self):
        """Переключает между светлой и тёмной темой."""
        app = QApplication.instance()
        if app is None:
            return

        if self.is_dark_theme:
            # Переключаем на светлую тему
            app.setStyleSheet(LIGHT_THEME)
            self.theme_action.setText("Переключить на тёмную тему")
            self.is_dark_theme = False

            # Устанавливаем белый фон для графиков
            self.set_plot_background("white")
        else:
            # Переключаем на тёмную тему
            app.setStyleSheet(DARK_THEME)
            self.theme_action.setText("Переключить на светлую тему")
            self.is_dark_theme = True

            # Возвращаем тёмный фон для графиков
            self.set_plot_background("dark")

    def set_plot_background(self, theme):
        """Устанавливает фон для графиков в зависимости от темы."""
        if theme == "white":
            # Белый фон для светлой темы
            background_color = "white"
            foreground_color = "black"
        else:
            # Тёмный фон для тёмной темы (по умолчанию pyqtgraph)
            background_color = None
            foreground_color = "white"

        # Применяем к существующим виджетам графиков
        if self.raw_plot_widget:
            if background_color:
                self.raw_plot_widget.setBackground(background_color)
            else:
                self.raw_plot_widget.setBackground("default")

        if self.clean_plot_widget:
            if background_color:
                self.clean_plot_widget.setBackground(background_color)
            else:
                self.clean_plot_widget.setBackground("default")

        # Сохраняем текущую тему для использования при отрисовке
        self.current_plot_theme = theme

        # Перерисовываем существующие графики с новыми цветами
        self.redraw_existing_plots()

    def redraw_existing_plots(self):
        """Перерисовывает все существующие графики с актуальными цветами."""
        # Получаем текущий выбранный файл
        current_item = self.list_widget.currentItem()
        if current_item:
            # Симулируем клик по текущему элементу для перерисовки
            self.file_list_click(current_item)

    def generate_test_data(self):
        """Запрашивает параметры и генерирует тестовые данные, добавляя их в список."""
        params = ask_test_data_params(self)
        if params is None:
            return
        n, peak_space, detail, noise_level = params

        # Используем разумные значения по умолчанию для ширины и высоты
        peak_width = 1.3
        peak_height = 1000

        data, M = getTestData(
            n, peak_space, peak_width, peak_height, detail, noise_level
        )

        # Формируем имя и сохраняем как реальный CSV, чтобы остальной функционал работал единообразно
        name = f"Test data {self.test_counter}"
        folder = f"gen_data/TestData_{self.test_counter}_seq"
        if not os.path.exists(folder):
            os.makedirs(folder)
        csv_path = os.path.join(folder, f"TestData_{self.test_counter}.csv")
        data.to_csv(csv_path, sep=";", index=False, header=False)

        # Регистрируем файл и кэшируем DataFrame
        self.registry.set_file(name, csv_path)
        self.registry.set_df(name, data)

        # Добавляем в список и показываем
        self.list_widget.addItem(name)
        self.test_counter += 1

        # Рисуем Raw и переключаемся на него
        self.plot_data(self.raw_plot_widget, data)
        self.view_tabs.setCurrentWidget(self.raw_plot_widget)

    def open_file_dialog(self):
        """Показывает диалог выбора и добавляет выбранные файлы в список."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Выберете файлы",
            "",
            "Data files (*.csv *.srd);;CSV (*.csv);;SRD (*.srd);;All files (*)",
        )
        names = [os.path.basename(path) for path in files]
        for name, path in zip(names, files):
            self.registry.set_file(name, path)
            self.list_widget.addItem(name)

    def show_context_menu(self, pos):
        """Контекстное меню по ПКМ: содержит пункт "Запуск" для обработки файла."""
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        action = menu.addAction("Запуск")
        action2 = menu.addAction("Удалить")
        action.triggered.connect(lambda: self.file_process(item.text()))
        action2.triggered.connect(lambda: self.delete_file(item))
        menu.exec(self.list_widget.mapToGlobal(pos))

    def delete_file(self, item: QListWidgetItem):
        """Удаляет файл из списка и соответствующую папку из processed_sequences."""
        name = item.text()

        # Получаем путь к исходному файлу
        if self.registry.has_file(name):
            file_path = self.registry.get_path(name)

            # Удаляем обработанные файлы из processed_sequences
            delete_processed_sequence(file_path)

        # Удаляем из списка и реестра
        self.list_widget.takeItem(self.list_widget.row(item))
        self.registry.remove(name)

        # Также удаляем связанный clean файл из реестра, если он есть
        base_name = os.path.splitext(name)[0]
        clean_candidates = [f"{base_name}_clean.csv", f"{base_name}_clean.srd"]
        for clean_name in clean_candidates:
            if self.registry.has_file(clean_name):
                self.registry.remove(clean_name)

    def file_process(self, name):
        """Обрабатывает файл: baseline → оценка W → очистка → сохранение и показ.

        Также печатает оценённую матрицу кросс-помех в терминал.
        """
        path = self.registry.get_path(name)

        # Проверяем, не обрабатывался ли файл ранее
        already_processed, existing_clean_path = is_file_already_processed(path)

        if already_processed:
            print(
                f"Файл уже обработан. Используем существующий результат: {existing_clean_path}"
            )
            # Загружаем существующий очищенный файл
            clean_data = self._load_data_by_path(existing_clean_path)
            clean_path = existing_clean_path
        else:
            # Показываем диалог выбора параметров обработки
            processing_options = ask_processing_options(self)
            if processing_options is None:
                # Пользователь отменил обработку
                return

            smooth_data, remove_baseline = processing_options

            # Обрабатываем файл
            if not self.registry.has_df(name):
                self.registry.set_df(name, self._load_data_by_path(path))

            data = self.registry.get_df(name)
            clean_data, clean_path = process_and_save(
                path, data, smooth_data, remove_baseline
            )

        # Кешируем очищенный файл
        clean_name = os.path.basename(clean_path)
        self.registry.set_file(clean_name, clean_path)
        self.registry.set_df(clean_name, clean_data)

        # Обеспечиваем вкладку Clean и рисуем данные
        self.ensure_clean_tab()
        self.plot_data(self.clean_plot_widget, clean_data)
        self.view_tabs.setCurrentWidget(self.clean_plot_widget)

    def plot_data(self, plot_widget: pg.PlotWidget, data: pd.DataFrame):
        """Адаптер к helper-функции отрисовки датафреймов с учётом темы."""
        self.plot_dataframe_with_theme(plot_widget, data, self.current_plot_theme)

    def plot_dataframe_with_theme(
        self, plot_widget: pg.PlotWidget, data: pd.DataFrame, theme: str
    ) -> None:
        """Отрисовывает датафрейм с цветами, подходящими для текущей темы."""
        plot_widget.clear()
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

        for i, column in enumerate(data.columns):
            y = pd.to_numeric(data[column], errors="coerce").fillna(0.0).astype(float)
            x = np.arange(len(y), dtype=float)
            plot_widget.plot(
                x,
                y.values,
                pen=pg.mkPen(color=colors[i % len(colors)], width=1.5),
                name=column,
            )

    def create_folder(self, path):
        """Создаёт папку <name>_seq и копирует туда исходный файл (если нужно)."""

        name = os.path.basename(path)
        only_name = os.path.splitext(name)[0]
        folder = f"./{only_name}_seq"
        if not os.path.exists(folder):
            os.makedirs(folder)
            shutil.copy(path, folder)
            self.registry.set_file(name, folder)

    def file_list_click(self, item: QListWidgetItem):
        """При клике по файлу показывает Raw и, если есть, добавляет/обновляет Clean."""
        name = item.text()
        if not self.registry.has_df(name):
            self.registry.set_df(
                name, self._load_data_by_path(self.registry.get_path(name))
            )

        # Определяем, исходный это файл или очищенный
        is_clean_file = "_clean" in os.path.splitext(name)[0]
        base_no_ext, ext = os.path.splitext(name)
        base_name = base_no_ext.replace("_clean", "")
        # Варианты имён очищенного файла: такое же расширение, или csv (для исходного .srd)
        clean_candidates = [f"{base_name}_clean{ext}"]
        if ext.lower() == ".srd":
            clean_candidates.append(f"{base_name}_clean.csv")

        if is_clean_file:
            # Кликнули на очищенный файл — показываем только его
            self.plot_data(self.raw_plot_widget, self.registry.get_df(name))
            self.view_tabs.setCurrentWidget(self.raw_plot_widget)
            self.remove_clean_tab()
        else:
            # Кликнули на исходный файл — показываем Raw и, если есть, Clean
            self.plot_data(self.raw_plot_widget, self.registry.get_df(name))
            self.view_tabs.setCurrentWidget(self.raw_plot_widget)

            clean_found = None
            for cand in clean_candidates:
                if self.registry.has_file(cand):
                    clean_found = cand
                    break
            if clean_found is not None:
                if not self.registry.has_df(clean_found):
                    self.registry.set_df(
                        clean_found,
                        self._load_data_by_path(self.registry.get_path(clean_found)),
                    )
                self.ensure_clean_tab()
                self.plot_data(
                    self.clean_plot_widget, self.registry.get_df(clean_found)
                )
            else:
                self.remove_clean_tab()

    def ensure_clean_tab(self):
        """Создаёт вкладку Clean при первом обращении к ней."""
        if self.clean_plot_widget is None:
            self.clean_plot_widget = pg.PlotWidget()
            self.view_tabs.addTab(self.clean_plot_widget, "Clean")

            # Применяем текущую тему к новому виджету
            theme = "white" if not self.is_dark_theme else "dark"
            if theme == "white":
                self.clean_plot_widget.setBackground("white")
            else:
                self.clean_plot_widget.setBackground("default")

    def remove_clean_tab(self):
        """Удаляет вкладку Clean, если очищенных данных для выбранного файла нет."""
        if self.clean_plot_widget is not None:
            idx = self.view_tabs.indexOf(self.clean_plot_widget)
            if idx != -1:
                self.view_tabs.removeTab(idx)
            self.clean_plot_widget = None

"""
Основной класс главного окна приложения.

Этот модуль содержит класс MyMenu - главное окно приложения,
которое координирует работу всех менеджеров и компонентов.
"""

from typing import Optional, List, Union
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QListWidget, QTabWidget
from PySide6.QtCore import QSettings, Qt
from app.core.data_registry import DataRegistry
from app.ui.ui_components import UIComponentsFactory
from app.ui.theme_manager import ThemeManager
from app.ui.file_operations import FileOperationsManager
from app.ui.data_processing import DataProcessingManager
from app.ui.plotting import PlottingManager
from app.utils.load_utils import load_dataframe_by_path


class MyMenu(QMainWindow):
    """Главное окно: список файлов слева, вкладки с графиками справа."""

    # Константы для настроек UI
    WINDOW_TITLE = "Base"
    INITIAL_WINDOW_WIDTH = 800
    INITIAL_WINDOW_HEIGHT = 600
    MIN_WINDOW_WIDTH = 600
    MIN_WINDOW_HEIGHT = 400
    LIST_WIDGET_MIN_WIDTH = 200
    LIST_WIDGET_MAX_WIDTH = 400
    DEFAULT_SPLITTER_SIZES = [250, 550]
    SETTINGS_ORGANIZATION = "CrossTalkAnalyzer"
    SETTINGS_APPLICATION = "MainWindow"

    def __init__(self):
        super().__init__()

        # Основные компоненты (будут инициализированы в _init_managers)
        self.registry: DataRegistry
        self.ui_factory: UIComponentsFactory
        self.theme_manager: ThemeManager
        self.file_manager: FileOperationsManager
        self.data_manager: DataProcessingManager
        self.plot_manager: PlottingManager

        # UI компоненты (будут созданы в _create_ui)
        self.list_widget: QListWidget
        self.view_tabs: QTabWidget
        self.main_splitter: QWidget
        self.progress_panel: QWidget
        self.cancel_button: QWidget
        self.downsample_slider: QWidget
        self.downsample_auto_button: QWidget
        self.disable_downsample_checkbox: QWidget
        self.iterations_widget: Optional[QWidget]

        # Настройки
        self.settings: QSettings

        # Инициализация
        self._init_window()
        self._init_settings()
        self._init_managers()
        self._create_ui()
        self._connect_signals()
        self._apply_initial_settings()

        # Восстанавливаем состояние окна после создания UI
        self.restore_window_state()

    def _init_window(self) -> None:
        """Инициализация основных настроек окна."""
        self.setWindowTitle(self.WINDOW_TITLE)

        # Устанавливаем начальный размер окна
        self.resize(self.INITIAL_WINDOW_WIDTH, self.INITIAL_WINDOW_HEIGHT)

        # Устанавливаем минимальный размер окна для удобства использования
        self.setMinimumSize(self.MIN_WINDOW_WIDTH, self.MIN_WINDOW_HEIGHT)

    def _init_settings(self) -> None:
        """Инициализация системы настроек."""
        self.settings = QSettings(self.SETTINGS_ORGANIZATION, self.SETTINGS_APPLICATION)

    def _init_managers(self) -> None:
        """Инициализация всех менеджеров."""
        self.registry = DataRegistry()
        self.ui_factory = UIComponentsFactory(self)
        self.theme_manager = ThemeManager(self)
        self.file_manager = FileOperationsManager(self)
        self.data_manager = DataProcessingManager(self)
        self.plot_manager = PlottingManager(self)

    def _create_ui(self) -> None:
        """Создание пользовательского интерфейса."""
        # Создаем основной layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        self.setCentralWidget(main_widget)

        # Создаем основной splitter
        self.main_splitter = self.ui_factory.create_main_splitter()
        main_layout.addWidget(self.main_splitter)

        # Создаем UI компоненты
        self._create_ui_components()

        # Настраиваем layout
        self._setup_ui_layout()

        # Создаем панель прогресса
        self.ui_factory.create_progress_panel()
        main_layout.addWidget(self.progress_panel)

        # Создаем меню
        self.ui_factory.create_menu_bar()

    def _create_ui_components(self) -> None:
        """Создание основных UI компонентов."""
        self.ui_factory.create_list_widget()
        self.ui_factory.create_plot_tabs()
        downsample_control_panel = self.ui_factory.create_downsample_control_panel()

        # Создаем правую часть с графиками и управлением
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.view_tabs)
        right_layout.addWidget(downsample_control_panel)

        # Добавляем виджеты в splitter
        self.main_splitter.addWidget(self.list_widget)
        self.main_splitter.addWidget(right_widget)

    def _setup_ui_layout(self) -> None:
        """Настройка размеров и расположения UI элементов."""
        # Настраиваем список файлов с ограничениями по ширине
        self.list_widget.setMinimumWidth(self.LIST_WIDGET_MIN_WIDTH)
        self.list_widget.setMaximumWidth(self.LIST_WIDGET_MAX_WIDTH)

        # Восстанавливаем сохранённые размеры или устанавливаем по умолчанию
        self._restore_splitter_sizes()

    def _restore_splitter_sizes(self) -> None:
        """Восстановление сохранённых размеров splitter."""
        saved_sizes = self.settings.value("splitterSizes", self.DEFAULT_SPLITTER_SIZES)
        if isinstance(saved_sizes, list) and len(saved_sizes) == 2:
            self.main_splitter.setSizes([int(size) for size in saved_sizes])
        else:
            self.main_splitter.setSizes(self.DEFAULT_SPLITTER_SIZES)

    def _connect_signals(self) -> None:
        """Подключение всех сигналов."""
        # Основные сигналы списка файлов
        self.list_widget.itemClicked.connect(self.plot_manager.file_list_click)
        self.list_widget.customContextMenuRequested.connect(
            self.file_manager.show_context_menu
        )

        # Сигналы обработки данных
        self.cancel_button.clicked.connect(self.data_manager.cancel_processing)

        # Сигналы управления прореживанием
        self._connect_downsample_signals()

    def _connect_downsample_signals(self) -> None:
        """Подключение сигналов управления прореживанием."""
        self.downsample_slider.valueChanged.connect(self.on_downsample_slider_changed)
        self.downsample_auto_button.clicked.connect(self.on_auto_downsample_clicked)
        self.disable_downsample_checkbox.stateChanged.connect(
            self.on_disable_downsample_changed
        )

    def _apply_initial_settings(self) -> None:
        """Применение начальных настроек."""
        # Применяем тёмную тему по умолчанию
        self.theme_manager.apply_dark_theme()

        # Автоматически загружаем файлы из processed_sequences
        self.file_manager.load_processed_files()

    def _load_data_by_path(self, path: str):
        """Прокси к helper-функции загрузки датафреймов по пути."""
        return load_dataframe_by_path(path)

    # ================================================================================
    # ДЕЛЕГИРОВАНИЕ МЕТОДОВ МЕНЕДЖЕРАМ
    # ================================================================================

    # --- Файловые операции ---

    def open_action(self) -> None:
        """Хэндлер для File → Open."""
        self.file_manager.open_file_dialog()

    def generate_test_data(self) -> None:
        """Хэндлер для File → Generate test data."""
        self.file_manager.generate_test_data()

    def delete_file(self, item) -> None:
        """Удаляет файл из списка."""
        self.file_manager.delete_file(item)

    # --- Управление темой ---

    def toggle_theme(self) -> None:
        """Переключает между светлой и тёмной темой."""
        self.theme_manager.toggle_theme()

    # --- Обработка данных ---

    def file_process(self, name: str) -> None:
        """Обрабатывает файл."""
        self.data_manager.process_file(name)

    # --- Построение графиков ---

    def plot_data(self, plot_widget, data) -> None:
        """Отрисовывает данные."""
        self.plot_manager.plot_data(plot_widget, data)

    def ensure_clean_tab(self) -> None:
        """Обеспечивает вкладку Clean."""
        self.plot_manager.ensure_clean_tab()

    def remove_clean_tab(self) -> None:
        """Удаляет вкладку Clean."""
        self.plot_manager.remove_clean_tab()

    def ensure_iterations_tab(self) -> None:
        """Обеспечивает вкладку Iterations."""
        self.plot_manager.ensure_iterations_tab()

    def remove_iterations_tab(self) -> None:
        """Удаляет вкладку Iterations."""
        self.plot_manager.remove_iterations_tab()

    # ================================================================================
    # ОБРАБОТЧИКИ СОБЫТИЙ ОБРАБОТКИ ДАННЫХ
    # ================================================================================

    def on_progress_updated(self, progress: int, message: str) -> None:
        """Обработчик обновления прогресса."""
        self.data_manager.on_progress_updated(progress, message)

    def on_processing_finished(self, clean_data, clean_path: str) -> None:
        """Обработчик завершения обработки."""
        self.data_manager.on_processing_finished(clean_data, clean_path)

    def on_processing_error(self, error_message: str) -> None:
        """Обработчик ошибки обработки."""
        self.data_manager.on_processing_error(error_message)

    # ================================================================================
    # ОБРАБОТЧИКИ УПРАВЛЕНИЯ ПРОРЕЖИВАНИЕМ
    # ================================================================================

    def on_downsample_slider_changed(self, value: int) -> None:
        """Обработчик изменения значения ползунка прореживания."""
        self.plot_manager.set_manual_downsample_mode(True)
        self.plot_manager.update_downsample_slider_label(value)
        self.plot_manager.refresh_current_plots()

    def on_auto_downsample_clicked(self) -> None:
        """Обработчик нажатия кнопки автоматического прореживания."""
        self.plot_manager.set_manual_downsample_mode(False)

        optimal_factor = self._get_optimal_downsample_factor()
        self.downsample_slider.setValue(optimal_factor)
        self.plot_manager.update_downsample_slider_label(optimal_factor)
        self.plot_manager.refresh_current_plots()

    def on_disable_downsample_changed(self, state: int) -> None:
        """Обработчик изменения состояния флажка отключения прореживания."""
        disabled = state == Qt.CheckState.Checked.value
        self.plot_manager.set_disable_downsample(disabled)

        if disabled:
            self.plot_manager.refresh_current_plots()

    def _get_optimal_downsample_factor(self) -> int:
        """Получает оптимальный коэффициент прореживания для текущих данных."""
        current_item = self.list_widget.currentItem()
        if current_item:
            name = current_item.text()
            if self.registry.has_df(name):
                data = self.registry.get_df(name)
                return self.plot_manager.get_optimal_downsample_factor(data)
        return 1

    # ================================================================================
    # УПРАВЛЕНИЕ СОСТОЯНИЕМ ОКНА
    # ================================================================================

    def save_splitter_state(self) -> None:
        """Сохраняет текущие размеры панелей splitter."""
        if hasattr(self, "main_splitter"):
            sizes = self.main_splitter.sizes()
            self.settings.setValue("splitterSizes", sizes)

    def save_window_state(self) -> None:
        """Сохраняет размер и позицию окна."""
        self.settings.setValue("windowGeometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())

    def restore_window_state(self) -> None:
        """Восстанавливает размер и позицию окна."""
        geometry = self.settings.value("windowGeometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            # Если сохраненной геометрии нет, используем значения по умолчанию
            self.resize(self.INITIAL_WINDOW_WIDTH, self.INITIAL_WINDOW_HEIGHT)

        state = self.settings.value("windowState")
        if state:
            self.restoreState(state)

    def reset_splitter_layout(self) -> None:
        """Сбрасывает размеры панелей к значениям по умолчанию."""
        if hasattr(self, "main_splitter"):
            self.main_splitter.setSizes(self.DEFAULT_SPLITTER_SIZES)
            self.save_splitter_state()

    def closeEvent(self, event) -> None:
        """Обработчик закрытия окна - сохраняет настройки."""
        self.save_splitter_state()
        self.save_window_state()
        super().closeEvent(event)

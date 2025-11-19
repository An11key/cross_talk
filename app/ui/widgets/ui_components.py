"""
Фабрика UI компонентов для главного окна приложения.

Этот модуль содержит функции для создания и настройки
всех основных UI элементов приложения.
"""

from PySide6.QtWidgets import (
    QListWidget,
    QProgressBar,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QWidget,
    QTabWidget,
    QSplitter,
    QSlider,
    QCheckBox,
    QMenu,
)
from PySide6.QtCore import Qt, QPoint
import pyqtgraph as pg


class UIComponentsFactory:
    """Фабрика для создания UI компонентов главного окна."""

    def __init__(self, parent_window):
        """
        Инициализация фабрики.

        Args:
            parent_window: Родительское окно (экземпляр MyMenu)
        """
        self.parent = parent_window

    def create_list_widget(self):
        """Создаёт левый список файлов и подключает события клика и ПКМ."""
        self.parent.list_widget = QListWidget()
        self.parent.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)  # type: ignore
        # Включаем режим множественного выбора
        self.parent.list_widget.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        return self.parent.list_widget

    def create_progress_panel(self):
        """Создаёт панель прогресса внизу окна."""
        self.parent.progress_panel = QWidget()
        self.parent.progress_panel.setFixedHeight(60)
        layout = QHBoxLayout(self.parent.progress_panel)
        layout.setContentsMargins(10, 5, 10, 5)

        # Метка статуса
        self.parent.status_label = QLabel("Готов к обработке")
        self.parent.status_label.setStyleSheet("font-size: 11px;")
        layout.addWidget(self.parent.status_label)

        # Прогресс-бар
        self.parent.progress_bar = QProgressBar()
        self.parent.progress_bar.setRange(0, 100)
        self.parent.progress_bar.setValue(0)
        self.parent.progress_bar.setVisible(False)  # Скрываем по умолчанию
        layout.addWidget(self.parent.progress_bar)

        # Кнопка отмены
        self.parent.cancel_button = QPushButton("Отмена")
        self.parent.cancel_button.setVisible(False)  # Скрываем по умолчанию
        layout.addWidget(self.parent.cancel_button)

        # Устанавливаем соотношение размеров
        layout.setStretchFactor(self.parent.status_label, 1)
        layout.setStretchFactor(self.parent.progress_bar, 2)
        layout.setStretchFactor(self.parent.cancel_button, 0)

        return self.parent.progress_panel

    def create_menu_bar(self):
        """Создаёт меню и действие открытия файлов."""
        menu_bar = self.parent.menuBar()

        # Меню File
        file_menu = menu_bar.addMenu("&File")
        action1 = file_menu.addAction("Open")
        action2 = file_menu.addAction("Generate test data")
        
        # Разделитель
        file_menu.addSeparator()
        
        # Экспорт статистики
        action3 = file_menu.addAction("Статистика")
        action3.setToolTip("Экспортировать всю статистику в CSV файл")
        
        action1.triggered.connect(self.parent.open_action)
        action2.triggered.connect(self.parent.generate_test_data)
        action3.triggered.connect(self.parent.export_statistics)

        # Меню View
        view_menu = menu_bar.addMenu("&View")
        self.parent.theme_action = view_menu.addAction("Переключить на светлую тему")
        self.parent.theme_action.triggered.connect(self.parent.toggle_theme)

        # Разделитель
        view_menu.addSeparator()

        # Действие переключения видимости панели детализации
        self.parent.toggle_detail_action = view_menu.addAction("Показать детализацию")
        self.parent.toggle_detail_action.triggered.connect(
            self.parent.toggle_detail_panel
        )

        # Разделитель
        view_menu.addSeparator()

        # Действие сброса размеров панелей
        self.parent.reset_layout_action = view_menu.addAction(
            "Сбросить размеры панелей"
        )
        self.parent.reset_layout_action.triggered.connect(
            self.parent.reset_splitter_layout
        )

        return menu_bar

    def create_plot_tabs(self):
        """Создаёт вкладки отображения над графиками."""
        self.parent.view_tabs = QTabWidget()
        self.parent.raw_plot_widget = pg.PlotWidget()
        self.parent.view_tabs.addTab(self.parent.raw_plot_widget, "Raw")
        self.parent.rwb_plot_widget = None  # появится при клике на файл
        self.parent.clean_plot_widget = None  # появится после обработки
        self.parent.iterations_widget = None  # появится после обработки
        self.parent.convergence_widget = None  # появится после обработки
        self.parent.matrix_widget = None  # появится после обработки
        self.parent.info_widget = None  # появится при клике на файл

        # Включаем контекстное меню для вкладок
        self.parent.view_tabs.setContextMenuPolicy(Qt.CustomContextMenu)
        self.parent.view_tabs.customContextMenuRequested.connect(
            self._show_tab_context_menu
        )

        return self.parent.view_tabs

    def _show_tab_context_menu(self, position: QPoint):
        """Показывает контекстное меню для вкладок."""
        # Определяем, на какой вкладке был клик
        tab_bar = self.parent.view_tabs.tabBar()

        # Преобразуем позицию от QTabWidget к QTabBar
        tab_bar_position = tab_bar.mapFromParent(position)
        tab_index = tab_bar.tabAt(tab_bar_position)

        if tab_index == -1:
            return  # Клик не по вкладке

        tab_text = self.parent.view_tabs.tabText(tab_index)

        # Показываем меню только для вкладки "Clean"
        if tab_text == "Clean":
            menu = QMenu(self.parent)
            delete_action = menu.addAction("Удалить")
            delete_action.triggered.connect(self._delete_clean_tab)

            # Показываем меню в глобальных координатах
            global_position = self.parent.view_tabs.mapToGlobal(position)
            menu.exec(global_position)

    def _delete_clean_tab(self):
        """Удаляет clean данные при клике на вкладку."""
        # Используем сохраненное базовое имя файла для clean вкладки
        if self.parent.plot_manager.current_clean_file_base:
            base_name = self.parent.plot_manager.current_clean_file_base
            # Удаляем clean данные
            self.parent.plot_manager.remove_clean_data_for_file(base_name)
        else:
            # Fallback: определяем базовое имя по текущему выбранному файлу
            current_item = self.parent.list_widget.currentItem()
            if current_item:
                file_name = current_item.text()

                # Определяем базовое имя файла
                if "_clean" in file_name:
                    base_name = file_name.split("_clean")[0]
                else:
                    parts = file_name.split(".")
                    base_name = parts[0]

                # Удаляем clean данные
                self.parent.plot_manager.remove_clean_data_for_file(base_name)

    def create_downsample_control_panel(self):
        """Создаёт панель управления прореживанием графиков."""
        control_panel = QWidget()
        control_panel.setFixedHeight(50)
        layout = QHBoxLayout(control_panel)
        layout.setContentsMargins(10, 5, 10, 5)

        # Метка
        downsample_label = QLabel("Детализация:")
        downsample_label.setStyleSheet("font-size: 11px;")
        layout.addWidget(downsample_label)

        # Ползунок прореживания
        self.parent.downsample_slider = QSlider(Qt.Horizontal)
        self.parent.downsample_slider.setMinimum(1)  # Минимум - без прореживания
        self.parent.downsample_slider.setMaximum(50)  # Максимум - прореживание в 50 раз
        self.parent.downsample_slider.setValue(1)  # По умолчанию без прореживания
        self.parent.downsample_slider.setTickPosition(QSlider.TicksBelow)
        self.parent.downsample_slider.setTickInterval(10)
        layout.addWidget(self.parent.downsample_slider)

        # Кнопка "Авто"
        auto_button = QPushButton("Авто")
        auto_button.setFixedWidth(60)
        auto_button.setToolTip("Автоматическое прореживание для производительности")
        layout.addWidget(auto_button)

        # Чекбокс "Отключить прореживание"
        disable_checkbox = QCheckBox("Отключить")
        disable_checkbox.setToolTip("Полностью отключить прореживание данных")
        layout.addWidget(disable_checkbox)

        # Устанавливаем соотношение размеров
        layout.setStretchFactor(downsample_label, 0)
        layout.setStretchFactor(self.parent.downsample_slider, 3)
        layout.setStretchFactor(auto_button, 0)
        layout.setStretchFactor(disable_checkbox, 0)

        # Сохраняем ссылки
        self.parent.downsample_auto_button = auto_button
        self.parent.disable_downsample_checkbox = disable_checkbox

        return control_panel

    def create_main_splitter(self):
        """Создаёт основной QSplitter для списка и графиков."""
        splitter = QSplitter(Qt.Horizontal)

        # Устанавливаем минимальные размеры для панелей
        splitter.setMinimumSize(800, 400)

        # Настраиваем поведение разделителя
        splitter.setChildrenCollapsible(
            False
        )  # Не позволяем панелям полностью сворачиваться
        splitter.setStretchFactor(0, 0)  # Список файлов не растягивается
        splitter.setStretchFactor(1, 1)  # Графики растягиваются

        return splitter
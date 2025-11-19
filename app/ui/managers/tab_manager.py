"""
Модуль управления вкладками интерфейса.

Содержит класс TabManager для создания, удаления и управления
вкладками просмотра данных.
"""

import pyqtgraph as pg
from typing import Optional, Dict
from app.ui.operations.iteration_results import IterationResultsWidget
from app.ui.widgets.convergence_widget import ConvergenceWidget
from app.ui.widgets.matrix_widget import MatrixWidget
from app.ui.widgets.sequence_info_widget import SequenceInfoWidget


class TabManager:
    """Менеджер для управления вкладками интерфейса."""

    # Порядок вкладок (используется для вставки в правильной последовательности)
    TAB_ORDER = ["Info", "Raw", "Rwb", "Clean", "Iterations", "Convergence", "Matrix"]

    def __init__(self, parent_window):
        """
        Инициализация менеджера вкладок.

        Args:
            parent_window: Родительское окно (экземпляр MyMenu)
        """
        self.parent = parent_window
        
        # Виджеты Clean для каждого алгоритма
        # {algorithm: plot_widget}
        self.clean_widgets_by_algorithm: Dict[str, pg.PlotWidget] = {}

    def _get_tab_insert_position(self, tab_name: str) -> int:
        """
        Определяет позицию для вставки вкладки, чтобы соблюсти правильный порядок.

        Args:
            tab_name: Название вкладки

        Returns:
            Индекс позиции для вставки вкладки
        """
        if tab_name not in self.TAB_ORDER:
            return self.parent.view_tabs.count()  # В конец, если не известна

        target_index = self.TAB_ORDER.index(tab_name)

        # Ищем позицию для вставки
        insert_position = 0
        for i in range(self.parent.view_tabs.count()):
            current_tab_name = self.parent.view_tabs.tabText(i)
            if current_tab_name in self.TAB_ORDER:
                current_index = self.TAB_ORDER.index(current_tab_name)
                if current_index < target_index:
                    insert_position = i + 1

        return insert_position

    def ensure_clean_tab_for_algorithm(self, algorithm: str, algorithm_name: str):
        """Создаёт вкладку Clean для конкретного алгоритма.
        
        Args:
            algorithm: Идентификатор алгоритма (например, 'estimate_crosstalk')
            algorithm_name: Отображаемое имя алгоритма (например, 'Метод 1')
        """
        if algorithm not in self.clean_widgets_by_algorithm:
            widget = pg.PlotWidget()
            self.clean_widgets_by_algorithm[algorithm] = widget
            
            # Вставляем вкладку Clean в правильную позицию
            insert_pos = self._get_tab_insert_position("Clean")
            # Если уже есть другие вкладки Clean, вставляем после них
            for i in range(self.parent.view_tabs.count()):
                tab_text = self.parent.view_tabs.tabText(i)
                if "Clean" in tab_text:
                    insert_pos = i + 1
            
            tab_name = f"Clean ({algorithm_name})"
            self.parent.view_tabs.insertTab(insert_pos, widget, tab_name)

            # Применяем текущую тему к новому виджету
            theme = "white" if not self.parent.theme_manager.is_dark_theme else "dark"
            if theme == "white":
                widget.setBackground("white")
            else:
                widget.setBackground("default")
    
    def get_clean_widget_for_algorithm(self, algorithm: str) -> Optional[pg.PlotWidget]:
        """Возвращает виджет Clean для конкретного алгоритма.
        
        Args:
            algorithm: Идентификатор алгоритма
            
        Returns:
            Виджет или None если не найден
        """
        return self.clean_widgets_by_algorithm.get(algorithm, None)
    
    def ensure_clean_tab(self):
        """Создаёт вкладку Clean при первом обращении к ней."""
        if self.parent.clean_plot_widget is None:
            self.parent.clean_plot_widget = pg.PlotWidget()
            # Вставляем вкладку Clean в правильную позицию
            insert_pos = self._get_tab_insert_position("Clean")
            self.parent.view_tabs.insertTab(
                insert_pos, self.parent.clean_plot_widget, "Clean"
            )

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

    def ensure_rwb_tab(self):
        """Создаёт вкладку Rwb (Raw without baseline) при первом обращении к ней."""
        if self.parent.rwb_plot_widget is None:
            self.parent.rwb_plot_widget = pg.PlotWidget()
            # Вставляем вкладку Rwb в правильную позицию
            insert_pos = self._get_tab_insert_position("Rwb")
            self.parent.view_tabs.insertTab(
                insert_pos, self.parent.rwb_plot_widget, "Rwb"
            )

            # Применяем текущую тему к новому виджету
            theme = "white" if not self.parent.theme_manager.is_dark_theme else "dark"
            if theme == "white":
                self.parent.rwb_plot_widget.setBackground("white")
            else:
                self.parent.rwb_plot_widget.setBackground("default")

    def remove_rwb_tab(self):
        """Удаляет вкладку Rwb."""
        if self.parent.rwb_plot_widget is not None:
            idx = self.parent.view_tabs.indexOf(self.parent.rwb_plot_widget)
            if idx != -1:
                self.parent.view_tabs.removeTab(idx)
            self.parent.rwb_plot_widget = None

    def ensure_iterations_tab(self):
        """Создаёт вкладку Iterations при первом обращении к ней."""
        if self.parent.iterations_widget is None:
            self.parent.iterations_widget = IterationResultsWidget(self.parent)
            # Вставляем вкладку Iterations в правильную позицию
            insert_pos = self._get_tab_insert_position("Iterations")
            self.parent.view_tabs.insertTab(
                insert_pos, self.parent.iterations_widget, "Iterations"
            )

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

    def ensure_convergence_tab(self):
        """Создаёт вкладку Convergence при первом обращении к ней."""
        if self.parent.convergence_widget is None:
            self.parent.convergence_widget = ConvergenceWidget(self.parent)
            # Вставляем вкладку Convergence в правильную позицию
            insert_pos = self._get_tab_insert_position("Convergence")
            self.parent.view_tabs.insertTab(
                insert_pos, self.parent.convergence_widget, "Convergence"
            )

            # Применяем текущую тему к новому виджету
            theme = "white" if not self.parent.theme_manager.is_dark_theme else "dark"
            self.parent.convergence_widget.apply_theme(theme)

    def remove_convergence_tab(self):
        """Удаляет вкладку Convergence."""
        if self.parent.convergence_widget is not None:
            idx = self.parent.view_tabs.indexOf(self.parent.convergence_widget)
            if idx != -1:
                self.parent.view_tabs.removeTab(idx)
            self.parent.convergence_widget = None

    def ensure_matrix_tab(self):
        """Создаёт вкладку Matrix при первом обращении к ней."""
        if self.parent.matrix_widget is None:
            self.parent.matrix_widget = MatrixWidget(self.parent)
            # Вставляем вкладку Matrix в правильную позицию
            insert_pos = self._get_tab_insert_position("Matrix")
            self.parent.view_tabs.insertTab(
                insert_pos, self.parent.matrix_widget, "Matrix"
            )

            # Применяем текущую тему к новому виджету
            theme = "white" if not self.parent.theme_manager.is_dark_theme else "dark"
            self.parent.matrix_widget.apply_theme(theme)

    def remove_matrix_tab(self):
        """Удаляет вкладку Matrix."""
        if self.parent.matrix_widget is not None:
            idx = self.parent.view_tabs.indexOf(self.parent.matrix_widget)
            if idx != -1:
                self.parent.view_tabs.removeTab(idx)
            self.parent.matrix_widget = None

    def ensure_info_tab(self):
        """Создаёт вкладку Info при первом обращении к ней."""
        if self.parent.info_widget is None:
            self.parent.info_widget = SequenceInfoWidget(self.parent)
            # Вставляем вкладку Info в правильную позицию
            insert_pos = self._get_tab_insert_position("Info")
            self.parent.view_tabs.insertTab(insert_pos, self.parent.info_widget, "Info")

            # Применяем текущую тему к новому виджету
            theme = "white" if not self.parent.theme_manager.is_dark_theme else "dark"
            self.parent.info_widget.apply_theme(theme)

    def remove_info_tab(self):
        """Удаляет вкладку Info."""
        if self.parent.info_widget is not None:
            idx = self.parent.view_tabs.indexOf(self.parent.info_widget)
            if idx != -1:
                self.parent.view_tabs.removeTab(idx)

            self.parent.info_widget = None


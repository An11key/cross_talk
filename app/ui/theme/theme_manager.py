"""
Менеджер тем и внешнего вида приложения.

Этот модуль управляет переключением между светлой и тёмной темами,
а также настройкой внешнего вида графиков и UI элементов.
"""

from PySide6.QtWidgets import QApplication


class ThemeManager:
    """Менеджер для управления темами приложения."""

    def __init__(self, parent_window):
        """
        Инициализация менеджера тем.

        Args:
            parent_window: Родительское окно (экземпляр MyMenu)
        """
        self.parent = parent_window
        self.is_dark_theme = True
        self.current_plot_theme = "dark"

    def apply_dark_theme(self):
        """Применяет тёмную тему при инициализации."""
        from app.ui.styles import DARK_THEME

        app = QApplication.instance()
        if app is None:
            return
        app.setStyleSheet(DARK_THEME)
        self.is_dark_theme = True
        self.current_plot_theme = "dark"

    def toggle_theme(self):
        """Переключает между светлой и тёмной темой."""
        from app.ui.styles import DARK_THEME, LIGHT_THEME

        app = QApplication.instance()
        if app is None:
            return

        if self.is_dark_theme:
            # Переключаем на светлую тему
            app.setStyleSheet(LIGHT_THEME)
            self.parent.theme_action.setText("Переключить на тёмную тему")
            self.is_dark_theme = False
            self.set_plot_background("white")
        else:
            # Переключаем на тёмную тему
            app.setStyleSheet(DARK_THEME)
            self.parent.theme_action.setText("Переключить на светлую тему")
            self.is_dark_theme = True
            self.set_plot_background("dark")

    def set_plot_background(self, theme):
        """
        Устанавливает фон для графиков в зависимости от темы.

        Args:
            theme (str): "white" или "dark"
        """
        if theme == "white":
            # Белый фон для светлой темы
            background_color = "white"
            foreground_color = "black"
        else:
            # Тёмный фон для тёмной темы (по умолчанию pyqtgraph)
            background_color = None
            foreground_color = "white"

        # Применяем к существующим виджетам графиков
        if self.parent.raw_plot_widget:
            if background_color:
                self.parent.raw_plot_widget.setBackground(background_color)
            else:
                self.parent.raw_plot_widget.setBackground("default")

        if self.parent.clean_plot_widget:
            if background_color:
                self.parent.clean_plot_widget.setBackground(background_color)
            else:
                self.parent.clean_plot_widget.setBackground("default")

        if self.parent.rwb_plot_widget:
            if background_color:
                self.parent.rwb_plot_widget.setBackground(background_color)
            else:
                self.parent.rwb_plot_widget.setBackground("default")

        if self.parent.iterations_widget:
            self.parent.iterations_widget.apply_theme(theme)

        if self.parent.convergence_widget:
            self.parent.convergence_widget.apply_theme(theme)

        if self.parent.matrix_widget:
            self.parent.matrix_widget.apply_theme(theme)

        if self.parent.info_widget:
            self.parent.info_widget.apply_theme(theme)

        # Сохраняем текущую тему для использования при отрисовке
        self.current_plot_theme = theme

        # Перерисовываем существующие графики с новыми цветами
        self.redraw_existing_plots()

    def redraw_existing_plots(self):
        """Перерисовывает все существующие графики с актуальными цветами."""
        # Получаем текущий выбранный файл
        current_item = self.parent.list_widget.currentItem()
        if current_item:
            # Симулируем клик по текущему элементу для перерисовки
            self.parent.plot_manager.file_list_click(current_item)

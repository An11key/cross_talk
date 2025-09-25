from __future__ import annotations

from typing import Optional, Tuple
from PySide6.QtWidgets import (
    QInputDialog,
    QWidget,
    QDialog,
    QVBoxLayout,
    QCheckBox,
    QPushButton,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QGroupBox,
    QFormLayout,
    QMessageBox,
)


def ask_test_data_params(parent: QWidget) -> Optional[Tuple[int, int, int, float]]:
    """Показывает последовательные диалоги и возвращает (n, peak_space, detail).

    Возвращает None, если пользователь отменил любой из шагов.
    """
    n, ok = QInputDialog.getInt(parent, "Длина последовательности", "N:", 1000, 1)
    if not ok:
        return None

    peak_space, ok = QInputDialog.getInt(
        parent, "Расстояние между пиками", "Peak space:", 10, 1
    )
    if not ok:
        return None

    detail, ok = QInputDialog.getInt(parent, "Точек на пик (detail)", "Detail:", 3, 1)
    if not ok:
        return None

    noise_level, ok = QInputDialog.getDouble(
        parent, "Уровень шума", "Noise level:", 0.05, 0.001, 1.0, 3
    )
    if not ok:
        return None
    return n, peak_space, detail, noise_level


class ProcessingOptionsDialog(QDialog):
    """Диалог для выбора опций обработки данных."""

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setWindowTitle("Параметры обработки")
        self.setModal(True)
        self.setFixedSize(400, 300)

        # Результат диалога
        self.smooth_data = True
        self.remove_baseline = True
        self.window_size = 21
        self.polyorder = 3

        self.setup_ui()

    def setup_ui(self):
        """Создает интерфейс диалога."""
        layout = QVBoxLayout()

        # Заголовок
        title_label = QLabel("Выберите параметры обработки:")
        layout.addWidget(title_label)

        # Чекбокс для удаления базовой линии
        self.baseline_checkbox = QCheckBox("Удаление базовой линии")
        self.baseline_checkbox.setChecked(True)  # Включено по умолчанию
        layout.addWidget(self.baseline_checkbox)

        # Группа для настроек сглаживания
        smooth_group = QGroupBox("Сглаживание данных")
        smooth_layout = QVBoxLayout()

        # Чекбокс для включения сглаживания
        self.smooth_checkbox = QCheckBox("Включить сглаживание")
        self.smooth_checkbox.setChecked(True)  # Включено по умолчанию
        smooth_layout.addWidget(self.smooth_checkbox)

        # Параметры сглаживания
        params_widget = QWidget()
        params_layout = QFormLayout()

        # Window size
        self.window_size_spinbox = QSpinBox()
        self.window_size_spinbox.setRange(3, 101)  # Минимум 3, максимум 101
        self.window_size_spinbox.setSingleStep(2)  # Шаг 2 для нечетных чисел
        self.window_size_spinbox.setValue(21)
        self.window_size_spinbox.setToolTip(
            "Размер окна для сглаживания Савицкого-Голея.\nДолжен быть нечетным числом (автокоррекция включена)."
        )
        # Обработчик для автокоррекции четных значений
        self.window_size_spinbox.valueChanged.connect(self._ensure_odd_window_size)
        params_layout.addRow("Window size:", self.window_size_spinbox)

        # Polyorder
        self.polyorder_spinbox = QSpinBox()
        self.polyorder_spinbox.setRange(1, 10)
        self.polyorder_spinbox.setValue(3)
        self.polyorder_spinbox.setToolTip(
            "Порядок полинома для сглаживания.\nДолжен быть меньше window size."
        )
        params_layout.addRow("Polyorder:", self.polyorder_spinbox)

        params_widget.setLayout(params_layout)
        smooth_layout.addWidget(params_widget)

        # Связываем включение сглаживания с доступностью параметров
        self.smooth_checkbox.toggled.connect(params_widget.setEnabled)

        smooth_group.setLayout(smooth_layout)
        layout.addWidget(smooth_group)

        # Кнопки
        button_layout = QHBoxLayout()

        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Отмена")

        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def accept(self):
        """Сохраняет выбранные параметры и закрывает диалог."""
        self.smooth_data = self.smooth_checkbox.isChecked()
        self.remove_baseline = self.baseline_checkbox.isChecked()

        if self.smooth_data:
            # Получаем значения параметров
            window_size = self.window_size_spinbox.value()
            polyorder = self.polyorder_spinbox.value()

            # Валидация: window_size должен быть нечетным
            if window_size % 2 == 0:
                QMessageBox.warning(
                    self,
                    "Некорректные параметры",
                    f"Window size должен быть нечетным числом.\nТекущее значение: {window_size}",
                )
                return

            # Валидация: polyorder должен быть меньше window_size
            if polyorder >= window_size:
                QMessageBox.warning(
                    self,
                    "Некорректные параметры",
                    f"Polyorder должен быть меньше window size.\n"
                    f"Текущие значения: polyorder={polyorder}, window_size={window_size}",
                )
                return

            # Сохраняем валидные параметры
            self.window_size = window_size
            self.polyorder = polyorder

        super().accept()

    def _ensure_odd_window_size(self, value):
        """Автоматически корректирует window_size до нечетного значения."""
        if value % 2 == 0:
            # Если четное, делаем нечетным (добавляем 1)
            self.window_size_spinbox.blockSignals(True)  # Избегаем рекурсии
            self.window_size_spinbox.setValue(value + 1)
            self.window_size_spinbox.blockSignals(False)


def ask_processing_options(parent: QWidget) -> Optional[Tuple[bool, bool, int, int]]:
    """Показывает диалог выбора опций обработки.

    Args:
        parent: Родительский виджет

    Returns:
        Tuple (smooth_data, remove_baseline, window_size, polyorder) или None если отменено
    """
    dialog = ProcessingOptionsDialog(parent)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return (
            dialog.smooth_data,
            dialog.remove_baseline,
            dialog.window_size,
            dialog.polyorder,
        )
    return None

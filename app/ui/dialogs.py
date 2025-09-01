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
        self.setFixedSize(300, 150)

        # Результат диалога
        self.smooth_data = True
        self.remove_baseline = True

        self.setup_ui()

    def setup_ui(self):
        """Создает интерфейс диалога."""
        layout = QVBoxLayout()

        # Заголовок
        title_label = QLabel("Выберите параметры обработки:")
        layout.addWidget(title_label)

        # Чекбокс для сглаживания
        self.smooth_checkbox = QCheckBox("Сглаживание данных")
        self.smooth_checkbox.setChecked(True)  # Включено по умолчанию
        layout.addWidget(self.smooth_checkbox)

        # Чекбокс для удаления базовой линии
        self.baseline_checkbox = QCheckBox("Удаление базовой линии")
        self.baseline_checkbox.setChecked(True)  # Включено по умолчанию
        layout.addWidget(self.baseline_checkbox)

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
        super().accept()


def ask_processing_options(parent: QWidget) -> Optional[Tuple[bool, bool]]:
    """Показывает диалог выбора опций обработки.

    Args:
        parent: Родительский виджет

    Returns:
        Tuple (smooth_data, remove_baseline) или None если отменено
    """
    dialog = ProcessingOptionsDialog(parent)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.smooth_data, dialog.remove_baseline
    return None

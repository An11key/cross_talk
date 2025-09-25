"""
Управление обработкой данных и потоками.

Этот модуль содержит логику запуска и управления потоками
обработки данных, а также обработку результатов.
"""

import os
import pandas as pd
from app.ui.processing_thread import DataProcessingThread
from app.core.processing import process_and_save, is_file_already_processed
from app.ui.dialogs import ask_processing_options


class DataProcessingManager:
    """Менеджер для обработки данных."""

    def __init__(self, parent_window):
        """
        Инициализация менеджера обработки данных.

        Args:
            parent_window: Родительское окно (экземпляр MyMenu)
        """
        self.parent = parent_window
        self.processing_thread = None
        self.current_processing_file = None

    def start_processing(
        self,
        file_name,
        data,
        smooth_data=True,
        remove_baseline=True,
        window_size=21,
        polyorder=3,
    ):
        """Запускает обработку файла в отдельном потоке."""
        if self.processing_thread and self.processing_thread.isRunning():
            return  # Уже идет обработка

        path = self.parent.registry.get_path(file_name)

        # Создаем и настраиваем поток
        self.processing_thread = DataProcessingThread(
            path, data, smooth_data, remove_baseline, window_size, polyorder
        )
        self.current_processing_file = file_name

        # Подключаем сигналы
        self.processing_thread.progress_updated.connect(self.parent.on_progress_updated)
        self.processing_thread.processing_finished.connect(
            self.parent.on_processing_finished
        )
        self.processing_thread.processing_error.connect(self.parent.on_processing_error)

        # Показываем прогресс-бар
        self.parent.progress_bar.setVisible(True)
        self.parent.cancel_button.setVisible(True)
        self.parent.status_label.setText(f"Обработка файла: {file_name}")

        # Запускаем поток
        self.processing_thread.start()

    def cancel_processing(self):
        """Отменяет текущую обработку."""
        if self.processing_thread and self.processing_thread.isRunning():
            self.processing_thread.cancel()
            self.parent.status_label.setText("Отмена обработки...")

    def on_progress_updated(self, progress, message):
        """Обработчик обновления прогресса."""
        # Проверяем, не является ли это сигналом данных итерации
        if progress == -1 and isinstance(message, str):
            try:
                import json

                data = json.loads(message)
                if data.get("type") == "iteration_data":
                    # Обрабатываем данные итерации
                    iteration_num = data["iteration"]
                    iteration_data = {}

                    # Восстанавливаем данные из JSON
                    for key, data_dict in data["data"].items():
                        i, j = map(int, key.split(","))
                        import numpy as np

                        iteration_data[(i, j)] = {
                            "x_data": np.array(data_dict["x_data"]),
                            "y_data": np.array(data_dict["y_data"]),
                            "slope": data_dict["slope"],
                            "intercept": data_dict["intercept"],
                        }

                    # Сохраняем данные итерации для текущего файла
                    current_file = self.current_processing_file
                    if current_file:
                        self.parent.plot_manager.store_iteration_data(
                            current_file, iteration_num, iteration_data
                        )
                    return
            except (json.JSONDecodeError, KeyError, ValueError):
                # Если не удалось декодировать, обрабатываем как обычное сообщение
                pass

        # Обычное обновление прогресса
        self.parent.progress_bar.setValue(int(progress))
        self.parent.status_label.setText(message)

    def on_processing_finished(self, clean_data, clean_path):
        """Обработчик завершения обработки."""
        # Скрываем прогресс-бар
        self.parent.progress_bar.setVisible(False)
        self.parent.cancel_button.setVisible(False)
        self.parent.status_label.setText("Обработка завершена")

        # Обрабатываем результат
        if self.current_processing_file:
            # Кешируем очищенный файл
            clean_name = os.path.basename(clean_path)
            self.parent.registry.set_file(clean_name, clean_path)
            self.parent.registry.set_df(clean_name, clean_data)

            # Обеспечиваем вкладку Clean и рисуем данные
            self.parent.ensure_clean_tab()
            self.parent.plot_data(self.parent.clean_plot_widget, clean_data)

            # Финализируем результаты итераций и создаем вкладку для этого файла
            if self.current_processing_file:
                self.parent.plot_manager.finalize_iteration_results(
                    self.current_processing_file
                )

            # Переключаемся на вкладку Iterations если есть данные для этого файла
            current_file_has_iterations = (
                self.current_processing_file
                and self.current_processing_file
                in self.parent.plot_manager.iteration_results_data
                and self.parent.plot_manager.iteration_results_data[
                    self.current_processing_file
                ]
            )

            if current_file_has_iterations:
                self.parent.view_tabs.setCurrentWidget(self.parent.iterations_widget)
            else:
                self.parent.view_tabs.setCurrentWidget(self.parent.clean_plot_widget)

            # Устанавливаем базовое имя файла для clean вкладки
            file_name = self.current_processing_file
            if "_clean" in file_name:
                base_name = file_name.split("_clean")[0]
            else:
                parts = file_name.split(".")
                base_name = parts[0]
            self.parent.plot_manager.current_clean_file_base = base_name

        # Очищаем ссылки
        self.processing_thread = None
        self.current_processing_file = None

    def on_processing_error(self, error_message):
        """Обработчик ошибки обработки."""
        # Скрываем прогресс-бар
        self.parent.progress_bar.setVisible(False)
        self.parent.cancel_button.setVisible(False)
        self.parent.status_label.setText(f"Ошибка: {error_message}")

        # Очищаем ссылки
        self.processing_thread = None
        self.current_processing_file = None

    def process_file(self, name):
        """Обрабатывает файл: baseline → оценка W → очистка → сохранение и показ.

        Также печатает оценённую матрицу кросс-помех в терминал.
        """
        path = self.parent.registry.get_path(name)

        # Проверяем, не обрабатывался ли файл ранее
        already_processed, existing_clean_path = is_file_already_processed(path)

        if already_processed:
            print(
                f"Файл уже обработан. Используем существующий результат: {existing_clean_path}"
            )
            # Загружаем существующий очищенный файл
            clean_data = self.parent._load_data_by_path(existing_clean_path)
            clean_path = existing_clean_path

            # Кешируем очищенный файл
            clean_name = os.path.basename(clean_path)
            self.parent.registry.set_file(clean_name, clean_path)
            self.parent.registry.set_df(clean_name, clean_data)

            # Обеспечиваем вкладку Clean и рисуем данные
            self.parent.ensure_clean_tab()
            self.parent.plot_data(self.parent.clean_plot_widget, clean_data)
            self.parent.view_tabs.setCurrentWidget(self.parent.clean_plot_widget)

            # Устанавливаем базовое имя файла для clean вкладки
            if "_clean" in name:
                base_name = name.split("_clean")[0]
            else:
                parts = name.split(".")
                base_name = parts[0]
            self.parent.plot_manager.current_clean_file_base = base_name

            # Пытаемся загрузить сохраненные данные итераций для этого файла
            self.parent.plot_manager.show_iterations_for_file(name)
        else:
            # Проверяем, не идет ли уже обработка
            if self.processing_thread and self.processing_thread.isRunning():
                self.parent.status_label.setText(
                    "Дождитесь завершения текущей обработки"
                )
                return

            # Показываем диалог выбора параметров обработки
            processing_options = ask_processing_options(self.parent)
            if processing_options is None:
                # Пользователь отменил обработку
                return

            smooth_data, remove_baseline, window_size, polyorder = processing_options

            # Загружаем данные если нужно
            if not self.parent.registry.has_df(name):
                self.parent.registry.set_df(name, self.parent._load_data_by_path(path))

            data = self.parent.registry.get_df(name)

            # Запускаем обработку в отдельном потоке
            self.start_processing(
                name, data, smooth_data, remove_baseline, window_size, polyorder
            )

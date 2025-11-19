"""
Управление обработкой данных и потоками.

Этот модуль содержит логику запуска и управления потоками
обработки данных, а также обработку результатов.
"""

import os
import pandas as pd
from app.ui.processing.processing_thread import DataProcessingThread
from app.core.processing import process_and_save, is_file_already_processed
from app.ui.dialogs.dialogs import ask_processing_options, ask_batch_processing_options


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

        # Параметры очереди обработки
        self.processing_queue = []
        self.current_queue_index = 0
        self.queue_processing_options = None

        # Опции пакетной обработки
        self.batch_save_data = True
        self.batch_save_statistics = False

        # Параметры множественной обработки (для двух алгоритмов)
        self.current_algorithms = []  # Список алгоритмов для текущей обработки
        self.current_algorithm_index = 0  # Индекс текущего алгоритма
        self.dual_processing_results = (
            {}
        )  # Результаты для обоих алгоритмов {algorithm: (data, path, matrix)}

    def start_processing(
        self,
        file_name,
        data,
        smooth_data=True,
        remove_baseline=True,
        window_size=21,
        polyorder=3,
        algorithm="estimate_crosstalk_2",
        save_data=True,
    ):
        """Запускает обработку файла в отдельном потоке."""
        if self.processing_thread and self.processing_thread.isRunning():
            return  # Уже идет обработка

        path = self.parent.registry.get_path(file_name)

        # Создаем и настраиваем поток
        self.processing_thread = DataProcessingThread(
            path,
            data,
            smooth_data,
            remove_baseline,
            window_size,
            polyorder,
            algorithm,
            save_data,
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

            # Если обрабатывается очередь, отменяем всю очередь
            if self.processing_queue:
                self.parent.status_label.setText("Отмена пакетной обработки...")
                # Очищаем очередь и опции
                self.processing_queue = []
                self.current_queue_index = 0
                self.queue_processing_options = None
                self.batch_save_data = True
                self.batch_save_statistics = False
            else:
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
                            "x_regression_points": np.array(
                                data_dict.get("x_regression_points", [])
                            ),
                            "y_regression_points": np.array(
                                data_dict.get("y_regression_points", [])
                            ),
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

        # Если обрабатывается очередь, добавляем информацию о прогрессе очереди
        if self.processing_queue:
            queue_info = f"[{self.current_queue_index}/{len(self.processing_queue)}] "
            self.parent.status_label.setText(queue_info + message)
        else:
            self.parent.status_label.setText(message)

    def on_processing_finished(self, clean_data, clean_path, crosstalk_matrix=None):
        """Обработчик завершения обработки."""
        # Сохраняем параметры обработки для текущего файла
        processing_params = None
        current_algorithm = None
        if self.processing_thread:
            processing_params = {
                "smooth_data": self.processing_thread.smooth_data,
                "remove_baseline": self.processing_thread.remove_baseline,
                "algorithm": self.processing_thread.algorithm,
            }
            current_algorithm = self.processing_thread.algorithm

        # Проверяем, нужно ли только собирать статистику (без сохранения файлов)
        is_statistics_only_mode = (
            self.processing_queue  # Это пакетная обработка
            and not self.batch_save_data  # Не сохраняем данные
            and self.batch_save_statistics  # Но собираем статистику
        )

        # Если мы обрабатываем несколько алгоритмов
        if self.current_algorithms and len(self.current_algorithms) > 1:
            # Сохраняем результат текущего алгоритма
            if current_algorithm:
                self.dual_processing_results[current_algorithm] = (
                    clean_data,
                    clean_path,
                    crosstalk_matrix,
                )
                print(f"[DEBUG] Сохранен результат для алгоритма {current_algorithm}")

            # Проверяем, есть ли еще алгоритмы для обработки
            self.current_algorithm_index += 1
            if self.current_algorithm_index < len(self.current_algorithms):
                # Запускаем обработку следующего алгоритма
                self._process_next_algorithm()
                return
            else:
                # Все алгоритмы обработаны - финализируем результаты
                print(
                    f"[DEBUG] Все алгоритмы обработаны. Результатов: {len(self.dual_processing_results)}"
                )
                self._finalize_dual_processing()
                return

        # Обрабатываем результат
        if self.current_processing_file:
            file_name = self.current_processing_file

            # Определяем базовое имя файла
            if "_clean" in file_name:
                base_name = file_name.split("_clean")[0]
            else:
                parts = file_name.split(".")
                base_name = parts[0]

            # Режим "только статистика" - сохраняем только необходимую информацию
            if is_statistics_only_mode:
                print(f"[DEBUG] Режим 'только статистика' для {file_name}")

                # Сохраняем параметры обработки и данные для статистики
                if self.parent.registry.has_df(file_name):
                    raw_data = self.parent.registry.get_df(file_name)
                    data_points = len(raw_data)
                    dye_names = list(raw_data.columns)

                    # Если это .srd файл, загружаем правильные названия
                    if file_name.endswith(".srd"):
                        try:
                            from app.utils.load_utils import load_dye_names_from_srd

                            file_path = self.parent.registry.get_path(file_name)
                            dye_names = load_dye_names_from_srd(file_path)
                        except Exception as e:
                            print(f"Не удалось загрузить названия красителей: {e}")

                    # Сохраняем информацию с параметрами обработки
                    if processing_params:
                        self.parent.plot_manager.store_sequence_info(
                            file_name,
                            data_points,
                            dye_names,
                            smooth_data=processing_params["smooth_data"],
                            remove_baseline=processing_params["remove_baseline"],
                            algorithm=processing_params["algorithm"],
                        )

                    # Если есть матрица, вычисляем разницу с оригинальной
                    if crosstalk_matrix is not None:
                        original_matrix = (
                            self.parent.plot_manager.original_matrices.get(
                                base_name, None
                            )
                        )
                        if original_matrix is not None:
                            self.parent.plot_manager.store_matrix_difference(
                                file_name, crosstalk_matrix, original_matrix
                            )
                            print(
                                f"[DEBUG] Разница матриц вычислена и сохранена для {file_name} (режим: только статистика)"
                            )
                        else:
                            print(
                                f"[DEBUG] Оригинальная матрица не найдена для {base_name} (режим: только статистика)"
                            )

                print(f"[DEBUG] Данные для статистики сохранены для {file_name}")

            else:
                # Обычный режим - сохраняем файлы и показываем в интерфейсе
                # Кешируем очищенный файл (только если он был сохранен на диск)
                file_was_saved = (
                    self.processing_thread
                    and self.processing_thread.save_data
                    and os.path.exists(clean_path)
                    and "_clean" in os.path.basename(clean_path)
                )

                if file_was_saved:
                    clean_name = os.path.basename(clean_path)
                    self.parent.registry.set_file(clean_name, clean_path)
                    self.parent.registry.set_df(clean_name, clean_data)

                # Обеспечиваем вкладку Clean и рисуем данные
                self.parent.ensure_clean_tab()
                self.parent.plot_data(self.parent.clean_plot_widget, clean_data)

                # Создаем вкладку Rwb для исходного файла (если это не clean файл)
                if "_clean" not in self.current_processing_file:
                    # Загружаем исходные данные для показа Raw и Rwb
                    if self.parent.registry.has_df(self.current_processing_file):
                        from app.utils.seq_utils import baseline_cor

                        raw_data = self.parent.registry.get_df(
                            self.current_processing_file
                        )
                        # Обновляем Raw вкладку с исходными данными
                        self.parent.plot_data(self.parent.raw_plot_widget, raw_data)
                        # Создаем и обновляем Rwb вкладку
                        self.parent.plot_manager.ensure_rwb_tab()
                        rwb_data = baseline_cor(raw_data)
                        self.parent.plot_data(self.parent.rwb_plot_widget, rwb_data)

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
                    self.parent.view_tabs.setCurrentWidget(
                        self.parent.iterations_widget
                    )
                else:
                    self.parent.view_tabs.setCurrentWidget(
                        self.parent.clean_plot_widget
                    )

                # Устанавливаем базовое имя файла для clean вкладки
                self.parent.plot_manager.current_clean_file_base = base_name

                # Сохраняем базовую информацию о последовательности (только в обычном режиме)
                print(f"[DEBUG] Сохранение информации о файле: {file_name}")
                print(
                    f"[DEBUG] Файл в реестре: {self.parent.registry.has_df(file_name)}"
                )
                print(f"[DEBUG] Параметры обработки: {processing_params}")

                if self.parent.registry.has_df(file_name):
                    raw_data = self.parent.registry.get_df(file_name)
                    data_points = len(raw_data)

                    # Получаем названия каналов (красителей)
                    dye_names = list(raw_data.columns)

                    # Если это .srd файл, пытаемся загрузить правильные названия из файла
                    if file_name.endswith(".srd"):
                        try:
                            from app.utils.load_utils import load_dye_names_from_srd

                            file_path = self.parent.registry.get_path(file_name)
                            dye_names = load_dye_names_from_srd(file_path)
                        except Exception as e:
                            print(
                                f"Не удалось загрузить названия красителей из .srd: {e}"
                            )

                    # Сохраняем информацию с параметрами обработки
                    if processing_params:
                        print(f"[DEBUG] Сохранение с параметрами для {file_name}")
                        self.parent.plot_manager.store_sequence_info(
                            file_name,
                            data_points,
                            dye_names,
                            smooth_data=processing_params["smooth_data"],
                            remove_baseline=processing_params["remove_baseline"],
                            algorithm=processing_params["algorithm"],
                        )
                    else:
                        print(f"[DEBUG] Сохранение без параметров для {file_name}")
                        self.parent.plot_manager.store_sequence_info(
                            file_name, data_points, dye_names
                        )
                else:
                    print(
                        f"[WARNING] Файл {file_name} не найден в реестре, не могу сохранить информацию"
                    )

            # Сохраняем и показываем матрицу кросс-помех (только в обычном режиме)
            if not is_statistics_only_mode and crosstalk_matrix is not None:
                print(f"Получена матрица кросс-помех для {file_name}")
                print(f"Форма матрицы: {crosstalk_matrix.shape}")

                # Находим оригинальный файл с расширением .srd в реестре
                original_file_name = None
                for registered_file in self.parent.registry._name_to_path.keys():
                    if registered_file.startswith(
                        base_name
                    ) and registered_file.endswith(".srd"):
                        original_file_name = registered_file
                        break

                # Если не нашли .srd, используем текущее имя файла
                if original_file_name is None:
                    original_file_name = file_name

                print(f"[DEBUG] Используем имя файла для матрицы: {original_file_name}")
                self.parent.plot_manager.store_crosstalk_matrix(
                    original_file_name, crosstalk_matrix
                )

                # Сохраняем матрицу в файл .matrix
                try:
                    from app.utils.load_utils import save_matrix_to_file

                    # Получаем путь к оригинальному файлу
                    original_path = self.parent.registry.get_path(original_file_name)
                    # Создаем путь для файла матрицы (заменяем расширение на .matrix)
                    matrix_file_path = os.path.splitext(original_path)[0] + ".matrix"
                    save_matrix_to_file(crosstalk_matrix, matrix_file_path)
                except Exception as e:
                    print(f"Ошибка при сохранении матрицы в файл: {e}")

                matrix_shown = self.parent.plot_manager.show_matrix_for_file(
                    original_file_name
                )
                print(f"Вкладка Matrix {'показана' if matrix_shown else 'не показана'}")

                # Если есть оригинальная матрица из .srd, вычисляем разницу
                original_matrix = self.parent.plot_manager.original_matrices.get(
                    base_name, None
                )
                if original_matrix is not None:
                    print(f"Вычисляем разницу между матрицами для {original_file_name}")
                    self.parent.plot_manager.store_matrix_difference(
                        original_file_name, crosstalk_matrix, original_matrix
                    )
                    # Обновляем вкладку Info с новой информацией
                    self.parent.plot_manager.show_info_for_file(original_file_name)
            else:
                print(f"Матрица кросс-помех не получена для {file_name}")

            # Показываем вкладку Info (только в обычном режиме)
            if not is_statistics_only_mode:
                # Используем исходное имя файла для отображения
                display_file_name = file_name
                if "_clean" not in file_name:
                    # Для исходных файлов ищем .srd версию, если есть
                    for registered_file in self.parent.registry._name_to_path.keys():
                        if registered_file.startswith(
                            base_name
                        ) and registered_file.endswith(".srd"):
                            display_file_name = registered_file
                            break
                self.parent.plot_manager.show_info_for_file(display_file_name)

        # Очищаем ссылки
        self.processing_thread = None
        self.current_processing_file = None

        # Проверяем, есть ли еще файлы в очереди
        if self.processing_queue and self.current_queue_index < len(
            self.processing_queue
        ):
            # Обрабатываем следующий файл из очереди
            self._process_next_in_queue()
        else:
            # Очередь пуста - завершаем пакетную обработку
            self._finish_queue_processing()

    def on_processing_error(self, error_message):
        """Обработчик ошибки обработки."""
        # Выводим информацию об ошибке
        if self.current_processing_file:
            error_text = (
                f"Ошибка при обработке {self.current_processing_file}: {error_message}"
            )
            print(error_text)
        else:
            error_text = f"Ошибка: {error_message}"

        self.parent.status_label.setText(error_text)

        # Очищаем ссылки
        self.processing_thread = None
        current_file = self.current_processing_file
        self.current_processing_file = None

        # Проверяем, есть ли еще файлы в очереди
        if self.processing_queue and self.current_queue_index < len(
            self.processing_queue
        ):
            # Продолжаем обработку следующего файла, несмотря на ошибку
            print(
                f"Продолжаем обработку очереди, пропускаем файл с ошибкой: {current_file}"
            )
            self._process_next_in_queue()
        else:
            # Очередь пуста - завершаем пакетную обработку
            if self.processing_queue:
                self._finish_queue_processing()
            else:
                # Одиночная обработка - просто скрываем прогресс-бар
                self.parent.progress_bar.setVisible(False)
                self.parent.cancel_button.setVisible(False)
                # Сбрасываем флаги пакетной обработки
                self.batch_save_data = True
                self.batch_save_statistics = False

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

            # Устанавливаем базовое имя файла для clean вкладки
            if "_clean" in name:
                base_name = name.split("_clean")[0]
            else:
                parts = name.split(".")
                base_name = parts[0]
            self.parent.plot_manager.current_clean_file_base = base_name

            # Создаем вкладку Rwb для исходного файла
            if "_clean" not in name and self.parent.registry.has_df(name):
                from app.utils.seq_utils import baseline_cor

                raw_data = self.parent.registry.get_df(name)
                # Обновляем Raw вкладку с исходными данными
                self.parent.plot_data(self.parent.raw_plot_widget, raw_data)
                # Создаем и обновляем Rwb вкладку
                self.parent.plot_manager.ensure_rwb_tab()
                rwb_data = baseline_cor(raw_data)
                self.parent.plot_data(self.parent.rwb_plot_widget, rwb_data)

            # Сохраняем базовую информацию о последовательности, если её ещё нет
            if base_name not in self.parent.plot_manager.sequence_info:
                if self.parent.registry.has_df(name):
                    raw_data = self.parent.registry.get_df(name)
                    data_points = len(raw_data)
                    dye_names = list(raw_data.columns)

                    # Если это .srd файл, пытаемся загрузить правильные названия из файла
                    if name.endswith(".srd"):
                        try:
                            from app.utils.load_utils import load_dye_names_from_srd

                            file_path = self.parent.registry.get_path(name)
                            dye_names = load_dye_names_from_srd(file_path)
                        except Exception as e:
                            print(
                                f"Не удалось загрузить названия красителей из .srd: {e}"
                            )

                    self.parent.plot_manager.store_sequence_info(
                        name, data_points, dye_names
                    )

            self.parent.view_tabs.setCurrentWidget(self.parent.clean_plot_widget)

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

            smooth_data, remove_baseline, window_size, polyorder, algorithms = (
                processing_options
            )

            # Загружаем данные если нужно
            if not self.parent.registry.has_df(name):
                self.parent.registry.set_df(name, self.parent._load_data_by_path(path))

            data = self.parent.registry.get_df(name)

            # Загружаем оригинальную матрицу из .srd файла для вычисления разницы
            if name.endswith(".srd"):
                self.parent.plot_manager.data_manager._load_original_matrix_from_srd(
                    name
                )
                print(f"[DEBUG] Загружена оригинальная матрица для {name}")

            # Инициализируем множественную обработку
            self.current_algorithms = algorithms
            self.current_algorithm_index = 0
            self.dual_processing_results = {}

            print(f"[DEBUG] Начинаем обработку {len(algorithms)} алгоритмом(ами)")

            # Запускаем обработку первым алгоритмом в отдельном потоке
            self.start_processing(
                name,
                data.copy(),
                smooth_data,
                remove_baseline,
                window_size,
                polyorder,
                algorithms[0],  # Первый алгоритм
            )

    def process_selected_files(self):
        """Запускает обработку всех выбранных файлов в очереди."""
        selected_items = self.parent.list_widget.selectedItems()

        if not selected_items:
            self.parent.status_label.setText("Нет выбранных файлов для обработки")
            return

        # Проверяем, не идет ли уже обработка
        if self.processing_thread and self.processing_thread.isRunning():
            self.parent.status_label.setText("Дождитесь завершения текущей обработки")
            return

        # Создаем очередь из выбранных файлов
        self.processing_queue = []
        for item in selected_items:
            name = item.text()
            path = self.parent.registry.get_path(name)

            # Проверяем, не обрабатывался ли файл ранее
            already_processed, _ = is_file_already_processed(path)

            # Добавляем в очередь только необработанные файлы
            if not already_processed:
                self.processing_queue.append(name)
            else:
                print(f"Файл {name} уже обработан, пропускаем")

        if not self.processing_queue:
            self.parent.status_label.setText("Все выбранные файлы уже обработаны")
            return

        # Показываем диалог опций пакетной обработки
        batch_options = ask_batch_processing_options(
            self.parent, len(self.processing_queue)
        )
        if batch_options is None:
            # Пользователь отменил или не выбрал ни одной опции
            self.processing_queue = []
            return

        # Сохраняем опции пакетной обработки
        self.batch_save_data, self.batch_save_statistics = batch_options

        # Показываем диалог выбора параметров обработки (один раз для всех файлов)
        processing_options = ask_processing_options(self.parent)
        if processing_options is None:
            # Пользователь отменил обработку
            self.processing_queue = []
            return

        # Сохраняем параметры для всей очереди
        self.queue_processing_options = processing_options

        # Начинаем обработку первого файла
        self.current_queue_index = 0
        self._process_next_in_queue()

    def _process_next_in_queue(self):
        """Обрабатывает следующий файл из очереди."""
        if self.current_queue_index >= len(self.processing_queue):
            self._finish_queue_processing()
            return

        name = self.processing_queue[self.current_queue_index]
        path = self.parent.registry.get_path(name)

        # Обновляем статус с информацией о прогрессе очереди
        queue_progress_text = f"Обработка файла {self.current_queue_index + 1} из {len(self.processing_queue)}: {name}"
        self.parent.status_label.setText(queue_progress_text)

        # Загружаем данные если нужно
        if not self.parent.registry.has_df(name):
            self.parent.registry.set_df(name, self.parent._load_data_by_path(path))

        data = self.parent.registry.get_df(name)

        # Загружаем оригинальную матрицу из .srd файла для вычисления разницы
        if name.endswith(".srd"):
            self.parent.plot_manager.data_manager._load_original_matrix_from_srd(name)
            print(f"[DEBUG] Загружена оригинальная матрица для {name}")

        # Используем сохраненные параметры обработки
        smooth_data, remove_baseline, window_size, polyorder, algorithms = (
            self.queue_processing_options
        )

        # Инициализируем множественную обработку
        self.current_algorithms = algorithms
        self.current_algorithm_index = 0
        self.dual_processing_results = {}

        # Запускаем обработку первым алгоритмом (создаем копию данных, чтобы не модифицировать данные в реестре)
        self.start_processing(
            name,
            data.copy(),
            smooth_data,
            remove_baseline,
            window_size,
            polyorder,
            algorithms[0],  # Первый алгоритм
            save_data=self.batch_save_data,
        )

        # Увеличиваем счетчик
        self.current_queue_index += 1

    def _finish_queue_processing(self):
        """Завершает пакетную обработку файлов."""
        # Сохраняем количество обработанных файлов
        total_processed = len(self.processing_queue)

        # Автоматически сохраняем статистику, если опция включена
        if self.batch_save_statistics:
            self._save_batch_statistics(total_processed)

        # Скрываем прогресс-бар
        self.parent.progress_bar.setVisible(False)
        self.parent.cancel_button.setVisible(False)

        # Обновляем статус
        status_message = (
            f"Пакетная обработка завершена. Обработано файлов: {total_processed}"
        )
        if self.batch_save_statistics:
            status_message += " (статистика сохранена)"
        self.parent.status_label.setText(status_message)

        # Очищаем очередь и опции
        self.processing_queue = []
        self.current_queue_index = 0
        self.queue_processing_options = None
        self.batch_save_data = True
        self.batch_save_statistics = False

    def _process_next_algorithm(self):
        """Запускает обработку следующего алгоритма в списке."""
        if not self.current_processing_file:
            return

        name = self.current_processing_file
        path = self.parent.registry.get_path(name)

        # Получаем параметры из последнего потока
        smooth_data = self.processing_thread.smooth_data
        remove_baseline = self.processing_thread.remove_baseline
        window_size = self.processing_thread.window_size
        polyorder = self.processing_thread.polyorder
        save_data = self.processing_thread.save_data

        # Получаем следующий алгоритм
        next_algorithm = self.current_algorithms[self.current_algorithm_index]

        # Загружаем данные
        if not self.parent.registry.has_df(name):
            self.parent.registry.set_df(name, self.parent._load_data_by_path(path))
        data = self.parent.registry.get_df(name)

        print(
            f"[DEBUG] Запуск обработки алгоритмом {next_algorithm} ({self.current_algorithm_index + 1}/{len(self.current_algorithms)})"
        )

        # Запускаем обработку следующего алгоритма
        self.processing_thread = None  # Очищаем старый поток
        self.start_processing(
            name,
            data.copy(),
            smooth_data,
            remove_baseline,
            window_size,
            polyorder,
            next_algorithm,
            save_data,
        )

    def _finalize_dual_processing(self):
        """Финализирует обработку двумя алгоритмами и создает вкладки."""
        if not self.current_processing_file:
            return

        file_name = self.current_processing_file

        # Проверяем, нужно ли только собирать статистику (без сохранения файлов)
        is_statistics_only_mode = (
            self.processing_queue  # Это пакетная обработка
            and not self.batch_save_data  # Не сохраняем данные
            and self.batch_save_statistics  # Но собираем статистику
        )

        # Получаем базовое имя файла
        if "_clean" in file_name:
            base_name = file_name.split("_clean")[0]
        else:
            parts = file_name.split(".")
            base_name = parts[0]

        # Находим оригинальный файл с расширением .srd в реестре
        original_file_name = None
        for registered_file in self.parent.registry._name_to_path.keys():
            if registered_file.startswith(base_name) and registered_file.endswith(
                ".srd"
            ):
                original_file_name = registered_file
                break
        if original_file_name is None:
            original_file_name = file_name

        mode_text = "только статистика" if is_statistics_only_mode else "обычный"
        print(
            f"[DEBUG] Финализация двойной обработки для {file_name} (режим: {mode_text})"
        )

        # Получаем параметры обработки и информацию о реагентах
        smooth_data = (
            self.processing_thread.smooth_data if self.processing_thread else None
        )
        remove_baseline = (
            self.processing_thread.remove_baseline if self.processing_thread else None
        )

        raw_data = None
        data_points = 0
        dye_names = []
        original_ext = ".csv"

        if self.parent.registry.has_df(file_name):
            raw_data = self.parent.registry.get_df(file_name)
            data_points = len(raw_data)
            dye_names = list(raw_data.columns)

            if file_name.endswith(".srd"):
                original_ext = ".srd"
                try:
                    from app.utils.load_utils import load_dye_names_from_srd

                    file_path = self.parent.registry.get_path(file_name)
                    dye_names = load_dye_names_from_srd(file_path)
                except Exception as e:
                    print(f"Не удалось загрузить названия красителей из .srd: {e}")

        # В режиме "только статистика" не создаем вкладки и не показываем в интерфейсе
        if not is_statistics_only_mode:
            # Создаем вкладки Raw и Rwb для исходного файла (если это не clean файл)
            if "_clean" not in file_name and raw_data is not None:
                from app.utils.seq_utils import baseline_cor

                # Обновляем Raw вкладку с исходными данными
                self.parent.plot_data(self.parent.raw_plot_widget, raw_data)
                # Создаем и обновляем Rwb вкладку
                self.parent.plot_manager.ensure_rwb_tab()
                rwb_data = baseline_cor(raw_data)
                self.parent.plot_data(self.parent.rwb_plot_widget, rwb_data)
                print(f"[DEBUG] Созданы вкладки Raw и Rwb для {file_name}")

        # Создаем отдельные файлы для каждого алгоритма
        algorithm_index = 1
        created_files = []

        for algorithm, (
            clean_data,
            clean_path,
            crosstalk_matrix,
        ) in self.dual_processing_results.items():
            algorithm_suffix = f"_{algorithm_index}"
            algorithm_name = (
                "Метод 1" if algorithm == "estimate_crosstalk" else "Метод 2"
            )
            print(
                f"[DEBUG] Создание данных для {algorithm_name} с суффиксом {algorithm_suffix}"
            )

            # Создаем имя файла с суффиксом
            save_ext = ".csv" if original_ext == ".srd" else original_ext
            clean_file_name = f"{base_name}_clean{algorithm_suffix}{save_ext}"

            # В режиме "только статистика" не сохраняем файлы на диск
            file_path = None
            if (
                not is_statistics_only_mode
                and self.processing_thread
                and self.processing_thread.save_data
            ):
                import os

                processed_dir = "processed_sequences"
                sequence_folder = os.path.join(processed_dir, f"{base_name}_seq")

                if not os.path.exists(sequence_folder):
                    os.makedirs(sequence_folder, exist_ok=True)

                file_path = os.path.join(sequence_folder, clean_file_name)
                clean_data.to_csv(file_path, sep=";", index=False, header=False)
                print(f"[DEBUG] Сохранен файл: {file_path}")

            # В обычном режиме регистрируем файл и добавляем в список
            if not is_statistics_only_mode:
                # Регистрируем файл и кешируем данные
                if file_path:
                    self.parent.registry.set_file(clean_file_name, file_path)
                self.parent.registry.set_df(clean_file_name, clean_data)

                # Добавляем файл в список
                existing_items = [
                    self.parent.list_widget.item(i).text()
                    for i in range(self.parent.list_widget.count())
                ]
                if clean_file_name not in existing_items:
                    self.parent.list_widget.addItem(clean_file_name)
                    print(f"[DEBUG] Добавлен в список: {clean_file_name}")
                    created_files.append(clean_file_name)

            # Сохраняем информацию о последовательности для этого файла
            self.parent.plot_manager.store_sequence_info(
                clean_file_name,
                data_points,
                dye_names,
                smooth_data=smooth_data,
                remove_baseline=remove_baseline,
                algorithm=algorithm,
            )

            # Сохраняем матрицу кросс-помех
            if crosstalk_matrix is not None:
                print(f"[DEBUG] Сохранение матрицы для {clean_file_name}")
                self.parent.plot_manager.store_crosstalk_matrix(
                    clean_file_name, crosstalk_matrix
                )

                # Вычисляем разницу матриц
                original_matrix = self.parent.plot_manager.original_matrices.get(
                    base_name, None
                )
                if original_matrix is not None:
                    self.parent.plot_manager.store_matrix_difference(
                        clean_file_name, crosstalk_matrix, original_matrix
                    )
                    print(
                        f"[DEBUG] Разница матриц вычислена и сохранена для {clean_file_name}"
                    )
                else:
                    print(f"[DEBUG] Оригинальная матрица не найдена для {base_name}")

                # Сохраняем матрицу в файл .matrix
                if file_path:
                    try:
                        from app.utils.load_utils import save_matrix_to_file

                        matrix_file_path = os.path.splitext(file_path)[0] + ".matrix"
                        save_matrix_to_file(crosstalk_matrix, matrix_file_path)
                        print(f"[DEBUG] Матрица сохранена в {matrix_file_path}")
                    except Exception as e:
                        print(f"Ошибка при сохранении матрицы в файл: {e}")

            algorithm_index += 1

        # В обычном режиме создаем вкладки и показываем в интерфейсе
        if not is_statistics_only_mode:
            # Создаем вкладку Clean для первого результата
            if created_files:
                first_clean_file = created_files[0]
                first_clean_data = self.parent.registry.get_df(first_clean_file)
                self.parent.ensure_clean_tab()
                self.parent.plot_data(self.parent.clean_plot_widget, first_clean_data)
                self.parent.plot_manager.current_clean_file_base = base_name
                print(f"[DEBUG] Создана вкладка Clean для {first_clean_file}")

            # Финализируем результаты итераций для исходного файла
            if file_name:
                self.parent.plot_manager.finalize_iteration_results(file_name)
                print(f"[DEBUG] Финализированы результаты итераций для {file_name}")

            # Показываем матрицы и вкладку Info для всех созданных файлов
            for clean_file_name in created_files:
                # Показываем матрицу для этого файла
                matrix_shown = self.parent.plot_manager.show_matrix_for_file(
                    clean_file_name
                )
                print(
                    f"[DEBUG] Матрица для {clean_file_name}: {'показана' if matrix_shown else 'не показана'}"
                )

            # Показываем вкладку Info для первого файла
            if created_files:
                self.parent.plot_manager.show_info_for_file(created_files[0])
                print(f"[DEBUG] Показана вкладка Info для {created_files[0]}")

            # Переключаемся на вкладку Iterations если есть данные, иначе на Clean
            current_file_has_iterations = (
                file_name
                and file_name in self.parent.plot_manager.iteration_results_data
                and self.parent.plot_manager.iteration_results_data[file_name]
            )

            if current_file_has_iterations:
                self.parent.view_tabs.setCurrentWidget(self.parent.iterations_widget)
                print(f"[DEBUG] Переключились на вкладку Iterations")
            else:
                self.parent.view_tabs.setCurrentWidget(self.parent.clean_plot_widget)
                print(f"[DEBUG] Переключились на вкладку Clean")

            # Выбираем первый созданный файл в списке
            if created_files:
                first_clean_file = created_files[0]
                for i in range(self.parent.list_widget.count()):
                    if self.parent.list_widget.item(i).text() == first_clean_file:
                        self.parent.list_widget.setCurrentRow(i)
                        break
        else:
            # В режиме "только статистика" просто сохраняем информацию о последовательности
            if file_name and raw_data is not None:
                self.parent.plot_manager.store_sequence_info(
                    file_name, data_points, dye_names
                )
                print(
                    f"[DEBUG] Сохранена информация о последовательности для {file_name} (режим: только статистика)"
                )

        # Очищаем состояние множественной обработки
        self.dual_processing_results = {}
        self.current_algorithms = []
        self.current_algorithm_index = 0
        self.processing_thread = None
        self.current_processing_file = None

        # Проверяем, есть ли еще файлы в очереди
        if self.processing_queue and self.current_queue_index < len(
            self.processing_queue
        ):
            self._process_next_in_queue()
        else:
            self._finish_queue_processing()

    def _save_batch_statistics(self, file_count: int):
        """
        Автоматически сохраняет статистику обработанных файлов.

        Args:
            file_count: Количество обработанных файлов
        """
        import csv
        from datetime import datetime

        try:
            # Создаем папку statistics, если её нет
            statistics_dir = "statistics"
            if not os.path.exists(statistics_dir):
                os.makedirs(statistics_dir, exist_ok=True)

            # Генерируем имя файла: statistics_N_YYYYMMDD_HHMMSS.csv
            now = datetime.now()
            timestamp = now.strftime("%Y%m%d_%H%M%S")
            filename = f"statistics_{file_count}_{timestamp}.csv"
            file_path = os.path.join(statistics_dir, filename)

            # Собираем данные только для обработанных файлов
            with open(file_path, "w", newline="", encoding="utf-8-sig") as csvfile:
                # Определяем колонки
                fieldnames = [
                    "Файл",
                    "Количество точек",
                    "Реагенты",
                    "Сглаживание",
                    "Удаление базовой линии",
                    "Алгоритм",
                    "Разница матриц",
                ]

                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=";")
                writer.writeheader()

                # Счетчик экспортированных записей
                exported_count = 0

                # Экспортируем данные каждой последовательности
                for base_name, info in sorted(
                    self.parent.plot_manager.sequence_info.items()
                ):
                    data_points = info.get("data_points", 0)
                    dye_names = info.get("dye_names", [])
                    smooth_data = info.get("smooth_data", None)
                    remove_baseline = info.get("remove_baseline", None)
                    algorithm = info.get("algorithm", None)
                    matrix_difference = info.get("matrix_difference", None)

                    # Проверяем, был ли файл обработан
                    is_processed = (
                        smooth_data is not None
                        or remove_baseline is not None
                        or algorithm is not None
                        or matrix_difference is not None
                    )

                    # Пропускаем необработанные файлы
                    if not is_processed:
                        continue

                    # Форматируем значения
                    dyes_str = ", ".join(dye_names) if dye_names else "—"
                    smooth_str = (
                        "Да"
                        if smooth_data
                        else "Нет" if smooth_data is not None else "—"
                    )
                    baseline_str = (
                        "Да"
                        if remove_baseline
                        else "Нет" if remove_baseline is not None else "—"
                    )

                    if algorithm == "estimate_crosstalk_2":
                        algorithm_str = "Метод 2 (новый)"
                    elif algorithm == "estimate_crosstalk":
                        algorithm_str = "Метод 1 (старый)"
                    else:
                        algorithm_str = "—"

                    matrix_diff_str = (
                        f"{matrix_difference:.6f}"
                        if matrix_difference is not None
                        else "—"
                    )

                    writer.writerow(
                        {
                            "Файл": base_name,
                            "Количество точек": data_points,
                            "Реагенты": dyes_str,
                            "Сглаживание": smooth_str,
                            "Удаление базовой линии": baseline_str,
                            "Алгоритм": algorithm_str,
                            "Разница матриц": matrix_diff_str,
                        }
                    )

                    exported_count += 1

            print(
                f"Статистика автоматически сохранена: {file_path} ({exported_count} записей)"
            )

        except Exception as e:
            print(f"Ошибка при автоматическом сохранении статистики: {e}")

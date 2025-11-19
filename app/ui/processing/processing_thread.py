"""
Модуль для потоковой обработки данных с отслеживанием прогресса.

Этот модуль содержит класс DataProcessingThread, который обеспечивает
асинхронную обработку данных флуоресцентного секвенирования с подробным
отслеживанием прогресса и возможностью отмены операции.

Основные возможности:
- Асинхронная обработка в отдельном потоке
- Детальное отслеживание прогресса через callback
- Возможность отмены обработки
- Интеграция с Qt сигналами для обновления UI
- Обработка ошибок с подробными сообщениями

Пример использования:
    from app.ui.processing.processing_thread import DataProcessingThread

    # Создание потока
    thread = DataProcessingThread(path, data, smooth_data=True, remove_baseline=True)

    # Подключение сигналов
    thread.progress_updated.connect(update_progress)
    thread.processing_finished.connect(on_finished)
    thread.processing_error.connect(on_error)

    # Запуск обработки
    thread.start()

    # Отмена обработки (если нужно)
    thread.cancel()
"""

from PySide6.QtCore import QThread, Signal
import pandas as pd


class DataProcessingThread(QThread):
    """Поток для обработки данных с отправкой прогресса"""

    # Сигналы для обновления UI
    progress_updated = Signal(float, str)  # прогресс (0-100), сообщение
    processing_finished = Signal(
        pd.DataFrame, str, object
    )  # результат, путь к файлу, матрица
    processing_error = Signal(str)  # сообщение об ошибке

    def __init__(
        self,
        path,
        data,
        smooth_data=True,
        remove_baseline=True,
        window_size=21,
        polyorder=3,
        algorithm="estimate_crosstalk_2",
        save_data=True,
    ):
        """
        Инициализация потока обработки данных.

        Args:
            path (str): Путь к файлу данных
            data (pd.DataFrame): Данные для обработки
            smooth_data (bool): Выполнять ли сглаживание данных
            remove_baseline (bool): Выполнять ли коррекцию базовой линии
            window_size (int): Размер окна для сглаживания
            polyorder (int): Порядок полинома для сглаживания
            algorithm (str): Алгоритм оценки кросс-помех
            save_data (bool): Сохранять ли обработанные данные на диск
        """
        super().__init__()
        self.path = path
        self.data = data
        self.smooth_data = smooth_data
        self.remove_baseline = remove_baseline
        self.window_size = window_size
        self.polyorder = polyorder
        self.algorithm = algorithm
        self.save_data = save_data
        self.is_cancelled = False

    def cancel(self):
        """Отменить обработку"""
        self.is_cancelled = True

    def run(self):
        """Выполнение обработки в отдельном потоке"""
        try:
            # Импортируем здесь, чтобы избежать циклических зависимостей
            from app.core.processing import process_and_save
            from app.utils.seq_utils import deleteCrossTalk

            # Создаем callback для отслеживания прогресса
            def progress_callback(progress, message):
                if self.is_cancelled:
                    return
                self.progress_updated.emit(progress, message)

            # Callback для сохранения данных итераций
            def iteration_callback(iteration_num, iteration_data):
                if self.is_cancelled:
                    return
                # Отправляем данные итерации в главное окно через сигнал
                # Будем использовать progress_updated сигнал со специальным форматом
                import json

                iteration_signal_data = json.dumps(
                    {
                        "type": "iteration_data",
                        "iteration": iteration_num,
                        "data": {
                            f"{i},{j}": {
                                "x_data": data_dict["x_data"].tolist(),
                                "y_data": data_dict["y_data"].tolist(),
                                "slope": data_dict["slope"],
                                "intercept": data_dict["intercept"],
                                "x_regression_points": data_dict[
                                    "x_regression_points"
                                ].tolist(),
                                "y_regression_points": data_dict[
                                    "y_regression_points"
                                ].tolist(),
                            }
                            for (i, j), data_dict in iteration_data.items()
                        },
                    }
                )
                self.progress_updated.emit(
                    -1, iteration_signal_data
                )  # -1 как специальный код

            # Запускаем полную обработку с отслеживанием прогресса
            clean_data, crosstalk_matrix = deleteCrossTalk(
                self.data,
                M=None,
                rem_base=self.remove_baseline,
                smooth_data=self.smooth_data,
                progress_callback=progress_callback,
                iteration_callback=iteration_callback,
                window_size=self.window_size,
                polyorder=self.polyorder,
                return_matrix=True,
                algorithm=self.algorithm,
            )

            if self.is_cancelled:
                return

            # Сохранение результатов (только если включена опция)
            if self.save_data:
                self.progress_updated.emit(98, "Сохранение результатов...")
                if self.is_cancelled:
                    return

                clean_data_result, clean_path = process_and_save(
                    self.path, clean_data, smooth_data=False, remove_baseline=False
                )

                self.processing_finished.emit(
                    clean_data_result, clean_path, crosstalk_matrix
                )
            else:
                # Не сохраняем на диск, но все равно отправляем результаты
                self.progress_updated.emit(98, "Обработка завершена (без сохранения)")
                # Используем путь к исходному файлу как "путь" для результата
                self.processing_finished.emit(
                    clean_data, self.path, crosstalk_matrix
                )

        except Exception as e:
            self.processing_error.emit(f"Ошибка при обработке: {str(e)}")

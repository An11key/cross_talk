"""
Модуль управления данными файлов, матрицами и информацией о последовательностях.

Содержит класс DataManager для хранения и управления данными обработки:
матрицами кросс-помех, информацией о последовательностях и т.д.
"""

import os
import numpy as np
from typing import Dict, Optional


class DataManager:
    """Менеджер для управления данными файлов и матрицами."""

    def __init__(self, parent_window):
        """
        Инициализация менеджера данных.

        Args:
            parent_window: Родительское окно (экземпляр MyMenu)
        """
        self.parent = parent_window
        
        # Текущее базовое имя файла для clean вкладки
        self.current_clean_file_base = None

        # Матрицы кросс-помех для файлов
        # {file_name: crosstalk_matrix} (для обратной совместимости - одиночный алгоритм)
        self.crosstalk_matrices: Dict[str, np.ndarray] = {}
        
        # Матрицы кросс-помех для файлов по алгоритмам
        # {file_name: {algorithm: crosstalk_matrix}}
        self.crosstalk_matrices_by_algorithm: Dict[str, Dict[str, np.ndarray]] = {}

        # Оригинальные матрицы из .srd файлов
        # {file_name: original_matrix}
        self.original_matrices: Dict[str, np.ndarray] = {}

        # Информация о последовательностях (для обратной совместимости - одиночный алгоритм)
        # {file_name: {'data_points': int, 'dye_names': list, 'matrix_difference': float}}
        self.sequence_info: Dict[str, Dict] = {}
        
        # Информация о последовательностях по алгоритмам
        # {file_name: {algorithm: {'data_points': int, 'dye_names': list, 'matrix_difference': float, ...}}}
        self.sequence_info_by_algorithm: Dict[str, Dict[str, Dict]] = {}

    def store_crosstalk_matrix(self, file_name: str, matrix: np.ndarray):
        """
        Сохраняет матрицу кросс-помех для файла.

        Args:
            file_name: Имя файла
            matrix: Матрица кросс-помех 4x4
        """
        print(f"[DEBUG] store_crosstalk_matrix вызван с file_name='{file_name}'")
        # Получаем базовое имя файла (без расширения)
        base_name = file_name.split(".")[0]
        self.crosstalk_matrices[base_name] = matrix
        print(f"Сохранена матрица кросс-помех для {base_name}")

        # Если это .srd файл, пытаемся загрузить оригинальную матрицу
        if file_name.endswith(".srd"):
            print(f"[DEBUG] Файл оканчивается на .srd, загружаем оригинальную матрицу")
            self._load_original_matrix_from_srd(file_name)
        else:
            print(
                f"[DEBUG] Файл НЕ оканчивается на .srd, пропускаем загрузку оригинальной матрицы"
            )

    def _load_original_matrix_from_srd(self, file_name: str):
        """
        Загружает оригинальную матрицу из .srd файла.

        Args:
            file_name: Имя файла .srd
        """
        print(
            f"[DEBUG] _load_original_matrix_from_srd вызван с file_name='{file_name}'"
        )

        # Проверяем, не загружена ли уже матрица
        base_name = file_name.split(".")[0]
        if base_name in self.original_matrices:
            print(
                f"[DEBUG] Оригинальная матрица для {base_name} уже загружена, пропускаем"
            )
            return

        try:
            from app.utils.load_utils import load_matrix_from_srd

            # Получаем путь к файлу
            if self.parent.registry.has_file(file_name):
                file_path = self.parent.registry.get_path(file_name)
                print(f"[DEBUG] Путь к файлу: {file_path}")
                original_matrix = load_matrix_from_srd(file_path)
                original_matrix = original_matrix / original_matrix.sum(axis=0)
                print(f"[DEBUG] Матрица загружена, размер: {original_matrix.shape}")

                self.original_matrices[base_name] = original_matrix
                print(
                    f"Загружена оригинальная матрица из {file_name} (сохранена под ключом '{base_name}')"
                )
                print(
                    f"[DEBUG] Текущие оригинальные матрицы: {list(self.original_matrices.keys())}"
                )
            else:
                print(f"[DEBUG] Файл {file_name} не найден в реестре")
                print(
                    f"[DEBUG] Доступные файлы в реестре: {list(self.parent.registry._name_to_path.keys())}"
                )
        except Exception as e:
            print(f"Ошибка при загрузке оригинальной матрицы из {file_name}: {e}")
            import traceback

            traceback.print_exc()

    def store_crosstalk_matrix_for_algorithm(
        self, file_name: str, algorithm: str, matrix: np.ndarray
    ):
        """
        Сохраняет матрицу кросс-помех для файла и конкретного алгоритма.

        Args:
            file_name: Имя файла
            algorithm: Идентификатор алгоритма
            matrix: Матрица кросс-помех 4x4
        """
        base_name = file_name.split(".")[0]
        
        if base_name not in self.crosstalk_matrices_by_algorithm:
            self.crosstalk_matrices_by_algorithm[base_name] = {}
        
        self.crosstalk_matrices_by_algorithm[base_name][algorithm] = matrix
        print(f"Сохранена матрица кросс-помех для {base_name}, алгоритм {algorithm}")
        
        # Если это .srd файл, пытаемся загрузить оригинальную матрицу
        if file_name.endswith(".srd"):
            self._load_original_matrix_from_srd(file_name)

    def store_sequence_info(
        self,
        file_name: str,
        data_points: int,
        dye_names: list = None,
        smooth_data: bool = None,
        remove_baseline: bool = None,
        algorithm: str = None,
    ):
        """
        Сохраняет информацию о последовательности в память и в файл.

        Args:
            file_name: Имя файла
            data_points: Количество точек данных
            dye_names: Список названий красителей
            smooth_data: Было ли применено сглаживание
            remove_baseline: Было ли удаление базовой линии
            algorithm: Используемый алгоритм оценки кросс-помех
        """
        base_name = file_name.split(".")[0]

        if base_name not in self.sequence_info:
            self.sequence_info[base_name] = {}

        self.sequence_info[base_name]["data_points"] = data_points
        self.sequence_info[base_name]["dye_names"] = dye_names if dye_names else []

        # Сохраняем параметры обработки, если они указаны
        if smooth_data is not None:
            self.sequence_info[base_name]["smooth_data"] = smooth_data
        if remove_baseline is not None:
            self.sequence_info[base_name]["remove_baseline"] = remove_baseline
        if algorithm is not None:
            self.sequence_info[base_name]["algorithm"] = algorithm

        print(f"Сохранена информация о последовательности для {base_name}")
        print(f"  Точек данных: {data_points}")
        if dye_names:
            print(f"  Реагенты: {', '.join(dye_names)}")
        if smooth_data is not None:
            print(f"  Сглаживание: {'Да' if smooth_data else 'Нет'}")
        if remove_baseline is not None:
            print(f"  Удаление базовой линии: {'Да' if remove_baseline else 'Нет'}")
        if algorithm is not None:
            algorithm_name = (
                "Метод 2 (новый)"
                if algorithm == "estimate_crosstalk_2"
                else "Метод 1 (старый)"
            )
            print(f"  Алгоритм: {algorithm_name}")

        # Сохраняем информацию в файл
        self._save_sequence_info_to_file(base_name)

    def store_sequence_info_for_algorithm(
        self,
        file_name: str,
        algorithm: str,
        data_points: int,
        dye_names: list = None,
        smooth_data: bool = None,
        remove_baseline: bool = None,
        **kwargs
    ):
        """
        Сохраняет информацию о последовательности для конкретного алгоритма.

        Args:
            file_name: Имя файла
            algorithm: Идентификатор алгоритма
            data_points: Количество точек данных
            dye_names: Список названий красителей
            smooth_data: Было ли применено сглаживание
            remove_baseline: Было ли удаление базовой линии
        """
        base_name = file_name.split(".")[0]

        if base_name not in self.sequence_info_by_algorithm:
            self.sequence_info_by_algorithm[base_name] = {}
        
        if algorithm not in self.sequence_info_by_algorithm[base_name]:
            self.sequence_info_by_algorithm[base_name][algorithm] = {}

        info = self.sequence_info_by_algorithm[base_name][algorithm]
        info["data_points"] = data_points
        info["dye_names"] = dye_names if dye_names else []
        info["algorithm"] = algorithm

        # Сохраняем параметры обработки, если они указаны
        if smooth_data is not None:
            info["smooth_data"] = smooth_data
        if remove_baseline is not None:
            info["remove_baseline"] = remove_baseline

        print(f"Сохранена информация о последовательности для {base_name}, алгоритм {algorithm}")

    def store_matrix_difference(
        self, file_name: str, computed_matrix: np.ndarray, original_matrix: np.ndarray
    ):
        """
        Вычисляет и сохраняет разницу между матрицами в память и в файл.

        Args:
            file_name: Имя файла
            computed_matrix: Вычисленная матрица
            original_matrix: Оригинальная матрица из .srd файла
        """
        from app.utils.utils import get_matrix_difference

        base_name = file_name.split(".")[0]

        if base_name not in self.sequence_info:
            self.sequence_info[base_name] = {}

        difference = get_matrix_difference(computed_matrix, original_matrix)
        self.sequence_info[base_name]["matrix_difference"] = difference

        print(f"Сохранена разница между матрицами для {base_name}: {difference:.6f}")

        # Сохраняем информацию в файл
        self._save_sequence_info_to_file(base_name)

    def store_matrix_difference_for_algorithm(
        self, file_name: str, algorithm: str, computed_matrix: np.ndarray, original_matrix: np.ndarray
    ):
        """
        Вычисляет и сохраняет разницу между матрицами для конкретного алгоритма.

        Args:
            file_name: Имя файла
            algorithm: Идентификатор алгоритма
            computed_matrix: Вычисленная матрица
            original_matrix: Оригинальная матрица из .srd файла
        """
        from app.utils.utils import get_matrix_difference

        base_name = file_name.split(".")[0]

        if base_name not in self.sequence_info_by_algorithm:
            self.sequence_info_by_algorithm[base_name] = {}
        
        if algorithm not in self.sequence_info_by_algorithm[base_name]:
            self.sequence_info_by_algorithm[base_name][algorithm] = {}

        difference = get_matrix_difference(computed_matrix, original_matrix)
        self.sequence_info_by_algorithm[base_name][algorithm]["matrix_difference"] = difference

        print(
            f"Вычислена разница между матрицами для {base_name}, алгоритм {algorithm}: {difference:.6f}"
        )

    def _save_sequence_info_to_file(self, base_name: str):
        """
        Сохраняет информацию о последовательности в файл .info.

        Args:
            base_name: Базовое имя файла (без расширения)
        """
        from app.utils.load_utils import save_sequence_info_to_file

        if base_name not in self.sequence_info:
            print(f"Нет информации для сохранения для {base_name}")
            return

        info = self.sequence_info[base_name]
        data_points = info.get("data_points", 0)
        dye_names = info.get("dye_names", [])
        matrix_difference = info.get("matrix_difference", None)
        smooth_data = info.get("smooth_data", None)
        remove_baseline = info.get("remove_baseline", None)
        algorithm = info.get("algorithm", None)

        # Определяем путь к файлу .info
        processed_dir = "processed_sequences"
        sequence_folder = os.path.join(processed_dir, f"{base_name}_seq")

        # Создаем папку, если она не существует
        if not os.path.exists(sequence_folder):
            os.makedirs(sequence_folder, exist_ok=True)

        info_file_path = os.path.join(sequence_folder, f"{base_name}.info")

        try:
            save_sequence_info_to_file(
                info_file_path,
                data_points,
                dye_names,
                matrix_difference,
                smooth_data,
                remove_baseline,
                algorithm,
            )
        except Exception as e:
            print(f"Ошибка при сохранении информации в файл: {e}")

    def _load_sequence_info_from_file(self, base_name: str) -> bool:
        """
        Загружает информацию о последовательности из файла .info.

        Args:
            base_name: Базовое имя файла (без расширения)

        Returns:
            True, если информация успешно загружена, False иначе
        """
        from app.utils.load_utils import load_sequence_info_from_file

        # Определяем путь к файлу .info
        processed_dir = "processed_sequences"
        sequence_folder = os.path.join(processed_dir, f"{base_name}_seq")
        info_file_path = os.path.join(sequence_folder, f"{base_name}.info")

        if not os.path.exists(info_file_path):
            print(f"Файл .info не найден для {base_name}")
            return False

        try:
            info_data = load_sequence_info_from_file(info_file_path)

            # Сохраняем загруженную информацию в память
            if base_name not in self.sequence_info:
                self.sequence_info[base_name] = {}

            self.sequence_info[base_name]["data_points"] = info_data.get(
                "data_points", 0
            )
            self.sequence_info[base_name]["dye_names"] = info_data.get("dye_names", [])

            matrix_diff = info_data.get("matrix_difference", None)
            if matrix_diff is not None:
                self.sequence_info[base_name]["matrix_difference"] = matrix_diff

            # Загружаем параметры обработки
            smooth_data = info_data.get("smooth_data", None)
            if smooth_data is not None:
                self.sequence_info[base_name]["smooth_data"] = smooth_data

            remove_baseline = info_data.get("remove_baseline", None)
            if remove_baseline is not None:
                self.sequence_info[base_name]["remove_baseline"] = remove_baseline

            algorithm = info_data.get("algorithm", None)
            if algorithm is not None:
                self.sequence_info[base_name]["algorithm"] = algorithm

            print(f"Информация успешно загружена из файла для {base_name}")
            return True
        except Exception as e:
            print(f"Ошибка при загрузке информации из файла: {e}")
            return False

    def get_matrix_for_file(self, file_name: str) -> Optional[np.ndarray]:
        """
        Получает матрицу кросс-помех для файла.

        Args:
            file_name: Имя файла

        Returns:
            Матрица или None если не найдена
        """
        base_name = file_name.split(".")[0]
        return self.crosstalk_matrices.get(base_name, None)

    def get_original_matrix_for_file(self, file_name: str) -> Optional[np.ndarray]:
        """
        Получает оригинальную матрицу для файла.

        Args:
            file_name: Имя файла

        Returns:
            Оригинальная матрица или None если не найдена
        """
        base_name = file_name.split(".")[0]
        return self.original_matrices.get(base_name, None)

    def get_sequence_info_for_file(self, file_name: str) -> Optional[Dict]:
        """
        Получает информацию о последовательности для файла.

        Args:
            file_name: Имя файла

        Returns:
            Словарь с информацией или None если не найдена
        """
        base_name = file_name.split(".")[0]
        return self.sequence_info.get(base_name, None)

    def remove_data_for_file(self, base_name: str):
        """
        Удаляет все данные для указанного файла.

        Args:
            base_name: Базовое имя файла (без расширения)
        """
        # Удаляем матрицу кросс-помех
        if base_name in self.crosstalk_matrices:
            del self.crosstalk_matrices[base_name]
            print(f"Удалена матрица кросс-помех для {base_name}")

        # Удаляем оригинальную матрицу
        if base_name in self.original_matrices:
            del self.original_matrices[base_name]
            print(f"Удалена оригинальная матрица для {base_name}")

        # Удаляем информацию о последовательности
        if base_name in self.sequence_info:
            del self.sequence_info[base_name]
            print(f"Удалена информация о последовательности для {base_name}")

        # Удаляем данные по алгоритмам
        if base_name in self.crosstalk_matrices_by_algorithm:
            del self.crosstalk_matrices_by_algorithm[base_name]
            print(f"Удалены матрицы по алгоритмам для {base_name}")

        if base_name in self.sequence_info_by_algorithm:
            del self.sequence_info_by_algorithm[base_name]
            print(f"Удалена информация по алгоритмам для {base_name}")


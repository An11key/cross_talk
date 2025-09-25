import os
import pandas as pd
import json
import numpy as np
from app.utils.seq_utils import baseline_cor, estimate_crosstalk, deleteCrossTalk
import shutil


# Базовая папка для хранения обработанных последовательностей
SEQUENCES_BASE_DIR = "processed_sequences"


def get_sequence_folder(file_path: str) -> str:
    """Возвращает путь к папке для данной последовательности."""
    base_name = os.path.basename(file_path)
    only_name, _ = os.path.splitext(base_name)
    return os.path.join(SEQUENCES_BASE_DIR, f"{only_name}_seq")


def is_file_already_processed(file_path: str) -> tuple[bool, str | None]:
    """Проверяет, обрабатывался ли уже этот файл.

    Возвращает (True, clean_path) если файл уже обработан,
    иначе (False, None).
    """
    base_name = os.path.basename(file_path)
    only_name, ext = os.path.splitext(base_name)
    folder = get_sequence_folder(file_path)

    # Проверяем различные варианты очищенного файла
    clean_candidates = [
        f"{only_name}_clean{ext}",
        f"{only_name}_clean.csv",  # для .srd файлов
    ]

    for clean_filename in clean_candidates:
        clean_path = os.path.join(folder, clean_filename)
        if os.path.exists(clean_path):
            return True, clean_path

    return False, None


def process_and_save(
    path: str,
    data: pd.DataFrame,
    smooth_data: bool = True,
    remove_baseline: bool = True,
) -> tuple[pd.DataFrame, str]:
    """Обрабатывает файл и сохраняет результат в organized структуре папок."""
    # Создаём базовую папку для последовательностей
    if not os.path.exists(SEQUENCES_BASE_DIR):
        os.makedirs(SEQUENCES_BASE_DIR)

    data_copy = data.copy()

    # Применяем коррекцию базовой линии только если включена
    if remove_baseline:
        data_copy = baseline_cor(data_copy)

    # Обрабатываем данные с выбранными параметрами
    clean_data = deleteCrossTalk(data_copy, rem_base=False, smooth_data=smooth_data)

    # Определяем папку для этой последовательности
    folder = get_sequence_folder(path)
    if not os.path.exists(folder):
        os.makedirs(folder)

    # Копируем исходный файл в папку последовательности только если его там нет
    dest_original = os.path.join(folder, os.path.basename(path))
    if not os.path.exists(dest_original):
        shutil.copy(path, dest_original)

    # Сохраняем очищенные данные
    base_name = os.path.basename(path)
    only_name, ext = os.path.splitext(base_name)
    clean_ext = ".csv" if ext.lower() == ".srd" else ext
    clean_filename = f"{only_name}_clean{clean_ext}"
    clean_path = os.path.join(folder, clean_filename)
    clean_data.to_csv(clean_path, sep=";", index=False, header=False)

    return clean_data, clean_path


def save_iteration_data(file_path: str, iteration_data: dict) -> str:
    """Сохраняет данные итераций в JSON файл.

    Args:
        file_path: Путь к исходному файлу
        iteration_data: Данные итераций в формате {iteration_num: {(i,j): data_dict}}

    Returns:
        Путь к сохраненному файлу итераций
    """
    folder = get_sequence_folder(file_path)
    if not os.path.exists(folder):
        os.makedirs(folder)

    base_name = os.path.basename(file_path)
    only_name, _ = os.path.splitext(base_name)
    iterations_filename = f"{only_name}_iterations.json"
    iterations_path = os.path.join(folder, iterations_filename)

    # Конвертируем данные для JSON сериализации
    json_data = {}
    for iteration_num, iteration_dict in iteration_data.items():
        json_data[str(iteration_num)] = {}
        for (i, j), data_dict in iteration_dict.items():
            key = f"{i},{j}"
            json_data[str(iteration_num)][key] = {
                "x_data": (
                    data_dict["x_data"].tolist()
                    if isinstance(data_dict["x_data"], np.ndarray)
                    else data_dict["x_data"]
                ),
                "y_data": (
                    data_dict["y_data"].tolist()
                    if isinstance(data_dict["y_data"], np.ndarray)
                    else data_dict["y_data"]
                ),
                "slope": (
                    float(data_dict["slope"])
                    if data_dict["slope"] is not None
                    else None
                ),
                "intercept": (
                    float(data_dict["intercept"])
                    if data_dict["intercept"] is not None
                    else None
                ),
            }

    # Сохраняем в JSON файл
    with open(iterations_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    return iterations_path


def check_iteration_file_exists(file_path: str) -> bool:
    """Проверяет, существует ли файл итераций для данного файла.

    Args:
        file_path: Путь к исходному файлу

    Returns:
        True если файл итераций существует, False иначе
    """
    folder = get_sequence_folder(file_path)
    base_name = os.path.basename(file_path)
    only_name, _ = os.path.splitext(base_name)
    iterations_filename = f"{only_name}_iterations.json"
    iterations_path = os.path.join(folder, iterations_filename)

    return os.path.exists(iterations_path)


def load_iteration_data(file_path: str) -> tuple[bool, dict]:
    """Загружает данные итераций из JSON файла.

    Args:
        file_path: Путь к исходному файлу

    Returns:
        Кортеж (существует_ли_файл, данные_итераций)
    """
    folder = get_sequence_folder(file_path)
    base_name = os.path.basename(file_path)
    only_name, _ = os.path.splitext(base_name)
    iterations_filename = f"{only_name}_iterations.json"
    iterations_path = os.path.join(folder, iterations_filename)

    if not os.path.exists(iterations_path):
        return False, {}

    try:
        with open(iterations_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        # Конвертируем обратно в нужный формат
        iteration_data = {}
        for iteration_str, iteration_dict in json_data.items():
            iteration_num = int(iteration_str)
            iteration_data[iteration_num] = {}

            for key, data_dict in iteration_dict.items():
                i, j = map(int, key.split(","))
                iteration_data[iteration_num][(i, j)] = {
                    "x_data": np.array(data_dict["x_data"]),
                    "y_data": np.array(data_dict["y_data"]),
                    "slope": data_dict["slope"],
                    "intercept": data_dict["intercept"],
                }

        return True, iteration_data

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"Ошибка при загрузке данных итераций из {iterations_path}: {e}")
        return False, {}


def delete_processed_sequence(file_path: str) -> bool:
    """Удаляет папку с обработанными файлами для данной последовательности.

    Args:
        file_path: Путь к исходному файлу

    Returns:
        True если папка была успешно удалена, False иначе
    """
    folder = get_sequence_folder(file_path)

    if os.path.exists(folder):
        try:
            shutil.rmtree(folder)
            print(f"Удалена папка обработанных файлов: {folder}")
            return True
        except OSError as e:
            print(f"Ошибка при удалении папки {folder}: {e}")
            return False
    else:
        print(f"Папка {folder} не существует")
        return False

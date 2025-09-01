import os
import pandas as pd
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
        # Копируем исходный файл в папку последовательности
        dest_original = os.path.join(folder, os.path.basename(path))
        shutil.copy(path, dest_original)

    # Сохраняем очищенные данные
    base_name = os.path.basename(path)
    only_name, ext = os.path.splitext(base_name)
    clean_ext = ".csv" if ext.lower() == ".srd" else ext
    clean_filename = f"{only_name}_clean{clean_ext}"
    clean_path = os.path.join(folder, clean_filename)
    clean_data.to_csv(clean_path, sep=";", index=False, header=False)

    return clean_data, clean_path


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

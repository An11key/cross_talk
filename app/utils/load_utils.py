import os
import pandas as pd
from lxml import etree
import numpy as np


def load_dataframe_by_path(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".csv":
        return load_data_from_csv(file_path)
    if ext == ".srd":
        return load_data_from_srd(file_path)
    return load_data_from_csv(file_path)


def load_data_from_srd(file_path):
    tree = etree.parse(file_path)
    root = tree.getroot()
    df = pd.DataFrame(columns=["A", "G", "C", "T"])
    for point in root.xpath(".//Point"):
        data_elem = point.find("Data")
        if data_elem is not None:
            row = [int(value.text) for value in data_elem.xpath("./int")]
            df = pd.concat(
                [df, pd.DataFrame([row], columns=df.columns)], ignore_index=True
            )
    # Приводим к числовому типу float для совместимости с обработкой/отрисовкой
    df = make_numeric(df)
    return df


def load_matrix_from_srd(file_path):
    tree = etree.parse(file_path)
    root = tree.getroot()
    rows = root.xpath("./Matrix/ArrayOfDouble")

    # Преобразуем каждую строку в список значений
    data = []
    for row in rows:
        row_data = [float(val.text) for val in row.xpath(".//double")]
        data.append(row_data)

    matrix = np.array(data)
    matrix = matrix / matrix.sum(axis=0)
    return matrix


def load_dye_names_from_srd(file_path):
    tree = etree.parse(file_path)
    root = tree.getroot()
    dye_names = (
        [val.text for val in root.xpath("./DyeNames/string")]
        if root.xpath("./DyeNames/string")
        else []
    )
    return dye_names


def load_data_from_csv(file_path):
    data = pd.read_csv(
        file_path,
        sep=";",
        header=None,
        usecols=[0, 1, 2, 3],
        names=["A", "G", "C", "T"],
        encoding="utf-8-sig",
    )
    # Обеспечиваем числовой тип данных
    data = make_numeric(data)
    return data


def make_numeric(data):
    for col in data.columns:
        data[col] = pd.to_numeric(data[col], errors="coerce")
    data = data.fillna(0.0).astype(float)
    return data


def save_matrix_to_file(matrix: np.ndarray, file_path: str):
    """
    Сохраняет матрицу в файл .matrix.

    Args:
        matrix: Матрица numpy для сохранения
        file_path: Путь к файлу (с расширением .matrix)
    """
    # Сохраняем матрицу в текстовом формате с высокой точностью
    np.savetxt(file_path, matrix, fmt="%.10f", delimiter="\t")
    print(f"Матрица сохранена в файл: {file_path}")


def load_matrix_from_file(file_path: str) -> np.ndarray:
    """
    Загружает матрицу из файла .matrix.

    Args:
        file_path: Путь к файлу .matrix

    Returns:
        Загруженная матрица numpy
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Файл матрицы не найден: {file_path}")

    matrix = np.loadtxt(file_path, delimiter="\t")
    print(f"Матрица загружена из файла: {file_path}")
    return matrix


def save_sequence_info_to_file(
    file_path: str,
    data_points: int,
    dye_names: list = None,
    matrix_difference: float = None,
    smooth_data: bool = None,
    remove_baseline: bool = None,
    algorithm: str = None,
):
    """
    Сохраняет информацию о последовательности в файл .info.

    Args:
        file_path: Путь к файлу (с расширением .info)
        data_points: Количество точек данных
        dye_names: Список названий красителей (опционально)
        matrix_difference: Разница между матрицами (опционально)
        smooth_data: Было ли применено сглаживание (опционально)
        remove_baseline: Было ли удаление базовой линии (опционально)
        algorithm: Используемый алгоритм оценки кросс-помех (опционально)
    """
    import json

    info_data = {
        "data_points": data_points,
        "dye_names": dye_names if dye_names else [],
        "matrix_difference": matrix_difference,
    }

    # Добавляем параметры обработки, если они указаны
    if smooth_data is not None:
        info_data["smooth_data"] = smooth_data
    if remove_baseline is not None:
        info_data["remove_baseline"] = remove_baseline
    if algorithm is not None:
        info_data["algorithm"] = algorithm

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(info_data, f, ensure_ascii=False, indent=2)

    print(f"Информация о последовательности сохранена в файл: {file_path}")


def load_sequence_info_from_file(file_path: str) -> dict:
    """
    Загружает информацию о последовательности из файла .info.

    Args:
        file_path: Путь к файлу .info

    Returns:
        Словарь с информацией о последовательности:
        {
            'data_points': int,
            'dye_names': list,
            'matrix_difference': float or None,
            'smooth_data': bool or None,
            'remove_baseline': bool or None,
            'algorithm': str or None
        }
    """
    import json

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Файл информации не найден: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        info_data = json.load(f)

    print(f"Информация о последовательности загружена из файла: {file_path}")
    return info_data

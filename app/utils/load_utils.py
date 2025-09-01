import os
import pandas as pd
from lxml import etree


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

from __future__ import annotations
from typing import Optional, List
import pandas as pd
import numpy as np
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Sequence:

    def __init__(
        self,
        dataframe: pd.DataFrame,
        name: str,
        source_path: Optional[str] = None,
        matrix: Optional[np.ndarray] = None,
        dye_names: Optional[List[str]] = None,
    ) -> None:
        required_columns = {"A", "G", "C", "T"}
        if not required_columns == set(dataframe.columns):
            raise ValueError(
                f"DataFrame должен содержать колонки: {required_columns}. "
                f"Найдены: {set(dataframe.columns)}"
            )

        self.dataframe = dataframe.copy()
        self.name = name
        self.source_path = source_path
        self.matrix = matrix
        self.dye_names = dye_names
        logger.info(
            f"Создана последовательность '{name}' с {len(dataframe)} точками данных"
        )

    def __repr__(self) -> str:
        return f"Sequence(name='{self.name}', length={len(self.dataframe)})"

    def __len__(self) -> int:
        return len(self.dataframe)

    def __eq__(self, other: Sequence) -> bool:
        return self.name == other.name and len(self) == len(other)

    def validate_data(self) -> bool:
        try:
            # Проверяем, что все значения числовые
            for col in ["A", "G", "C", "T"]:
                pd.to_numeric(self.dataframe[col], errors="raise")

            # Проверяем наличие данных
            if self.dataframe.empty:
                logger.warning(
                    f"Последовательность '{self.name}' содержит пустые данные"
                )
                return False

            return True

        except (ValueError, TypeError) as e:
            logger.error(f"Ошибка валидации данных для '{self.name}': {e}")
            return False

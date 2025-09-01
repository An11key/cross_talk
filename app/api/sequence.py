from typing import Optional
from __future__ import annotations
import pandas as pd

import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Sequence:
    """
    Класс для хранения одной нуклеотидной последовательности.

    Attributes:
        dataframe (pd.DataFrame): DataFrame с 4 колонками (A, C, G, T)
                                 содержащий интенсивности сигналов
        name (str): Имя последовательности
        source_path (Optional[str]): Путь к исходному файлу
    """

    def __init__(
        self, dataframe: pd.DataFrame, name: str, source_path: Optional[str] = None
    ) -> None:
        """
        Инициализация последовательности.

        Args:
            dataframe: DataFrame с колонками A, C, G, T
            name: Имя последовательности
            source_path: Путь к исходному файлу (опционально)

        Raises:
            ValueError: Если DataFrame не содержит нужные колонки
        """
        required_columns = {"A", "G", "C", "T"}
        if not required_columns == set(dataframe.columns):
            raise ValueError(
                f"DataFrame должен содержать колонки: {required_columns}. "
                f"Найдены: {set(dataframe.columns)}"
            )

        self.dataframe = dataframe.copy()
        self.name = name
        self.source_path = source_path

        logger.info(
            f"Создана последовательность '{name}' с {len(dataframe)} точками данных"
        )

    def __repr__(self) -> str:
        return f"Sequence(name='{self.name}', length={len(self.dataframe)})"

    def __len__(self) -> int:
        """Возвращает длину последовательности."""
        return len(self.dataframe)

    def __eq__(self, other: Sequence) -> bool:
        """Проверяет равенство последовательностей."""
        return self.name == other.name and len(self) == len(other)

    def validate_data(self) -> bool:
        """
        Проверяет корректность данных последовательности.

        Returns:
            True если данные корректны, False иначе
        """
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

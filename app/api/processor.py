from typing import Optional, List

import pandas as pd
from pathlib import Path
from app.api.sequence import Sequence
from app.utils.seq_utils import deleteCrossTalk
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Processor:
    """
    Класс для обработки списка нуклеотидных последовательностей.

    Attributes:
        sequences (List[Sequence]): Список последовательностей для обработки
        output_directory (str): Директория для сохранения результатов
    """

    def __init__(
        self,
        sequences: Optional[List[Sequence]] = None,
        output_directory: str = "processed_sequences",
    ) -> None:
        """
        Инициализация процессора.

        Args:
            sequences: Список последовательностей для обработки
            output_directory: Директория для сохранения результатов
        """
        self.sequences: List[Sequence] = sequences or []
        self.output_directory = output_directory

        # Создаем выходную директорию если её нет
        Path(self.output_directory).mkdir(exist_ok=True)

        logger.info(
            f"Инициализирован процессор с {len(self.sequences)} последовательностями, "
            f"выходная директория: {self.output_directory}"
        )

    def add_sequence(self, sequence: Sequence) -> None:
        """
        Добавляет последовательность в список для обработки.

        Args:
            sequence: Последовательность для добавления
        """
        self.sequences.append(sequence)
        logger.info(f"Добавлена последовательность '{sequence.name}'")

    def add_sequences(self, sequences: List[Sequence]) -> None:
        """
        Добавляет несколько последовательностей в список для обработки.

        Args:
            sequences: Список последовательностей для добавления
        """
        self.sequences.extend(sequences)
        logger.info(f"Добавлено {len(sequences)} последовательностей")

    def clear_sequences(self) -> None:
        """Очищает список последовательностей."""
        count = len(self.sequences)
        self.sequences.clear()
        logger.info(f"Удалено {count} последовательностей из списка")

    def process_sequence(
        self, sequence: Sequence, save_files: bool = True
    ) -> tuple[pd.DataFrame, Optional[str]]:
        """
        Обрабатывает одну последовательность - удаляет перекрестные помехи.

        Args:
            sequence: Последовательность для обработки
            save_files: Сохранять ли файлы на диск

        Returns:
            Кортеж (очищенный_dataframe, путь_к_папке_или_None)

        Raises:
            ValueError: Если данные последовательности некорректны
        """
        logger.info(f"Начало обработки последовательности '{sequence.name}'")

        # Валидация данных
        if not sequence.validate_data():
            raise ValueError(
                f"Некорректные данные в последовательности '{sequence.name}'"
            )

        # Обработка: удаление перекрестных помех
        try:
            clean_dataframe = deleteCrossTalk(sequence.dataframe.copy())
            logger.info(f"Успешно очищена последовательность '{sequence.name}'")

        except Exception as e:
            logger.error(
                f"Ошибка при обработке последовательности '{sequence.name}': {e}"
            )
            raise

        sequence_folder = None

        if save_files:
            # Создание папки для последовательности
            sequence_folder = Path(self.output_directory) / f"{sequence.name}_seq"
            sequence_folder.mkdir(exist_ok=True)

            # Сохранение исходных данных (raw.csv)
            raw_path = sequence_folder / "raw.csv"
            sequence.dataframe.to_csv(raw_path, sep=";", index=False, header=False)
            logger.info(f"Сохранены исходные данные: {raw_path}")

            # Сохранение очищенных данных (clean.csv)
            clean_path = sequence_folder / "clean.csv"
            clean_dataframe.to_csv(clean_path, sep=";", index=False, header=False)
            logger.info(f"Сохранены очищенные данные: {clean_path}")

        return clean_dataframe, str(sequence_folder) if sequence_folder else None

    def process_all(
        self, save_files: bool = True
    ) -> List[tuple[Sequence, pd.DataFrame, Optional[str]]]:
        """
        Обрабатывает все последовательности в списке.

        Args:
            save_files: Сохранять ли файлы на диск

        Returns:
            Список кортежей (исходная_последовательность, очищенный_dataframe, путь_к_папке)

        Raises:
            ValueError: Если список последовательностей пуст
        """
        if not self.sequences:
            raise ValueError(
                "Список последовательностей пуст. Добавьте последовательности перед обработкой."
            )

        logger.info(f"Начало обработки {len(self.sequences)} последовательностей")

        results = []
        successful_count = 0
        failed_count = 0

        for i, sequence in enumerate(self.sequences, 1):
            try:
                logger.info(f"Обработка {i}/{len(self.sequences)}: '{sequence.name}'")

                clean_dataframe, folder_path = self.process_sequence(
                    sequence, save_files
                )
                results.append((sequence, clean_dataframe, folder_path))
                successful_count += 1

            except Exception as e:
                logger.error(
                    f"Не удалось обработать последовательность '{sequence.name}': {e}"
                )
                failed_count += 1
                # Добавляем None результат для неудачной обработки
                results.append((sequence, None, None))

        logger.info(
            f"Обработка завершена. Успешно: {successful_count}, "
            f"с ошибками: {failed_count}, всего: {len(self.sequences)}"
        )

        return results

    def get_statistics(self) -> dict:
        """
        Возвращает статистику по загруженным последовательностям.

        Returns:
            Словарь со статистикой
        """
        if not self.sequences:
            return {"count": 0, "total_length": 0, "average_length": 0}

        lengths = [len(seq) for seq in self.sequences]

        return {
            "count": len(self.sequences),
            "total_length": sum(lengths),
            "average_length": sum(lengths) / len(lengths),
            "min_length": min(lengths),
            "max_length": max(lengths),
        }

    def __repr__(self) -> str:
        return f"Processor(sequences={len(self.sequences)}, output_dir='{self.output_directory}')"

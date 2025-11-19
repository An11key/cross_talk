from typing import Optional, List

import pandas as pd
from pathlib import Path
from app.api.sequence import Sequence
from app.utils.load_utils import load_data_from_srd
from app.utils.seq_utils import deleteCrossTalk
from app.utils.utils import get_matrix_difference
from concurrent.futures import ProcessPoolExecutor, as_completed
import os
from datetime import datetime


class Processor:
    def __init__(
        self,
        need_save: bool = False,
        need_statistics: bool = False,
        save_path: Optional[str] = "processed_sequences",
        statistics_path: Optional[str] = "statistics",
    ) -> None:
        self.need_save = need_save
        self.need_statistics = need_statistics
        self.save_path = save_path
        self.statistics_path = statistics_path

    def process_single_sequence(self, sequence: Sequence, algorithms: List[int]):
        try:
            if sequence.matrix is not None:
                matrix = sequence.matrix
            else:
                matrix = None
            file_statistics = []
            clear_data = []
            # Применение каждого алгоритма
            for algorithm in algorithms:
                if algorithm == 1:
                    cur_data, W = deleteCrossTalk(
                        sequence.dataframe,
                        rem_base=True,
                        algorithm="estimate_crosstalk",
                        return_matrix=True,
                    )
                    clear_data.append(cur_data)
                elif algorithm == 2:
                    cur_data, W = deleteCrossTalk(
                        sequence.dataframe,
                        rem_base=True,
                        algorithm="estimate_crosstalk_2",
                        return_matrix=True,
                    )
                    clear_data.append(cur_data)

                matrix_difference = get_matrix_difference(W, matrix)
                file_statistics.append(
                    {
                        "Name": sequence.name,
                        "Algorithm": algorithm,
                        "Matrix Difference": matrix_difference,
                        "Dye Names": sequence.dye_names,
                    }
                )
            if self.need_save:
                for i, data in enumerate(clear_data):
                    data.to_csv(
                        f"{self.save_path}/{sequence.name}_{algorithms[i]}.csv",
                        index=False,
                        sep=";",
                    )
            return file_statistics

        except Exception as e:
            print(f"Ошибка при обработке последовательности {sequence.name}: {e}")
            return []

    def process_sequences(self, sequences, alg=-1, max_workers=None):
        algorithms = []

        # Определение алгоритмов для применения
        if alg == -1:
            algorithms = [1, 2]
        elif alg == 1:
            algorithms = [1]
        elif alg == 2:
            algorithms = [2]
        else:
            raise ValueError(f"Invalid algorithm: {alg}")

        statistics = []

        # Параллельная обработка файлов
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Запускаем обработку всех файлов параллельно
            futures = {
                executor.submit(
                    self.process_single_sequence, sequence, algorithms
                ): sequence
                for sequence in sequences
            }

            # Собираем результаты по мере их готовности
            for future in as_completed(futures):
                sequence = futures[future]
                try:
                    sequence_stats = future.result()
                    if sequence_stats is not None:
                        statistics.extend(sequence_stats)
                    print(f"Обработана последовательность: {sequence.name}")
                except Exception as e:
                    print(
                        f"Ошибка при обработке последовательности {sequence.name}: {e}"
                    )

        # Создание DataFrame и сохранение результатов
        statistics = pd.DataFrame(statistics)
        if self.need_statistics:
            statistics.to_csv(
                f"{self.statistics_path}/statistics_{len(sequences)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                index=False,
                sep=";",
            )
            print(
                f"Обработка завершена. Обработано последовательностей: {len(sequences)}"
            )
        return statistics

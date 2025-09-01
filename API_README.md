# API для работы с нуклеотидными последовательностями

Этот API предоставляет удобную обертку для обработки нуклеотидных последовательностей, включая удаление перекрестных помех (crosstalk).

## Основные классы

### Класс `Sequence`

Представляет одну нуклеотидную последовательность.

**Атрибуты:**

-   `dataframe` (pd.DataFrame): DataFrame с 4 колонками (A, C, G, T) содержащий интенсивности сигналов
-   `name` (str): Имя последовательности
-   `source_path` (Optional[str]): Путь к исходному файлу

**Методы:**

-   `__init__(dataframe, name, source_path=None)`: Создание последовательности
-   `get_length()`: Возвращает длину последовательности
-   `validate_data()`: Проверяет корректность данных

**Пример использования:**

```python
import pandas as pd
from sequence_api import Sequence

# Создание DataFrame с данными
data = pd.DataFrame({
    'A': [100, 200, 150],
    'C': [80, 180, 120],
    'G': [90, 190, 130],
    'T': [70, 170, 110]
})

# Создание последовательности
sequence = Sequence(
    dataframe=data,
    name="my_sequence",
    source_path="path/to/file.csv"
)

print(f"Длина последовательности: {sequence.get_length()}")
```

### Класс `Processor`

Обрабатывает список нуклеотидных последовательностей.

**Атрибуты:**

-   `sequences` (List[Sequence]): Список последовательностей для обработки
-   `output_directory` (str): Директория для сохранения результатов

**Методы:**

-   `__init__(sequences=None, output_directory="processed_sequences")`: Создание процессора
-   `add_sequence(sequence)`: Добавляет одну последовательность
-   `add_sequences(sequences)`: Добавляет несколько последовательностей
-   `clear_sequences()`: Очищает список последовательностей
-   `process_sequence(sequence, save_files=True)`: Обрабатывает одну последовательность
-   `process_all(save_files=True)`: Обрабатывает все последовательности
-   `get_statistics()`: Возвращает статистику по последовательностям

**Пример использования:**

```python
from sequence_api import Sequence, Processor

# Создание процессора
processor = Processor(output_directory="my_results")

# Добавление последовательностей
processor.add_sequence(sequence1)
processor.add_sequence(sequence2)

# Обработка всех последовательностей
results = processor.process_all()

# Анализ результатов
for original_seq, clean_data, folder_path in results:
    if clean_data is not None:
        print(f"Успешно обработана: {original_seq.name}")
        print(f"Результаты сохранены в: {folder_path}")
    else:
        print(f"Ошибка при обработке: {original_seq.name}")
```

## Структура выходных файлов

Для каждой обработанной последовательности создается отдельная папка с именем `{sequence_name}_seq` в указанной выходной директории.

В каждой папке создаются два файла:

-   `raw.csv` — исходные данные последовательности
-   `clean.csv` — данные после удаления перекрестных помех

Пример структуры:

```
processed_sequences/
├── sequence1_seq/
│   ├── raw.csv
│   └── clean.csv
├── sequence2_seq/
│   ├── raw.csv
│   └── clean.csv
└── ...
```

## Логирование

API использует стандартное логирование Python. Все операции логируются с соответствующим уровнем:

-   INFO: Обычные операции (создание, добавление, обработка)
-   WARNING: Предупреждения (пустые данные)
-   ERROR: Ошибки (некорректные данные, ошибки обработки)

## Обработка ошибок

API содержит проверки на:

-   Корректность структуры DataFrame (наличие колонок A, C, G, T)
-   Валидность числовых данных
-   Пустые последовательности
-   Ошибки при обработке функцией `deleteCrossTalk`

## Интеграция с существующим кодом

API использует уже существующую функцию `deleteCrossTalk` из модуля `utils.py`. Никакие UI компоненты не затрагиваются - это чистая обертка для удобного использования существующего функционала.

## Полный пример использования

```python
from sequence_api import Sequence, Processor
from utils import load_data_from_csv

# 1. Загрузка данных
data1 = load_data_from_csv("data/sequence1.csv")
data2 = load_data_from_csv("data/sequence2.csv")

# 2. Создание последовательностей
seq1 = Sequence(data1, "sequence1", "data/sequence1.csv")
seq2 = Sequence(data2, "sequence2", "data/sequence2.csv")

# 3. Создание и настройка процессора
processor = Processor(
    sequences=[seq1, seq2],
    output_directory="experiment_results"
)

# 4. Получение статистики
stats = processor.get_statistics()
print(f"Загружено {stats['count']} последовательностей")
print(f"Средняя длина: {stats['average_length']:.1f}")

# 5. Обработка всех последовательностей
results = processor.process_all()

# 6. Анализ результатов
successful = sum(1 for _, clean_data, _ in results if clean_data is not None)
print(f"Успешно обработано: {successful}/{len(results)} последовательностей")
```

## Зависимости

-   pandas
-   numpy (через utils.py)
-   logging (стандартная библиотека)
-   pathlib (стандартная библиотека)
-   typing (стандартная библиотека)

Все зависимости для обработки данных уже присутствуют в существующем проекте.

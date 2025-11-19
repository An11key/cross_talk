"""
Модуль для обработки данных секвенирования и устранения перекрестных помех.

Этот модуль содержит функции для анализа и коррекции данных флуоресцентных сигналов
в процессе секвенирования ДНК. Основные возможности:

- Оценка матрицы перекрестных помех между каналами флуоресценции
- Коррекция базовой линии сигналов
- Устранение перекрестных помех между каналами A, C, G, T
- L1-регрессия для робустной оценки параметров

Функции модуля:
    estimate_crosstalk: Итеративная оценка матрицы перекрестных помех
    baseline_cor: Коррекция базовой линии сигналов
    l1_regression: L1-регрессия (квантильная регрессия с медианой)
    deleteCrossTalk: Основная функция устранения перекрестных помех

"""

from __future__ import annotations
from statsmodels.regression.quantile_regression import QuantReg
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from app.utils.utils import makeFig, smooth_func
from peakutils import baseline
import statsmodels.api as sm


def estimate_crosstalk_2(
    data,
    epsilon=0.005,
    iter=11,
    progress_callback=None,
    iteration_callback=None,
):
    """
    Альтернативный метод итеративной оценки матрицы перекрестных помех.

    Использует упрощенный подход без разбиения на интервалы, работает напрямую
    с отфильтрованными данными для более быстрой оценки.

    Args:
        data (pd.DataFrame): Данные флуоресценции с колонками для каждого канала (A, G, C, T)
        bins (int, optional): Параметр для совместимости. По умолчанию 300
        epsilon (float, optional): Критерий сходимости. По умолчанию 0.005
        iter (int, optional): Максимальное количество итераций. По умолчанию 11
        progress_callback (callable, optional): Функция обратного вызова для отправки прогресса.
                                               Принимает (progress_percent, message)
        iteration_callback (callable, optional): Функция обратного вызова для сохранения данных итерации.
                                                Принимает (iteration_num, iteration_data)

    Returns:
        np.ndarray: Нормализованная матрица перекрестных помех размером 4x4
    """
    W = np.eye(4)
    names = data.columns
    iteration = 1

    # Определяем названия каналов для сообщений
    channel_names = ["A", "G", "C", "T"]

    # Отправляем начальный прогресс
    if progress_callback:
        progress_callback(0, "Начало оценки перекрестных помех (метод 2)")

    max_iterations = iter - 1  # iteration < iter, так что максимум iter-1
    current_operation = 0

    while iteration < iter:
        W_estim = np.eye(4)
        slopes = []

        # Данные текущей итерации для callback
        iteration_data = {}

        for i in range(4):
            for j in range(4):
                if i is j:
                    continue

                current_operation += 1
                # Отправляем прогресс для текущей операции
                if progress_callback:
                    iteration_progress = (iteration - 1) / max_iterations
                    channel_progress = (
                        i * 3 + (j if j < i else j - 1)
                    ) / 12  # 0-11 для 12 пар
                    total_progress = (
                        iteration_progress + channel_progress / max_iterations
                    ) * 100

                    message = f"Итерация {iteration}/{max_iterations} | Анализ {channel_names[i]} vs {channel_names[j]}"
                    progress_callback(min(total_progress, 95), message)

                name_x = names[i]
                name_y = names[j]
                q1 = data[name_x].quantile(0.6)
                q2 = data[name_x].quantile(0.99)
                filt_data = data[(data[name_x] >= q1) & (data[name_x] <= q2)]
                filt_data = filt_data[filt_data[name_x] == filt_data.max(axis=1)]

                # Проверяем, что есть достаточно данных для обработки
                if len(filt_data.index) == 0:
                    continue

                # bins = max(1, len(filt_data.index) // 8)  # Минимум 1
                # intervals = np.array_split(filt_data, bins)
                # max_rows = []
                # for interval in intervals:
                #     if not interval.empty:
                #         average_x = interval[name_x].mean()
                #         average_y = interval[name_y].mean()
                #         if average_x > average_y:
                #             max_index = interval[name_y].idxmin()
                #             max_rows.append(interval.loc[max_index])
                #         else:
                #             continue
                # if not max_rows:
                #     continue
                # max_df = pd.DataFrame(max_rows)
                # x = max_df[name_x]
                # y = max_df[name_y]
                x = filt_data[name_x]
                y = filt_data[name_y]

                # Проверяем, что есть минимум 2 точки для регрессии
                if len(x) < 2:
                    continue

                try:
                    interc, slope = l1_regression(x, y, 0.5)
                    W_estim[j, i] = slope
                    slopes.append(slope)
                except Exception as e:
                    print(
                        f"[WARNING] Ошибка регрессии для {channel_names[i]} vs {channel_names[j]}: {e}"
                    )
                    continue

                # Сохраняем все точки и рассчитанный slope для visualization callback
                if iteration_callback is not None and not data.empty:
                    x_all = data[name_x].values
                    y_all = data[name_y].values

                    # Получаем координаты точек регрессии
                    x_regression = x.values if len(x) > 0 else np.array([])
                    y_regression = y.values if len(y) > 0 else np.array([])

                    iteration_data[(i, j)] = {
                        "x_data": x_all,
                        "y_data": y_all,
                        "x_regression_points": x_regression,
                        "y_regression_points": y_regression,
                        "slope": slope,
                        "intercept": interc,
                    }

        # Отправляем данные итерации в callback
        if iteration_callback is not None and iteration_data:
            iteration_callback(iteration, iteration_data)

        if abs(max(slopes)) < epsilon:
            if progress_callback:
                progress_callback(95, f"Достигнута сходимость на итерации {iteration}")
            break

        data = (np.linalg.inv(W_estim) @ data.T).T
        data.columns = names
        W = W @ W_estim
        iteration += 1

        # Отправляем прогресс после каждой итерации
        if progress_callback:
            iteration_progress = min(iteration / max_iterations * 100, 95)
            message = f"Завершена итерация {iteration-1}/{max_iterations}"
            progress_callback(iteration_progress, message)

    W = W / W.sum(axis=0)

    # Отправляем финальный прогресс
    if progress_callback:
        progress_callback(100, "Оценка перекрестных помех завершена (метод 2)")

    return W


def estimate_crosstalk(
    data,
    bins=300,
    epsilon=0.01,
    iter=11,
    progress_callback=None,
    iteration_callback=None,
):
    """
    Итеративная оценка матрицы перекрестных помех между каналами флуоресценции.

    Функция использует итеративный алгоритм для оценки матрицы перекрестных помех W,
    где W[i,j] показывает влияние канала j на канал i. Алгоритм основан на анализе
    минимальных значений в интервалах высоких сигналов для каждой пары каналов.

    Args:
        data (pd.DataFrame): Данные флуоресценции с колонками для каждого канала (A, G, C, T)
        bins (int, optional): Количество интервалов для разбиения данных. По умолчанию 300
        epsilon (float, optional): Критерий сходимости - максимальное изменение наклонов.
                                 По умолчанию 0.05
        iter (int, optional): Максимальное количество итераций. По умолчанию 11
        show_fig (bool, optional): Показывать ли графики в процессе итераций.
                                 По умолчанию False
        progress_callback (callable, optional): Функция обратного вызова для отправки прогресса.
                                               Принимает (progress_percent, message)
        iteration_callback (callable, optional): Функция обратного вызова для сохранения данных итерации.
                                                Принимает (iteration_num, iteration_data)

    Returns:
        np.ndarray: Нормализованная матрица перекрестных помех размером 4x4,
                   где сумма по каждому столбцу равна 1

    Note:
        Алгоритм использует квантили 0.6-0.99 для выбора участков с высокими сигналами
        и L1-регрессию для робустной оценки коэффициентов перекрестных помех.
    """
    W = np.eye(4)
    data = data
    names = data.columns
    iteration = 1

    # Определяем названия каналов для сообщений
    channel_names = ["A", "G", "C", "T"]

    # Отправляем начальный прогресс
    if progress_callback:
        progress_callback(0, "Начало оценки перекрестных помех")

    max_iterations = iter - 1  # iteration < iter, так что максимум iter-1
    total_operations = max_iterations * 4 * 3  # итерации × каналы × пары
    current_operation = 0

    while iteration < iter:
        slopes = []
        W_estim = np.eye(4)

        # Данные текущей итерации для callback
        iteration_data = {}

        for i in range(4):
            for j in range(4):
                if i is j:
                    continue

                current_operation += 1
                # Отправляем прогресс для текущей операции
                if progress_callback:
                    iteration_progress = (iteration - 1) / max_iterations
                    channel_progress = (
                        i * 3 + (j if j < i else j - 1)
                    ) / 12  # 0-11 для 12 пар
                    total_progress = (
                        iteration_progress + channel_progress / max_iterations
                    ) * 100

                    message = f"Итерация {iteration}/{max_iterations} | Анализ {channel_names[i]} vs {channel_names[j]}"
                    progress_callback(min(total_progress, 95), message)

                name_x = names[i]
                name_y = names[j]

                q1 = data[name_x].quantile(0.6)
                q2 = data[name_x].quantile(0.99)

                filt_data = data[(data[name_x] >= q1) & (data[name_x] <= q2)]
                result_data = filt_data[[name_x, name_y]]

                # Проверяем, что есть достаточно данных для обработки
                if len(result_data.index) == 0:
                    continue

                # Продолжаем обычную логику для расчёта коэффициентов
                bins = max(1, len(result_data.index) // 8)  # Минимум 1
                intervals = np.array_split(result_data, bins)
                min_rows = []

                for interval in intervals:
                    if not interval.empty:
                        average_y = interval[name_y].mean()
                        average_x = interval[name_x].mean()

                        if average_x > average_y:
                            min_index = interval[name_y].idxmin()
                            min_rows.append(interval.loc[min_index])
                        else:
                            continue
                if not min_rows:
                    continue

                min_df = pd.DataFrame(min_rows)
                x = min_df[name_x]
                y = min_df[name_y]

                # Проверяем, что есть минимум 2 точки для регрессии
                if len(x) < 2:
                    continue

                try:
                    interc, slope = l1_regression(x, y, 0.5)
                    W_estim[j, i] = slope
                    slopes.append(slope)
                except Exception as e:
                    print(
                        f"[WARNING] Ошибка регрессии для {channel_names[i]} vs {channel_names[j]}: {e}"
                    )
                    continue

                # Сохраняем все точки и рассчитанный slope для visualization callback
                if iteration_callback is not None and not data.empty:
                    x_all = data[name_x].values
                    y_all = data[name_y].values

                    # Получаем координаты точек регрессии (минимумы из интервалов)
                    x_regression = x.values if len(x) > 0 else np.array([])
                    y_regression = y.values if len(y) > 0 else np.array([])

                    iteration_data[(i, j)] = {
                        "x_data": x_all,
                        "y_data": y_all,
                        "x_regression_points": x_regression,
                        "y_regression_points": y_regression,
                        "slope": slope,
                        "intercept": interc,
                    }

        # Отправляем данные итерации в callback
        if iteration_callback is not None and iteration_data:
            iteration_callback(iteration, iteration_data)

        if abs(max(slopes)) < epsilon:
            if progress_callback:
                progress_callback(95, f"Достигнута сходимость на итерации {iteration}")
            break

        data = (np.linalg.inv(W_estim) @ data.T).T
        data.columns = names
        iteration += 1
        W = W @ W_estim

        # Отправляем прогресс после каждой итерации
        if progress_callback:
            iteration_progress = min(iteration / max_iterations * 100, 95)
            message = f"Завершена итерация {iteration-1}/{max_iterations}"
            progress_callback(iteration_progress, message)
    W = W / W.sum(axis=0)

    # Отправляем финальный прогресс
    if progress_callback:
        progress_callback(100, "Оценка перекрестных помех завершена")

    return W


def baseline_cor(data, deg=6):
    """
    Коррекция базовой линии для всех каналов флуоресцентных данных.

    Функция вычитает из каждого канала его базовую линию, полученную с помощью
    алгоритма Asymmetric Least Squares (ALS). Это позволяет устранить дрейф
    базовой линии и улучшить качество дальнейшего анализа.

    Args:
        data (pd.DataFrame): Данные флуоресценции с колонками для каждого канала
        deg (int, optional): Степень полинома для аппроксимации базовой линии.
                           По умолчанию 6

    Returns:
        pd.DataFrame: Данные с скорректированной базовой линией

    Note:
        Функция создает копию исходного DataFrame и возвращает скорректированную версию.
        Исходные данные остаются без изменений. Используется библиотека peakutils
        для вычисления базовой линии методом ALS.
    """
    # Создаем копию данных, чтобы не модифицировать исходный DataFrame
    data_corrected = data.copy()
    for col in data_corrected.columns:
        bl = baseline(data_corrected[col], deg)
        data_corrected[col] = data_corrected[col] - bl

    return data_corrected


def l1_regression(x, y, q):
    """
    L1-регрессия (квантильная регрессия) для робустной оценки параметров.

    Выполняет квантильную регрессию для заданного квантиля q, что обеспечивает
    более робустную оценку параметров по сравнению с обычной линейной регрессией,
    особенно в присутствии выбросов.

    Args:
        x (array-like): Независимые переменные (предикторы)
        y (array-like): Зависимая переменная (отклик)
        q (float): Квантиль для регрессии (0 < q < 1).
                  q=0.5 соответствует медианной регрессии

    Returns:
        tuple: (intercept, slope) - оценки параметров

    Note:
        Функция автоматически добавляет константу для оценки свободного члена.
        Использует библиотеку statsmodels для вычислений.
    """
    x = np.array(x).reshape(-1, 1)
    y = np.array(y)

    # Проверка на минимальное количество точек
    if len(x) < 2:
        raise ValueError("Недостаточно данных для регрессии (минимум 2 точки)")

    X = sm.add_constant(x)
    model = QuantReg(y, X)
    result = model.fit(q=q, max_iter=1000)
    params = result.params

    # Убеждаемся, что params содержит именно 2 значения
    if len(params) != 2:
        raise ValueError(f"Ожидалось 2 параметра, получено {len(params)}")

    return params[0], params[1]  # intercept, slope


def deleteCrossTalk(
    data,
    M=None,
    rem_base=False,
    smooth_data=False,
    progress_callback=None,
    iteration_callback=None,
    window_size=21,
    polyorder=3,
    return_matrix=False,
    algorithm="estimate_crosstalk_2",
):
    """
    Основная функция устранения перекрестных помех из данных флуоресценции.

    Выполняет полный цикл обработки флуоресцентных данных секвенирования:
    оценку матрицы перекрестных помех, коррекцию базовой линии (опционально),
    сглаживание (опционально) и устранение перекрестных помех между каналами.

    Args:
        data (pd.DataFrame): Исходные данные флуоресценции с колонками каналов
        M (np.ndarray, optional): Матрица перекрестных помех 4x4. Если None,
                                 будет оценена автоматически. По умолчанию None
        rem_base (bool, optional): Выполнять ли коррекцию базовой линии.
                                 По умолчанию False
        smooth_data (bool, optional): Выполнять ли сглаживание данных.
                                    По умолчанию False
        progress_callback (callable, optional): Функция обратного вызова для отправки прогресса.
                                               Принимает (progress_percent, message)
        iteration_callback (callable, optional): Функция обратного вызова для сохранения данных итерации.
                                                Принимает (iteration_num, iteration_data)
        window_size (int, optional): Размер окна для сглаживания Савицкого-Голея.
                                   Должен быть нечетным числом. По умолчанию 21
        polyorder (int, optional): Порядок полинома для сглаживания Савицкого-Голея.
                                 Должен быть меньше window_size. По умолчанию 3
        return_matrix (bool, optional): Возвращать ли матрицу кросс-помех.
                                       По умолчанию False
        algorithm (str, optional): Алгоритм оценки кросс-помех: "estimate_crosstalk" или "estimate_crosstalk_2".
                                  По умолчанию "estimate_crosstalk_2"

    Returns:
        pd.DataFrame или tuple: Очищенные от перекрестных помех данные с теми же названиями колонок.
                               Если return_matrix=True, возвращает кортеж (data, matrix)

    Note:
        Порядок обработки: коррекция базовой линии -> сглаживание -> устранение перекрестных помех.
        Функция применяет обратную матрицу перекрестных помех для коррекции данных.

    """
    clear_data = None
    # Этап 1: Сглаживание данных
    if smooth_data:
        if progress_callback:
            progress_callback(10, "Сглаживание данных...")
        data = smooth_func(data, window_size=window_size, polyorder=polyorder)

    # Этап 2: Коррекция базовой линии
    if rem_base:
        if progress_callback:
            progress_callback(30, "Коррекция базовой линии...")
        data = baseline_cor(data)

    # Этап 3: Оценка матрицы перекрестных помех
    if M is None:
        if progress_callback:
            progress_callback(50, "Оценка матрицы перекрестных помех...")

        # Выбираем алгоритм в зависимости от параметра
        if algorithm == "estimate_crosstalk":
            M = estimate_crosstalk(
                data,
                progress_callback=progress_callback,
                iteration_callback=iteration_callback,
            )
        else:  # По умолчанию используем estimate_crosstalk_2
            M = estimate_crosstalk_2(
                data,
                progress_callback=progress_callback,
                iteration_callback=iteration_callback,
            )

    # Этап 4: Устранение перекрестных помех
    if progress_callback:
        progress_callback(95, "Устранение перекрестных помех...")
    if clear_data is None:
        clear_data = (np.linalg.inv(M) @ data.T).T
        clear_data.columns = data.columns

    if progress_callback:
        progress_callback(100, "Обработка завершена")

    if return_matrix:
        return clear_data, M
    return clear_data

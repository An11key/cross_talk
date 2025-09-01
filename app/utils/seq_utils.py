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


def estimate_crosstalk(data, bins=300, epsilon=0.05, iter=11, show_fig=False):
    """
    Итеративная оценка матрицы перекрестных помех между каналами флуоресценции.

    Функция использует итеративный алгоритм для оценки матрицы перекрестных помех W,
    где W[i,j] показывает влияние канала j на канал i. Алгоритм основан на анализе
    минимальных значений в интервалах высоких сигналов для каждой пары каналов.

    Args:
        data (pd.DataFrame): Данные флуоресценции с колонками для каждого канала (A, C, G, T)
        bins (int, optional): Количество интервалов для разбиения данных. По умолчанию 300
        epsilon (float, optional): Критерий сходимости - максимальное изменение наклонов.
                                 По умолчанию 0.05
        iter (int, optional): Максимальное количество итераций. По умолчанию 11
        show_fig (bool, optional): Показывать ли графики в процессе итераций.
                                 По умолчанию False

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
    while iteration < iter:

        slopes = []
        W_estim = np.eye(4)

        if show_fig:
            fig, axs = plt.subplots(2, 3)
            makeFig(data, axs, 0, 1)
            plt.show()

        for i in range(4):

            for j in range(4):
                if i is j:
                    continue

                data_x = data[names[i]]

                q1 = data_x.quantile(0.6)
                q2 = data_x.quantile(0.99)

                filt_data = data[(data_x >= q1) & (data_x <= q2)]
                result_data = filt_data[[names[i], names[j]]]
                bins = len(result_data.index) // 8
                intervals = np.array_split(result_data, bins)
                min_rows = []

                for interval in intervals:
                    if not interval.empty:
                        min_index = interval[names[j]].idxmin()
                        min_rows.append(interval.loc[min_index])
                if not min_rows:
                    continue

                min_df = pd.DataFrame(min_rows)
                x = min_df[names[i]]
                y = min_df[names[j]]

                interc, slope = l1_regression(x, y, 0.5)
                W_estim[j, i] = slope
                slopes.append(slope)
        if abs(max(slopes)) < epsilon:
            break
        data = (np.linalg.inv(W_estim) @ data.T).T

        data.columns = names
        iteration += 1
        W = W @ W_estim
    W = W / W.sum(axis=0)
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
        Функция модифицирует исходный DataFrame. Используется библиотека peakutils
        для вычисления базовой линии методом ALS.
    """
    for col in data.columns:
        bl = baseline(data[col], deg)
        data[col] = data[col] - bl

    return data


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
        array: Оценки параметров [intercept, slope]

    Note:
        Функция автоматически добавляет константу для оценки свободного члена.
        Использует библиотеку statsmodels для вычислений.
    """
    x = np.array(x).reshape(-1, 1)
    y = np.array(y)
    X = sm.add_constant(x)
    model = QuantReg(y, X)
    result = model.fit(q=q)
    return result.params


def deleteCrossTalk(data, M=None, rem_base=True, smooth_data=True):
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

    Returns:
        pd.DataFrame: Очищенные от перекрестных помех данные с теми же названиями колонок

    Note:
        Порядок обработки: коррекция базовой линии -> сглаживание -> устранение перекрестных помех.
        Функция применяет обратную матрицу перекрестных помех для коррекции данных.

    Example:
        >>> clean_data = deleteCrossTalk(raw_data, rem_base=True, smooth_data=True)
        >>> # Полная обработка с коррекцией базовой линии и сглаживанием
    """

    if smooth_data:
        data = smooth_func(data, window_size=21)
    if rem_base:
        data = baseline_cor(data)
    if M is None:
        M = estimate_crosstalk(data)

    names = data.columns
    data = (np.linalg.inv(M) @ data.T).T
    data.columns = names
    return data

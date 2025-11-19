import warnings
import numpy as np
from scipy.signal import savgol_filter

warnings.filterwarnings("ignore")

rng = np.random.default_rng()


def makePlot(axs, df, name1, name2, q1=0, q2=1):
    axs.scatter(df.iloc[q1:q2][name1], df.iloc[q1:q2][name2], s=10, alpha=0.2)
    axs.set_xlabel(name1)
    axs.set_ylabel(name2)


def makeFig(data, axs, qu1=0.6, qu2=0.99):
    count = 0
    n = len(data)
    q1 = int(qu1 * n)
    q2 = int(qu2 * n)
    names = data.columns
    for i in range(len(names)):
        for j in range(i, len(names)):
            if i is j:
                continue
            if count < 3:
                makePlot(axs[0, count], data, names[i], names[j], q1, q2)
            else:
                makePlot(axs[1, count - 3], data, names[i], names[j], q1, q2)
            count += 1


def smooth_func(data, window_size=15, polyorder=3):
    smoothed_data = data.copy()
    for column in data.columns:
        smoothed_data[column] = savgol_filter(data[column], window_size, polyorder)
    return smoothed_data


def get_matrix_difference(matrix1, matrix2):
    if matrix1 is None or matrix2 is None:
        return None
    a = matrix1
    b = matrix2
    diff = np.abs(a - b).mean()
    return diff

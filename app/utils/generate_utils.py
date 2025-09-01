import numpy as np
import pandas as pd

rng = np.random.default_rng()


def getTestData(
    n=1000,
    peak_space=10,
    peak_width=1.3,
    peak_height=1000,
    detail=3,
    noise_level=0.007,
    peak_rand=0.5,
):

    names = ["A", "G", "C", "T"]
    seq = rng.choice(names, n)
    time_axis = np.arange(0, (peak_space * n * detail))
    data = pd.DataFrame(np.zeros((len(time_axis), len(names))))
    data.columns = names

    for i, base in enumerate(seq):
        A = rng.uniform(peak_height * (1 - peak_rand), peak_height * (1 + peak_rand))
        position = i * peak_space * detail + rng.integers(detail)
        peak = getPeak(time_axis, position, peak_width * detail, A)
        data[base] += peak

    M = getCrossTalk()
    data = (M @ data.T).T
    data.columns = names

    for base in data:
        data[base] += rng.normal(0, peak_height * noise_level, len(time_axis))

    return data, M


def applyCrossTalk(data, M, width):
    data = data.T
    mult = 0.2
    for i in range(0, len(data.columns), width):
        rand_dev = rng.uniform(1 - mult, 1 + mult, (4, 4))
        np.fill_diagonal(rand_dev, 1)
        for j in range(width):
            data[i + j] = ((M * rand_dev) @ data[i + j].T).T
    return data.T


def getPeak(t, t_k, width, A):
    return A * np.exp((-1) * (t - t_k) ** 2 / (2 * width**2))


def getCrossTalk():
    M = np.empty((4, 4))
    for i in range(4):
        col = getCrossTalkColumn()
        M[i] = col[3 - i : 7 - i]
    return M.T


def getCrossTalkColumn():
    ls = [1]
    for i in range(3):
        cur_min = min(ls[0], ls[-1])
        ls.append(rng.uniform(0, cur_min))
        ls.insert(0, rng.uniform(0, cur_min))
    return ls

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from utils import getTestData, getCrossTalk, estimate_crosstalk, deleteCrossTalk, baseline_cor, getCrossTalkColumn

def make_process(data):
    showData(data, 0.5, 0.7)

    W = estimate_crosstalk(data)
    clear_data = deleteCrossTalk(data, W)
    print("Итоговая матрица\n", W)
    showData(clear_data, 0.5, 0.7)


def showData(data, b1, b2):
    data.plot()
    n = len(data.index)
    plt.xlim(n*b1, n*b2)
    plt.show()


true_data = pd.read_csv("data/2_pGEM_G2_PDMA6_36.csv",
                   sep=';',
                   usecols=[0,1,2,3],
                   header=None,
                   names=['A','G','T','C'])
true_M = pd.read_csv("data/2_pGEM_G2_PDMA6_36.matrix",
                   sep=';',
                   usecols=[0,1,2,3],
                   header=None,
                   names=['A','G','T','C'])
true_M.index = true_M.columns


data, M = getTestData(1000, 5, 1.3, 1000, 2)

W = estimate_crosstalk(data)

make_process(data)

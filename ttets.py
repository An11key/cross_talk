import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from utils import getTestData, getCrossTalk, estimate_crosstalk, deleteCrossTalk, baseline_cor, getCrossTalkColumn

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
n = len(data.index)
print(M)

data.plot()
plt.show()

W = estimate_crosstalk(data)

test_data = deleteCrossTalk(data, W)
clear_data = deleteCrossTalk(data, M)
true_data = deleteCrossTalk(true_data, W)

print("Итоговая матрица\n", W)
test_data.plot()
plt.xlim(int(n*0.5), int(n*0.7))
plt.show()
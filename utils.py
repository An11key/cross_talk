import warnings
import statsmodels.api as sm
from statsmodels.regression.quantile_regression import QuantReg
import pandas as pd
import numpy as np
from scipy.signal import medfilt
import matplotlib.pyplot as plt
from peakutils import baseline
warnings.filterwarnings("ignore")

rng = np.random.default_rng()

def load_data_from_csv(file_path):
    """
    Загрузка данных из CSV-файла.
    
    Параметры:
    - file_path: Путь к CSV-файлу.
    
    Возвращает:
    - I: Массив измеренных интенсивностей флуоресценции (4 x N).
    """
    data = pd.read_csv(file_path,
                   sep=';',
                   header=None,
                   usecols=[0, 1, 2, 3],
                   names=['A', 'G', 'C', 'T'],
                   encoding='utf-8-sig')
    
    
    return data


def estimate_crosstalk(data, bins=300, epsilon=0.05, iter=11):
    W = np.eye(4)
    data = data
    names = data.columns
    iteration = 1
    while iteration < iter:

        slopes = []
        W_estim = np.eye(4)

        fig, axs = plt.subplots(2,3)
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
                bins = len(result_data.index)//8
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

                
                interc, slope = l1_regression(x,y,0.5)
                W_estim[j,i] = slope
                slopes.append(slope)
        if abs(max(slopes)) < epsilon:
            break
        data = (np.linalg.inv(W_estim) @ data.T).T

        data.columns = names
        iteration+=1
        W = W @ W_estim
    W = W / W.sum(axis=0)
    return W

def draw_line(intercept, slope, min, max):
    x = np.linspace(min, max, 500)
    y = slope * x + intercept
    plt.plot(x,y)


def baseline_cor(data, deg=6):

    for col in data.columns:
        bl = baseline(data[col], deg)
        data[col] = data[col]-bl
    
    return data


def l1_regression(x, y, q):
    x = np.array(x).reshape(-1, 1)  
    y = np.array(y)
    X = sm.add_constant(x)
    model = QuantReg(y, X)
    result = model.fit(q=q)
    return result.params


def makePlot(axs, df, name1, name2, q1=0, q2=1):
    axs.scatter(df.iloc[q1: q2][name1],df.iloc[q1: q2][name2], s=10, alpha=0.2)
    axs.set_xlabel(name1)
    axs.set_ylabel(name2)

def makeFig(data, axs, qu1=0.6, qu2=0.99):
    count = 0
    n = len(data)
    q1 = int(qu1*n)
    q2 = int(qu2*n)
    names = data.columns
    for i in range(len(names)):
        for j in range(i,len(names)):
            if i is j:
                continue
            if count < 3:
                makePlot(axs[0,count], data, names[i], names[j], q1, q2)
            else:
                makePlot(axs[1,count-3], data, names[i], names[j], q1, q2)
            count+=1


def getTestData(n, peak_space, peak_width, peak_height, detail):
    noise_level = 0.001
    peak_rand = 0.5

    names = ['A','G','C','T']
    seq = rng.choice(names, n)
    time_axis = np.arange(0, (peak_space * n * detail))
    data = pd.DataFrame(np.zeros((len(time_axis), len(names))))
    data.columns = names

    for i,base in enumerate(seq):
        A = rng.uniform(peak_height * (1-peak_rand), peak_height * (1+peak_rand))
        position = i * peak_space * detail + rng.integers(detail)
        peak = getPeak(time_axis, position, peak_width * detail, A)
        data[base] += peak

    for base in data:
        data[base]+=rng.normal(0, peak_height * noise_level, len(time_axis))

    M = getCrossTalk()
    # data = applyCrossTalk(data, M, peak_space*detail)
    data = (M @ data.T).T
    data.columns = names

    return data, M

def applyCrossTalk(data, M, width):
    data = data.T
    mult = 0.2
    for i in range(0,len(data.columns),width):
        rand_dev = rng.uniform(1 - mult, 1 + mult, (4,4))
        np.fill_diagonal(rand_dev, 1)
        for j in range(width):
            data[i+j] = ((M * rand_dev) @ data[i+j].T).T
    return data.T

def getPeak(t, t_k, width, A):
    return A * np.exp((-1)*(t-t_k)**2/(2*width**2))

def getCrossTalk():
    M = np.empty((4,4))
    for i in range(4):
        col = getCrossTalkColumn()
        M[i] = col[3-i:7-i]
    return M.T

def getCrossTalkColumn():
    ls = [1]
    for i in range(3):
        cur_min = min(ls[0], ls[-1])
        ls.append(rng.uniform(0, cur_min))
        ls.insert(0, rng.uniform(0, cur_min))
    return ls

def deleteCrossTalk(data, M, rem_base = False):

    if rem_base:
        data = baseline_cor(data)

    names = data.columns
    data = (np.linalg.inv(M) @ data.T).T
    data.columns = names
    return data
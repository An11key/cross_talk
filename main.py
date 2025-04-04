import statsmodels.api as sm
from statsmodels.regression.quantile_regression import QuantReg
import statsmodels.formula.api as smf
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import warnings
from scipy.signal import medfilt
import matplotlib.pyplot as plt
from utils import load_data_from_csv, estimate_crosstalk





# Пример использования
if __name__ == "__main__":

    data = load_data_from_csv('data/2_pGEM_G2_PDMA6_36.csv')
    # data = baseline_cor(data)
    estimated_W = estimate_crosstalk(data)
    print("Оцененная матрица перекрестных помех:")
    print(estimated_W)
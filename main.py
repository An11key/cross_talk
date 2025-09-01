from app.utils.load_utils import load_data_from_csv
from app import estimate_crosstalk

# Пример использования
if __name__ == "__main__":

    data = load_data_from_csv("data/2_pGEM_G2_PDMA6_36.csv")
    # data = baseline_cor(data)
    estimated_W = estimate_crosstalk(data)
    print("Оцененная матрица перекрестных помех:")
    print(estimated_W)

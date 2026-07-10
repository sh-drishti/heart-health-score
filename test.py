import pandas as pd

df = pd.read_csv("data/cardio_hhs.csv", keep_default_na=False)

print(df.dtypes)
print(df["Resting_Heart_Rate"].unique())
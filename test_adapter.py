import pandas as pd

from adapter import calculate_hhs

df = pd.read_csv("data/cardio_hhs.csv")

patient = df.iloc[0]

result = calculate_hhs(patient)

print(result["hhs"])
print(result["category"])
print(result["data_confidence"])
print(result["burden"])
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from scipy.cluster.hierarchy import linkage
from scipy.spatial.distance import squareform
from scipy.cluster.hierarchy import dendrogram
# from scipy.cluster.hierarchy import fcluster

def normalize_name(name):
    return (
        str(name)
        .lower()
        .replace("_", "")
        .replace(" ", "")
        .replace("-", "")
        .replace("/", "")
        .replace("(", "")
        .replace(")", "")
    )

def get_severity_score(feature, value, sex):

    matching_rows = thresholds[
        thresholds["Features"].apply(normalize_name)
        == normalize_name(feature)
    ]

    sex_rows = matching_rows[
        matching_rows["Sex"] == sex
    ]

    if len(sex_rows) > 0:
        row = sex_rows.iloc[0]
    else:
        row = matching_rows[
            matching_rows["Sex"] == "Both"
        ].iloc[0]

    reverse_features = [
        "HDL",
        "eGFR",
        "Physical Activity",
        "Dietary Quality"
    ]

    if normalize_name(feature) in [
        normalize_name(f) for f in reverse_features
    ]:

        if value >= row["Normal_Min"]:
            return 0
        elif row["Borderline_Min"] <= value <= row["Borderline_Max"]:
            return 1
        else:
            return 2

    elif normalize_name(feature) == normalize_name("Sleep Duration"):

        if 7 <= value <= 9:
            return 0
        elif (6 <= value < 7) or (9 < value <= 10):
            return 1
        else:
            return 2

    else:

        if row["Normal_Min"] <= value <= row["Normal_Max"]:
            return 0

        elif row["Borderline_Min"] <= value <= row["Borderline_Max"]:
            return 1

        else:
            return 2

df=pd.read_csv("cardio_synthetic_50pts_v2.csv", index_col='Patient_ID')

df["Sex_For_Thresholds"] = df["Biological_Sex"]

thresholds=pd.read_excel("feature_mapping.xlsx")

thresholds.columns = thresholds.columns.str.strip()
thresholds["Features"] = thresholds["Features"].astype(str).str.strip()
thresholds["Sex"] = thresholds["Sex"].astype(str).str.strip()
df.drop(columns=["Archetype","Pulse_Pressure","TC_HDL_Ratio"], inplace=True)
# Biological Sex
df["Biological_Sex"] = df["Biological_Sex"].map({
    "F": 0,
    "M": 1
})

# Diabetes Status
df["Diabetes_Status"] = df["Diabetes_Status"].map({
    "No": 0,
    "Prediabetes": 1,
    "Yes": 2
})

# Smoking Status
df["Smoking_Status"] = df["Smoking_Status"].map({
    "Never": 0,
    "Former": 1,
    "Current": 2
})

# Alcohol
df["Alcohol"] = df["Alcohol"].map({
    "None": 0,
    "Moderate": 1,
    "Heavy": 2
})

# Family History
df["Family_History_CVD"] = df["Family_History_CVD"].map({
    "No": 0,
    "Yes": 1
})

# Atrial Fibrillation
df["Atrial_Fibrillation"] = df["Atrial_Fibrillation"].map({
    "No": 0,
    "Yes": 1
})

# ECG Abnormalities
df["ECG_Abnormalities"] = df["ECG_Abnormalities"].map({
    "Normal": 0,
    "Abnormal": 1
})

# Prior ASCVD
df["Prior_ASCVD"] = df["Prior_ASCVD"].map({
    "No": 0,
    "Yes": 1
})
df_column_map = {
    normalize_name(col): col
    for col in df.columns
}
# print(df.head())
numeric_df = df.select_dtypes(include=np.number)

matrix = numeric_df.corr()
#print(matrix)
corr_matrix = matrix.abs()

upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))

strong_corr = (upper.stack().sort_values(ascending=False))
# print("\nStrong Correlations (>0.5):\n")
# print(strong_corr[strong_corr > 0.5])
plt.figure(figsize=(22,18))
sns.heatmap(matrix,annot=True,cmap="coolwarm", fmt=".2f",linewidths=0.5)
plt.title("Heatmap")
plt.show()

# print("\nSeverity Scores for Patient 1\n")
# print("-" * 80)

patient_id = 1

for feature in thresholds["Features"].unique():

    normalized_feature = normalize_name(feature)

    if normalized_feature not in df_column_map:
        print(f"{feature:<35} NOT FOUND")
        continue

    actual_column = df_column_map[normalized_feature]

    value = df.loc[patient_id, actual_column]

    sex = df.loc[patient_id, "Sex_For_Thresholds"]

    severity = get_severity_score(
        feature,
        value,
        sex
    )

    severity_label = {
        0: "NORMAL",
        1: "BORDERLINE",
        2: "RISK"
    }[severity]

    # print(
    #     f"{feature:<35}"
    #     f"Value: {round(float(value),2):<10}"
    #     f"Score: {severity} "
    #     f"({severity_label})"
    # )
    
dist_matrix=1-abs(corr_matrix)
print(dist_matrix)
condensed_dist=squareform(dist_matrix)
z=linkage(condensed_dist,method="average")
print(z.shape)
print(z[:10])

plt.figure(figsize=(18,10))

dendrogram(
    z,
    labels=numeric_df.columns,
    leaf_rotation=90,
    leaf_font_size=10
)

# clusters=fcluster(z,t=10,criterion="inconsistent")
# cluster_dict = {}

# for feature, cluster in zip(matrix.columns, clusters):

#     if cluster not in cluster_dict:
#         cluster_dict[cluster] = []

#     cluster_dict[cluster].append(feature)
    
# print("\nFEATURE CLUSTERS")
# print("="*60)

# for cluster in sorted(cluster_dict.keys()):

#     print(f"\nCluster {cluster}")
#     print("-"*25)

#     for feature in cluster_dict[cluster]:
#         print(feature)
        
plt.title("Hierarchical Feature Clustering Dendrogram")
plt.xlabel("Features")
plt.ylabel("Distance (1 - |Correlation|)")
plt.tight_layout()
plt.show()
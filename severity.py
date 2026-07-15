import pandas as pd
from mapping import HHS_FIELD_METADATA, FIELD_MAPPING

thresholds = pd.read_excel("data/feature_mapping_hhs.xlsx")

def get_feature_metadata(feature, sex="Both"):
    """
    Returns the threshold row for the given feature.
    Handles sex-specific thresholds automatically.
    """

    rows = thresholds[thresholds["Feature"] == feature]

    if rows.empty:
        print(f"Feature not found : {feature}")
        return None

    # Try exact sex match first
    if sex in rows["Sex"].values:
        return rows[rows["Sex"] == sex]

    # Otherwise use "Both"
    if "Both" in rows["Sex"].values:
        return rows[rows["Sex"] == "Both"]

    return rows

def calculate_numeric_severity(value, row):
    
    if row["Normal_Min"] <= value <= row["Normal_Max"]:
        return 0

    elif row["Borderline_Min"] <= value <= row["Borderline_Max"]:
        return 0.5

    elif row["Risk_Min"] <= value <= row["Risk_Max"]:
        return 1

    return None


def calculate_categorical_severity(value, row):

    mapping = str(row["Category_Mapping"])

    severity_lookup = {
        "Normal": 0,
        "Borderline": 0.5,
        "Risk": 1
    }

    category_dict = {}

    mappings = mapping.split(";")

    for item in mappings:

        if "=" not in item:
            continue

        key, val = item.split("=")

        category_dict[key.strip()] = val.strip()

    if value not in category_dict:
        return None

    return severity_lookup[category_dict[value]]

def get_severity(feature, value, sex):

    row = get_feature_metadata(feature, sex)

    if row is None:
        return None

    for _, r in row.iterrows():
        if r["Direction"] == "CATEGORICAL":
            severity = calculate_categorical_severity(value, r)

        else:
            severity = calculate_numeric_severity(value, r)

        if severity is not None:
            return severity

    return None

def calculate_patient_severity(patient):

    patient_data = {}

    sex = patient["Biological_Sex"]

    ignore = [
        "Patient_ID",
        "Age",
        "Biological_Sex"
    ]

    for feature in patient.index:

        if feature in ignore:
            continue

        
        severity = get_severity(feature, patient[feature], sex)
        hhs_key=FIELD_MAPPING.get(feature)
        unit=""
        if hhs_key in HHS_FIELD_METADATA:
            unit = HHS_FIELD_METADATA[hhs_key]["unit"]

        patient_data[feature] = {
            "value": patient[feature],
            "severity": severity,
            "excel_name": feature.replace("_", " "),
            "unit": unit
        }

    return patient_data
import pandas as pd


# ==========================================
# Load Threshold Mapping
# ==========================================

thresholds = pd.read_excel("data/feature_mapping_hhs.xlsx")


# ==========================================
# Helper Functions
# ==========================================

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
        return rows[rows["Sex"] == sex].iloc[0]

    # Otherwise use "Both"
    if "Both" in rows["Sex"].values:
        return rows[rows["Sex"] == "Both"].iloc[0]

    return rows.iloc[0]


# ==========================================
# Numeric Severity
# ==========================================

def calculate_numeric_severity(value, row):

    if row["Normal_Min"] <= value <= row["Normal_Max"]:
        return 0

    elif row["Borderline_Min"] <= value <= row["Borderline_Max"]:
        return 1

    elif row["Risk_Min"] <= value <= row["Risk_Max"]:
        return 2

    return None


# ==========================================
# Categorical Severity
# ==========================================

def calculate_categorical_severity(value, row):

    mapping = str(row["Category_Mapping"])

    severity_lookup = {
        "Normal": 0,
        "Borderline": 1,
        "Risk": 2
    }

    category_dict = {}

    mappings = mapping.split(";")

    for item in mappings:

        if "=" not in item:
            continue

        key, val = item.split("=")

        category_dict[key.strip()] = val.strip()

    if value not in category_dict:
        print(f"Unknown category '{value}'")
        return None

    return severity_lookup[category_dict[value]]


# ==========================================
# Master Severity Function
# ==========================================

def get_severity(feature, value, sex):

    row = get_feature_metadata(feature, sex)

    if row is None:
        return None

    # Category mapping exists
    if row["Direction"] == "CATEGORICAL":

        return calculate_categorical_severity(
            value,
            row
        )

    # Numeric parameter
    return calculate_numeric_severity(
        value,
        row
    )


# ==========================================
# Patient Severity
# ==========================================

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

        severity = get_severity(
            feature,
            patient[feature],
            sex
        )

        patient_data[feature] = {

            "value": patient[feature],

            "severity": severity,

            "excel_name": feature.replace("_", " ")

        }

    return patient_data
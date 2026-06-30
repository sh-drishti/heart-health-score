import pandas as pd

thresholds = pd.read_excel("feature_mapping.xlsx")


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


threshold_map = {
    normalize_name(feature): feature
    for feature in thresholds["Features"]
}


reverse_features = [
    "eGFR",
    "Physical Activity",
    "Dietary Quality",
    "HDL_M",
    "HDL_F"
]



def get_severity_score(feature, value, sex):

    if feature in ["HDL", "Waist Circumference", "Waist-Hip Ratio"]:

        sex_label = "M" if sex == 1 else "F"

        row = thresholds[
            (thresholds["Features"] == feature) &
            (thresholds["Sex"] == sex_label)
        ].iloc[0]

    else:

        row = thresholds[
            thresholds["Features"] == feature
        ].iloc[0]

    reverse_features = [
        "eGFR",
        "Physical Activity",
        "Dietary Quality",
        "HDL"
    ]

    if feature in reverse_features:

        if value >= row["Normal_Min"]:
            return 0

        elif row["Borderline_Min"] <= value <= row["Borderline_Max"]:
            return 1

        else:
            return 2

    elif feature == "Sleep Duration":

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
        
def calculate_patient_severity(patient):

    patient_data = {}

    sex = patient["Biological_Sex"]

    patient_column_map = {
        normalize_name(col): col
        for col in patient.index
    }

    for normalized_feature, excel_feature in threshold_map.items():

        if normalized_feature not in patient_column_map:
            continue

        csv_column = patient_column_map[normalized_feature]

        value = patient[csv_column]

        severity = get_severity_score(
            excel_feature,
            value,
            sex
        )

        patient_data[csv_column] = {

            "excel_name": excel_feature,

            "value": value,

            "severity": severity

        }

    return patient_data
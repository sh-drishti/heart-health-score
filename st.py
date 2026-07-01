import pandas as pd

from severity import calculate_patient_severity

# Load dataset
df = pd.read_csv(
    "data/cardio_hhs.csv",
    keep_default_na=False
)

severity_map = {
    0: "Normal",
    1: "Borderline",
    2: "Risk"
}

print("=" * 70)
print("CHECKING ALL PATIENTS")
print("=" * 70)

errors_found = False

for _, patient in df.iterrows():

    patient_data = calculate_patient_severity(patient)

    for feature, info in patient_data.items():

        if info["severity"] is None:

            errors_found = True

            print(
                f"Patient : {patient['Patient_ID']}"
            )

            print(
                f"Feature : {feature}"
            )

            print(
                f"Value   : {info['value']}"
            )

            print("-" * 50)

if not errors_found:

    print("✓ All patients classified successfully.")

print("\nAlcohol values present in dataset:")
print(df["Alcohol"].unique())
from mapping import FIELD_MAPPING, HHS_FIELD_METADATA
from hhs_v1_2_ui_app import FieldRecord, HHSManualScorer


def create_hhs_input(patient):
    """
    Converts one patient row from the CSV into the
    format expected by HHSManualScorer.
    """

    fields = {}

    for csv_name, hhs_key in FIELD_MAPPING.items():

        if hhs_key not in ["patient_id", "age", "biological_sex"]:
            continue
        if csv_name not in patient.index:
            continue

        meta = HHS_FIELD_METADATA[hhs_key]

        value = patient[csv_name]

        # Handle missing values
        if value is None:
            status = "Missing"
        else:
            try:
                import pandas as pd
                status = "Missing" if pd.isna(value) else "Available"
            except:
                status = "Available"

        fields[hhs_key] = FieldRecord(

            domain=meta["domain"],

            label=meta["label"],

            value=value,

            unit=meta["unit"],

            status=status,

            months_old=0

        )

    return {

        "fields": fields,

        "age": int(patient["Age"]),

        "sex": str(patient["Biological_Sex"]),

        # Change later if your dataset stores nmol/L
        "lpa_unit": "mg/dL"

    }


def calculate_hhs(patient):
    """
    Runs the official HHS engine for one patient.
    """

    hhs_input = create_hhs_input(patient)

    scorer = HHSManualScorer(

        hhs_input["fields"],

        hhs_input["age"],

        hhs_input["sex"],

        hhs_input["lpa_unit"]

    )

    return scorer.calculate()
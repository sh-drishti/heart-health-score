from mapping import HHS_FIELD_METADATA
import pandas as pd
from hhs_v1_2_ui_app import FieldRecord, HHSManualScorer


def create_hhs_input(patient):
    """
    Converts one patient row from the CSV into the
    format expected by HHSManualScorer.
    """

    fields = {}

    for hhs_key,meta in HHS_FIELD_METADATA.items():

        if hhs_key in ["patient_id", "age", "biological_sex"]:
            continue
        if hhs_key not in patient.index:
            continue

        value = patient[hhs_key]

        status = "Missing" if pd.isna(value) else "Available"

        months_col = f"{hhs_key}_months_old"
        if months_col in patient.index:
            months_old = patient[months_col]
        else:
            months_old = 0

        fields[hhs_key] = FieldRecord(
            domain=meta["domain"],
            label=meta["label"],
            value=value,
            unit=meta["unit"],
            status=status,
            months_old=months_old
        )

    return {

        "fields": fields,

        "age": int(patient["age"]),

        "sex": str(patient["biological_sex"]),

        # Change later if your dataset stores nmol/L
        "lpa_unit": "mg/dL"

    }


def calculate_hhs(patient):
    """
    Runs the official HHS engine for one patient.
    """

    hhs_input = create_hhs_input(patient)

    print(sorted(hhs_input["fields"].keys()))
    print(f"Number of fields passed: {len(hhs_input['fields'])}")
    scorer = HHSManualScorer(

        hhs_input["fields"],

        hhs_input["age"],

        hhs_input["sex"],

        hhs_input["lpa_unit"]

    )

    return scorer.calculate()
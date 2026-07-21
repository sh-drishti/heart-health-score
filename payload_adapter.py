from mapping import HHS_FIELD_METADATA
import pandas as pd
import json
# Reverse mapping: Official Label -> HHS Key
LABEL_TO_KEY = {
    meta["label"]: key
    for key, meta in HHS_FIELD_METADATA.items()
}

def payload_to_patient(payload):
    """
    Converts a senior HHS payload into the same patient
    dictionary structure currently used by the dashboard.
    """

    patient = {}

    visit = payload["visit"]

    patient["patient_id"] = visit["patient_id"]
    patient["age"] = visit["age"]
    patient["biological_sex"] = visit["biological_sex"]

    for feed in payload["input_feeds"]:

        label = feed["label"]
        if label not in LABEL_TO_KEY:
            continue

        key = LABEL_TO_KEY[label]

        patient[key] = feed["value"]

        if feed["months_old"] is not None:
            patient[f"{key}_months_old"] = feed["months_old"]

        patient[f"{key}_status"] = feed["status"]

    return {
        "patient": patient,
        "assessment": payload["assessment"],
        "visit": payload["visit"],
        "clinician_note": payload.get("clinician_note")
    }

with open("data/hhs_encounter_payload.json", "r") as f:
    payload = json.load(f)
patient=payload_to_patient(payload)
for k, v in patient.items():
    print(f"{k}: {v}")
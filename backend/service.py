"""
Dashboard data service.

Reuses the existing Python engine untouched:
- adapter.calculate_hhs            -> official HHS assessment (CSV source)
- severity.calculate_patient_severity -> per-parameter severities
- database.EncounterRepository     -> MongoDB payloads (payload source)
"""

import math

import numpy as np
import pandas as pd

from adapter import calculate_hhs
from severity import calculate_patient_severity
from database import EncounterRepository
from backend.payload_convert import payload_to_patient

CSV_PATH = "data/cardio_hhs_2.csv"


def to_json_safe(obj):
    """Recursively convert pandas/numpy values to JSON-safe Python values."""

    if isinstance(obj, dict):
        return {str(k): to_json_safe(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple)):
        return [to_json_safe(v) for v in obj]

    if isinstance(obj, pd.Series):
        return to_json_safe(obj.to_dict())

    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None

    if isinstance(obj, (np.floating, np.integer)):
        return obj.item()

    if isinstance(obj, np.bool_):
        return bool(obj)

    if obj is pd.NA or obj is pd.NaT:
        return None

    try:
        if pd.isna(obj):
            return None
    except (TypeError, ValueError):
        pass

    return obj


def _load_df() -> pd.DataFrame:
    return pd.read_csv(CSV_PATH)


def get_patient_ids(source: str = "csv") -> list:
    if source == "csv":
        return _load_df()["Patient_ID"].tolist()

    repo = EncounterRepository()
    return repo.get_all_patients()


def get_dashboard(patient_id: str, source: str = "csv") -> dict | None:
    """Full dashboard bundle for one patient. None if not found."""

    if source == "csv":
        df = _load_df()
        rows = df[df["Patient_ID"] == patient_id]
        if rows.empty:
            return None

        patient = rows.iloc[0]
        assessment = calculate_hhs(patient)
        extra = {}

    else:
        repo = EncounterRepository()
        payload = repo.get_payload(patient_id)
        if payload is None:
            return None

        converted = payload_to_patient(payload)
        patient = pd.Series(converted["patient"])
        assessment = converted["assessment"]
        extra = {
            "visit": converted["visit"],
            "clinician_note": converted["clinician_note"],
        }

    patient_data = calculate_patient_severity(patient)

    return to_json_safe({
        "patient": patient,
        "patient_data": patient_data,
        "assessment": assessment,
        **extra,
    })


# In-memory validation store, keyed by patient_id.
_validations: dict = {}


def save_validation(validation: dict) -> dict:
    _validations[validation["patient_id"]] = validation
    return validation


def get_validation(patient_id: str) -> dict | None:
    return _validations.get(patient_id)

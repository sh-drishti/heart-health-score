"""Per-parameter severity for the dashboard badges, taken from the HHS engine.

Why this module exists
----------------------
`severity.py` at the repo root predates the v1.2 engine by six days and
implements the same clinical thresholds a second time, reading them from
`data/feature_mapping_hhs_2.xlsx`. Two defects follow from how it bands values:

* Its bands share endpoints (``Borderline_Max == Risk_Min``) and are tested
  Normal -> Borderline -> Risk with ``<=`` at both ends, so a value sitting
  exactly on a risk threshold matches Borderline first and never reaches Risk.
  HbA1c 6.5, fasting glucose 126, SBP 140, DBP 90 and LDL 160 all read as
  "Moderate" -- 23 of 24 HIGH_BAD features are affected.
* The bands are closed at both ends and the function falls through to
  ``return None``, so anything past the outer bound renders as "N/A".
  SBP 300 and HbA1c 18 disappear rather than reading as High.

The engine's ``sev_*`` functions have neither problem: ``piecewise`` is
open-ended and tests ``value >= threshold``, so the boundary belongs to the
higher band and extremes clamp to 1.0.

These are the engine's *raw* clinical severities. Deliberately not
``HHSManualScorer._severity()``, which blends in measurement staleness as
``c * raw + (1 - c) * prior``. That blend is correct for scoring -- a
twelve-month-old LDL should not count in full -- but wrong for a badge whose
whole claim is to describe the measurement in front of the reader.

Output shape is identical to ``severity.calculate_patient_severity`` so the
frontend needs no change; ``getLevel()`` already consumes a 0-1 severity.
"""

from typing import Any, Dict, Optional

from mapping import HHS_FIELD_METADATA
from hhs_v1_2_ui_app import (
    piecewise,
    sev_activity,
    sev_alcohol_audit,
    sev_apob,
    sev_bmi_indian,
    sev_cac,
    sev_ckd,
    sev_dbp,
    sev_diabetes,
    sev_diet_score,
    sev_egfr,
    sev_family_history,
    sev_fasting_glucose,
    sev_hba1c,
    sev_hscrp,
    sev_ldl,
    sev_lpa,
    sev_non_hdl,
    sev_pack_years,
    sev_prs,
    sev_sbp,
    sev_sleep_hours,
    sev_smoking_status,
    sev_stress,
    sev_tc_hdl_ratio,
    sev_triglycerides,
    sev_uacr,
    sev_waist,
    sev_whr,
    sev_yes_no,
)

# "Unknown" has to stay N/A. The engine's sev_yes_no("Unknown") returns 0.0
# because bool_yes only recognises affirmatives, which would paint every
# unanswered yes/no question with a green "Low" badge. Note that "None" is NOT
# in this set: it is a real answer for family_history, meaning no affected
# relatives.
_UNKNOWN = {"unknown", ""}

# The engine scores treatment as a domain-level prior (see
# HHSManualScorer._prior_treatment), not as a per-field severity, so there is no
# sev_* function to borrow. Being on treatment is a managed risk factor rather
# than a high-risk finding, so this keeps the 0.5 the spreadsheet assigned it
# and the behaviour the dashboard already had.
def _sev_treatment(value: Any) -> float:
    return 0.5 if str(value).strip().lower() in {"yes", "true", "1"} else 0.0


# The engine has no sev_hdl -- HDL reaches the score only through non_hdl and
# tc_hdl_ratio. The spreadsheet does have an hdl row, but its bands are encoded
# ascending while every other HIGH_GOOD feature runs descending, so it currently
# scores HDL 25 as "Normal" and HDL 70 as "At risk", exactly backwards. Its own
# Source_Guideline cell reads "NCEP ATP III (higher = healthier)", contradicting
# its numbers.
#
# These are the spreadsheet's own cut-points with the direction corrected. Needs
# the data scientist's sign-off before it is treated as authoritative.
def _sev_hdl(value: Any, sex: str) -> float:
    v = float(value)
    low = 50.0 if str(sex).strip().lower().startswith("f") else 40.0
    if v >= 60.0:
        return 0.0
    if v >= low:
        return 0.35
    if v >= low - 10.0:
        return 0.70
    return 1.0


# The engine does not score these two at all: resting HR is not modelled, and
# years_since_quit is consumed as *input* to sev_smoking_status's decay rather
# than scored on its own. Both appear in the dashboard's domain lists and both
# carried a severity before this change, so dropping them would be a visible
# regression. These follow the spreadsheet's cut-points and, like _sev_hdl,
# want the data scientist's sign-off.
def _sev_resting_hr(value: Any) -> float:
    v = float(value)
    if v < 50.0:  # bradycardia, flagged but not equated with tachycardia
        return 0.5
    return piecewise(v, [(0, 0.00), (85, 0.35), (100, 0.70), (120, 1.00)])


def _sev_years_since_quit(value: Any) -> float:
    v = float(value)
    if v >= 15.0:
        return 0.0
    if v >= 5.0:
        return 0.35
    return 0.7


# Feature -> severity function, mirroring HHSManualScorer.domain_severities.
_SIMPLE = {
    "sbp": sev_sbp,
    "resting_hr": _sev_resting_hr,
    "years_since_quit": _sev_years_since_quit,
    "dbp": sev_dbp,
    "lvh": sev_yes_no,
    "ldl": sev_ldl,
    "non_hdl": sev_non_hdl,
    "tc_hdl_ratio": sev_tc_hdl_ratio,
    "apob": sev_apob,
    "triglycerides": sev_triglycerides,
    "hba1c": sev_hba1c,
    "fasting_glucose": sev_fasting_glucose,
    "diabetes": sev_diabetes,
    "uacr": sev_uacr,
    "ckd": sev_ckd,
    "bmi": sev_bmi_indian,
    "pack_years": sev_pack_years,
    "smokeless_tobacco": sev_yes_no,
    "physical_activity": sev_activity,
    "diet_score": sev_diet_score,
    "alcohol_audit": sev_alcohol_audit,
    "sleep_hours": sev_sleep_hours,
    "stress_score": sev_stress,
    "genetic_mutation": sev_yes_no,
    "prs_percentile": sev_prs,
    "cac": sev_cac,
    "hscrp": sev_hscrp,
    "bp_treatment": _sev_treatment,
    "lipid_treatment": _sev_treatment,
    "glucose_treatment": _sev_treatment,
    "kidney_treatment": _sev_treatment,
}

# Features whose severity depends on more than their own value.
_CONTEXTUAL = {
    "waist": lambda v, ctx: sev_waist(v, ctx["sex"]),
    "whr": lambda v, ctx: sev_whr(v, ctx["sex"]),
    "hdl": lambda v, ctx: _sev_hdl(v, ctx["sex"]),
    "lpa": lambda v, ctx: sev_lpa(v, ctx["lpa_unit"]),
    "egfr": lambda v, ctx: sev_egfr(v, ctx["uacr"], ctx["ckd"]),
    "smoking_status": lambda v, ctx: sev_smoking_status(v, ctx["years_since_quit"]),
    # sev_family_history returns (severity, specialist_referral_flag).
    "family_history": lambda v, ctx: sev_family_history(v)[0],
}

_IGNORE = {"Patient_ID", "patient_id", "age", "biological_sex"}


def _number(patient, key: str) -> Optional[float]:
    value = patient.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _severity_for(feature: str, value: Any, ctx: Dict[str, Any]) -> Optional[float]:
    if isinstance(value, str) and value.strip().lower() in _UNKNOWN:
        return None
    try:
        if feature in _CONTEXTUAL:
            return float(_CONTEXTUAL[feature](value, ctx))
        func = _SIMPLE.get(feature)
        if func is None:
            return None
        return float(func(value))
    except (TypeError, ValueError):
        # A numeric field carrying a non-numeric value, e.g. a stray "Unknown".
        return None


def calculate_patient_severity(patient) -> Dict[str, Dict[str, Any]]:
    """Per-parameter severity keyed by feature, in the dashboard's shape."""

    ckd_raw = patient.get("ckd")
    ctx = {
        "sex": str(patient.get("biological_sex", "")),
        "uacr": _number(patient, "uacr"),
        "ckd": ckd_raw if isinstance(ckd_raw, str) else None,
        "years_since_quit": _number(patient, "years_since_quit"),
        # adapter.create_hhs_input pins the same unit when scoring.
        "lpa_unit": "mg/dL",
    }

    patient_data: Dict[str, Dict[str, Any]] = {}

    for feature in patient.index:
        if feature in _IGNORE:
            continue

        metadata = HHS_FIELD_METADATA.get(feature) or {}
        excel_name = metadata.get("label", feature.replace("_", " ").title())
        unit = metadata.get("unit", "")
        value = patient[feature]

        if value is None:
            patient_data[feature] = {
                "value": None,
                "severity": None,
                "status": "Unknown",
                "excel_name": excel_name,
                "unit": unit,
            }
            continue

        patient_data[feature] = {
            "value": value,
            "severity": _severity_for(feature, value, ctx),
            "excel_name": excel_name,
            "unit": unit,
        }

    return patient_data

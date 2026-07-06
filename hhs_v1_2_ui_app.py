#!/usr/bin/env python3
"""
HHS Clinical Application v1.2 - Fixed UI + Locked Formula
=========================================================

Streamlit application for manual entry of patient data and deterministic
Heart Health Score calculation using the locked HHS-v1.2 implementation profile.

Run UI:
    streamlit run hhs_v1_2_fixed_ui_app.py

Run CLI sample:
    python hhs_v1_2_fixed_ui_app.py --sample

Run CLI JSON:
    python hhs_v1_2_fixed_ui_app.py --cli sample_patient_hhs_v1_2_fixed.json

Important:
- This is a research/prototype implementation for cardiologist review.
- It is not validated for clinical decision-making.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

try:  # Streamlit is required only for UI mode.
    import pandas as pd
    import streamlit as st
except Exception:  # pragma: no cover - allows CLI/core import without streamlit installed.
    pd = None
    st = None


# =============================================================================
# Locked HHS-v1.2 model configuration
# =============================================================================

MODEL_VERSION = "HHS-v1.2"
PROFILE_ID = "HHS-General-India-v1"
WEIGHT_PROFILE_TYPE = "general_cvd_india_provisional"
INTERACTION_MODE = "v1_zero_default"
CLINICIAN_PROFILE_ID = None

D_STAR = 0.25
W_STAR = 20.0

# Locked HHS-General-India-v1 profile. Sum = 75.
DOMAIN_WEIGHTS: Dict[str, float] = {
    "Lipids": 13.0,
    "Blood Pressure": 10.0,
    "Glucose": 8.0,
    "Tobacco": 9.0,
    "Adiposity": 8.0,
    "Kidney": 7.0,
    "Activity": 5.0,
    "Diet": 5.0,
    "Behavioral": 4.0,
    "Inherited Risk": 6.0,
}

# Interaction architecture exists, but default v1.2 mode is zero unless research-gated.
INTERACTION_WEIGHTS: Dict[Tuple[str, str], float] = {}

# Treatment residual budget. Sum = 10.
TREATMENT_RHO: Dict[str, float] = {
    "Blood Pressure": 3.0,
    "Lipids": 3.0,
    "Glucose": 3.0,
    "Kidney": 1.0,
}

BEHAVIORAL_COMPONENT_WEIGHTS: Dict[str, float] = {
    "alcohol_audit": 0.40,
    "sleep_hours": 0.35,
    "stress_score": 0.25,
}

LIPID_MODIFIER_WEIGHTS = {"triglycerides": 0.55, "lpa": 0.45}
TOBACCO_MODIFIER_WEIGHTS = {"pack_years": 0.75, "smokeless_tobacco": 0.25}
INHERITED_MODIFIER_WEIGHTS = {"prs_percentile": 1.00}
BP_MODIFIER_WEIGHTS = {"lvh": 1.00}
MODIFIER_BETA = 0.35

FIELD_HALF_LIFE_MONTHS: Dict[str, float] = {
    "sbp": 6,
    "dbp": 6,
    "resting_hr": 3,
    "ldl": 12,
    "hdl": 12,
    "total_cholesterol": 12,
    "non_hdl": 12,
    "tc_hdl_ratio": 12,
    "apob": 12,
    "triglycerides": 12,
    "lpa": 120,
    "hba1c": 6,
    "fasting_glucose": 3,
    "diabetes": 24,
    "egfr": 6,
    "uacr": 6,
    "ckd": 24,
    "bmi": 12,
    "waist": 12,
    "whr": 12,
    "smoking_status": 12,
    "pack_years": 240,
    "years_since_quit": 120,
    "smokeless_tobacco": 12,
    "physical_activity": 3,
    "diet_score": 3,
    "sleep_hours": 3,
    "alcohol_audit": 3,
    "stress_score": 3,
    "family_history": 9999,
    "genetic_mutation": 9999,
    "prs_percentile": 9999,
    "lvh": 24,
    "cac": 60,
    "hscrp": 3,
}

FIELD_PRIORS: Dict[str, float] = {
    "bp": 0.30,
    "lipid": 0.32,
    "glucose": 0.25,
    "kidney": 0.18,
    "adiposity": 0.30,
    "tobacco": 0.20,
    "activity": 0.45,
    "diet": 0.35,
    "behavioral": 0.25,
    "inherited": 0.10,
}

# Anchor fields used for C_core freshness. Missingness itself is handled by D.
DOMAIN_ANCHORS_FOR_Q: Dict[str, List[str]] = {
    "Blood Pressure": ["sbp", "dbp"],
    "Lipids": ["ldl", "non_hdl", "tc_hdl_ratio", "apob"],
    "Glucose": ["hba1c", "fasting_glucose", "diabetes"],
    "Tobacco": ["smoking_status"],
    "Adiposity": ["bmi", "waist"],
    "Kidney": ["egfr", "uacr", "ckd"],
    "Activity": ["physical_activity"],
    "Diet": ["diet_score"],
    "Behavioral": ["alcohol_audit", "sleep_hours", "stress_score"],
    "Inherited Risk": ["family_history"],
}

# These fields influence missing-data uncertainty and VOI. Optional/research fields do not.
REQUIRED_OR_PREFERRED_FIELDS: Dict[str, Tuple[str, str, str]] = {
    "sbp": ("Blood Pressure", "Systolic BP", "bp"),
    "dbp": ("Blood Pressure", "Diastolic BP", "bp"),
    "ldl": ("Lipids", "LDL-C", "lipid"),
    "hba1c": ("Glucose", "HbA1c", "glucose"),
    "egfr": ("Kidney", "eGFR", "kidney"),
    "uacr": ("Kidney", "UACR / Microalbuminuria", "kidney"),
    "bmi": ("Adiposity", "BMI", "adiposity"),
    "waist": ("Adiposity", "Waist circumference", "adiposity"),
    "smoking_status": ("Tobacco", "Smoking status", "tobacco"),
    "physical_activity": ("Activity", "Physical activity", "activity"),
    "diet_score": ("Diet", "Diet score", "diet"),
    "sleep_hours": ("Behavioral", "Sleep duration", "behavioral"),
    "alcohol_audit": ("Behavioral", "Alcohol AUDIT", "behavioral"),
    "stress_score": ("Behavioral", "Stress score", "behavioral"),
    "family_history": ("Inherited Risk", "Premature family history", "inherited"),
}


# =============================================================================
# Deterministic model helpers
# =============================================================================


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(x)))


def clamp_score(x: float) -> float:
    return max(0.0, min(100.0, float(x)))


def piecewise(value: float, points: List[Tuple[float, float]]) -> float:
    value = float(value)
    severity = points[0][1]
    for threshold, sev in points:
        if value >= threshold:
            severity = sev
        else:
            break
    return clamp(severity)


def measurement_confidence(months_old: float, half_life_months: float) -> float:
    if half_life_months <= 0:
        return 1.0
    return clamp(2 ** (-float(months_old) / float(half_life_months)))


def bool_yes(value: Any) -> bool:
    return str(value).strip().lower() in {"yes", "true", "1", "present", "positive", "treated"}


def sev_sbp(v: Any) -> float:
    return piecewise(float(v), [(0, 0.00), (120, 0.20), (130, 0.45), (140, 0.70), (160, 0.90), (180, 1.00)])


def sev_dbp(v: Any) -> float:
    return piecewise(float(v), [(0, 0.00), (80, 0.45), (90, 0.70), (100, 0.90), (120, 1.00)])


def sev_ldl(v: Any) -> float:
    return piecewise(float(v), [(0, 0.00), (100, 0.20), (130, 0.45), (160, 0.75), (190, 1.00)])


def sev_non_hdl(v: Any) -> float:
    return piecewise(float(v), [(0, 0.00), (130, 0.20), (160, 0.45), (190, 0.75), (220, 1.00)])


def sev_tc_hdl_ratio(v: Any) -> float:
    return piecewise(float(v), [(0, 0.00), (3.5, 0.20), (4.5, 0.45), (5.5, 0.75), (6.5, 1.00)])


def sev_apob(v: Any) -> float:
    return piecewise(float(v), [(0, 0.00), (90, 0.35), (110, 0.55), (130, 0.85), (150, 1.00)])


def sev_triglycerides(v: Any) -> float:
    return piecewise(float(v), [(0, 0.00), (150, 0.35), (175, 0.45), (200, 0.60), (500, 1.00)])


def sev_lpa(value: Any, unit: str = "mg/dL") -> float:
    if unit == "nmol/L":
        return piecewise(float(value), [(0, 0.00), (75, 0.40), (125, 0.75), (250, 1.00)])
    return piecewise(float(value), [(0, 0.00), (30, 0.40), (50, 0.75), (100, 1.00)])


def sev_hba1c(v: Any) -> float:
    return piecewise(float(v), [(0, 0.00), (5.7, 0.45), (6.5, 0.70), (8.0, 0.85), (9.0, 1.00)])


def sev_fasting_glucose(v: Any) -> float:
    return piecewise(float(v), [(0, 0.00), (100, 0.45), (126, 0.70), (180, 0.90), (250, 1.00)])


def sev_diabetes(v: Any) -> float:
    return 0.70 if bool_yes(v) else 0.00


def sev_egfr(value: Any, uacr_value: Optional[float], ckd_value: Optional[str]) -> float:
    """
    Locked HHS-v1.2 eGFR rule:
    G2 (60-89) receives only minimal severity unless albuminuria or CKD marker exists.
    """
    egfr = float(value)
    has_marker = (uacr_value is not None and uacr_value >= 30) or bool_yes(ckd_value)
    if egfr >= 90:
        return 0.00
    if egfr >= 60:
        return 0.25 if has_marker else 0.05
    if egfr >= 45:
        return 0.50
    if egfr >= 30:
        return 0.75
    if egfr >= 15:
        return 0.90
    return 1.00


def sev_uacr(v: Any) -> float:
    return piecewise(float(v), [(0, 0.00), (30, 0.45), (300, 1.00)])


def sev_ckd(v: Any) -> float:
    return 0.70 if bool_yes(v) else 0.00


def sev_bmi_indian(v: Any) -> float:
    v = float(v)
    if v < 18.5:
        return 0.40
    return piecewise(v, [(18.5, 0.00), (23.0, 0.35), (25.0, 0.65), (30.0, 0.90), (35.0, 1.00)])


def sev_waist(v: Any, sex: str) -> float:
    value = float(v)
    sex_l = str(sex).lower()
    cutoff1 = 80 if sex_l == "female" else 90
    cutoff2 = cutoff1 + 10
    cutoff3 = cutoff1 + 20
    if value < cutoff1:
        return 0.00
    if value < cutoff2:
        return 0.45
    if value < cutoff3:
        return 0.75
    return 1.00


def sev_whr(v: Any, sex: str) -> float:
    value = float(v)
    sex_l = str(sex).lower()
    c1 = 0.85 if sex_l == "female" else 0.90
    c2 = c1 + 0.05
    c3 = c1 + 0.10
    if value < c1:
        return 0.00
    if value < c2:
        return 0.45
    if value < c3:
        return 0.75
    return 1.00


def sev_smoking_status(value: Any, years_since_quit: Optional[float]) -> float:
    status = str(value).strip().lower().replace(" ", "_")
    if status in {"never", "none", "no"}:
        return 0.00
    if status in {"current_heavy", "heavy"}:
        return 1.00
    if status in {"current", "yes", "smoker"}:
        return 0.75
    if status in {"former", "ex_smoker", "ex"}:
        yq = float(years_since_quit or 0.0)
        return clamp(0.75 * (2 ** (-yq / 4.0)))
    return 0.50


def sev_pack_years(v: Any) -> float:
    return piecewise(float(v), [(0, 0.00), (1, 0.20), (5, 0.40), (10, 0.70), (20, 1.00)])


def sev_yes_no(v: Any) -> float:
    return 1.0 if bool_yes(v) else 0.0


def sev_activity(v: Any) -> float:
    value = float(v)
    if value >= 150:
        return 0.00
    if value >= 90:
        return 0.35
    if value >= 30:
        return 0.65
    return 1.00


def sev_diet_score(v: Any) -> float:
    return clamp(1.0 - float(v) / 100.0)


def sev_sleep_hours(v: Any) -> float:
    value = float(v)
    if 7 <= value <= 9:
        return 0.00
    if 6 <= value < 7 or 9 < value <= 10:
        return 0.35
    if 5 <= value < 6 or 10 < value <= 11:
        return 0.65
    return 1.00


def sev_alcohol_audit(v: Any) -> float:
    value = float(v)
    if value == 0:
        return 0.00
    if value <= 7:
        return 0.20
    if value <= 14:
        return 0.60
    return 1.00


def sev_stress(v: Any) -> float:
    return clamp(float(v) / 10.0)


def sev_family_history(v: Any) -> Tuple[float, bool]:
    """
    Returns (severity, specialist_flag).
    Bare positive history is treated as one premature first-degree relative.
    """
    value = str(v).strip().lower()
    if value in {"none", "no", "unknown", "not measured"}:
        return 0.00, False
    if value in {"yes", "true", "1", "one first-degree relative", "one_fdr_premature", "single", "one"}:
        return 0.70, False
    if value in {"multiple first-degree relatives", "multiple_fdr_premature", "multiple"}:
        return 1.00, False
    if value in {"pathogenic mutation", "pathogenic_mutation", "known pathogenic mutation"}:
        return 1.00, True
    return 0.10, False


def sev_prs(v: Any) -> float:
    value = float(v)
    if value < 50:
        return 0.00
    if value < 80:
        return 0.30
    if value < 95:
        return 0.65
    return 1.00


def sev_cac(v: Any) -> float:
    return piecewise(float(v), [(0, 0.00), (1, 0.30), (100, 0.70), (300, 1.00)])


def sev_hscrp(v: Any) -> float:
    return piecewise(float(v), [(0, 0.00), (1, 0.35), (2, 0.55), (3, 0.70), (10, 1.00)])


def headroom_aggregate(anchor: float, modifiers: List[Tuple[Optional[float], float]], beta: float = MODIFIER_BETA) -> float:
    product = 1.0
    found = False
    for severity, weight in modifiers:
        if severity is None:
            continue
        found = True
        product *= 1.0 - beta * weight * severity
    modifier_effect = 1.0 - product if found else 0.0
    return clamp(anchor + (1.0 - anchor) * modifier_effect)


@dataclass
class FieldRecord:
    domain: str
    label: str
    value: Any
    unit: str
    status: str
    months_old: Optional[float]


class HHSManualScorer:
    def __init__(self, fields: Dict[str, FieldRecord], age: int, sex: str, lpa_unit: str = "mg/dL"):
        self.fields = fields
        self.age = age
        self.sex = sex
        self.lpa_unit = lpa_unit

    def _is_available(self, key: str) -> bool:
        return key in self.fields and self.fields[key].status == "Available" and self.fields[key].value is not None

    def _raw(self, key: str) -> Any:
        return self.fields[key].value

    def _months(self, key: str) -> float:
        return float(self.fields[key].months_old or 0.0)

    def _prior_treatment(self, domain: str) -> float:
        if domain == "Blood Pressure":
            return 0.30 if self.age >= 50 else 0.15
        if domain == "Lipids":
            return 0.25 if self.age >= 50 else 0.10
        if domain == "Glucose":
            return 0.20 if self.age >= 50 else 0.08
        if domain == "Kidney":
            return 0.05
        return 0.0

    def _severity(
        self,
        key: str,
        severity_func: Callable[[Any], float],
        domain_prior_key: str,
        state: str = "expected",
        required: bool = True,
        overrides: Optional[Dict[str, float]] = None,
    ) -> Optional[float]:
        overrides = overrides or {}
        if key in overrides:
            return clamp(overrides[key])

        prior = FIELD_PRIORS.get(domain_prior_key, 0.20)

        if not self._is_available(key):
            if not required:
                return None
            return {"optimistic": 0.0, "expected": prior, "floor": 1.0}[state]

        raw_sev = clamp(severity_func(self._raw(key)))
        half_life = FIELD_HALF_LIFE_MONTHS.get(key, 12.0)
        c = measurement_confidence(self._months(key), half_life)

        if state == "optimistic":
            return clamp(c * raw_sev)
        if state == "floor":
            return clamp(c * raw_sev + (1.0 - c) * 1.0)
        return clamp(c * raw_sev + (1.0 - c) * prior)

    def _optional_num_value(self, key: str) -> Optional[float]:
        if self._is_available(key):
            return float(self._raw(key))
        return None

    def domain_severities(self, state: str = "expected", overrides: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        overrides = overrides or {}

        # Blood Pressure
        sbp = self._severity("sbp", sev_sbp, "bp", state, True, overrides)
        dbp = self._severity("dbp", sev_dbp, "bp", state, True, overrides)
        lvh = self._severity("lvh", sev_yes_no, "bp", state, False, overrides)
        bp_anchor = max(sbp or 0.0, dbp or 0.0)
        bp_r = headroom_aggregate(bp_anchor, [(lvh, BP_MODIFIER_WEIGHTS["lvh"])])

        # Lipids
        ldl = self._severity("ldl", sev_ldl, "lipid", state, True, overrides)
        non_hdl = self._severity("non_hdl", sev_non_hdl, "lipid", state, False, overrides)
        tc_hdl_ratio = self._severity("tc_hdl_ratio", sev_tc_hdl_ratio, "lipid", state, False, overrides)
        apob = self._severity("apob", sev_apob, "lipid", state, False, overrides)
        triglycerides = self._severity("triglycerides", sev_triglycerides, "lipid", state, False, overrides)
        lpa = self._severity("lpa", lambda x: sev_lpa(x, self.lpa_unit), "lipid", state, False, overrides)
        lipid_anchor = max([x for x in [ldl, non_hdl, tc_hdl_ratio, apob] if x is not None] or [FIELD_PRIORS["lipid"]])
        lipid_r = headroom_aggregate(
            lipid_anchor,
            [(triglycerides, LIPID_MODIFIER_WEIGHTS["triglycerides"]), (lpa, LIPID_MODIFIER_WEIGHTS["lpa"])],
        )

        # Glucose
        hba1c = self._severity("hba1c", sev_hba1c, "glucose", state, True, overrides)
        fasting_glucose = self._severity("fasting_glucose", sev_fasting_glucose, "glucose", state, False, overrides)
        diabetes = self._severity("diabetes", sev_diabetes, "glucose", state, False, overrides)
        glucose_r = max([x for x in [hba1c, fasting_glucose, diabetes] if x is not None] or [FIELD_PRIORS["glucose"]])

        # Kidney with conditional eGFR G2 rule.
        uacr_raw = self._optional_num_value("uacr")
        ckd_raw = self._raw("ckd") if self._is_available("ckd") else None
        egfr = self._severity("egfr", lambda x: sev_egfr(x, uacr_raw, ckd_raw), "kidney", state, True, overrides)
        uacr = self._severity("uacr", sev_uacr, "kidney", state, True, overrides)
        ckd = self._severity("ckd", sev_ckd, "kidney", state, False, overrides)
        kidney_r = max([x for x in [egfr, uacr, ckd] if x is not None] or [FIELD_PRIORS["kidney"]])

        # Adiposity
        bmi = self._severity("bmi", sev_bmi_indian, "adiposity", state, True, overrides)
        waist = self._severity("waist", lambda x: sev_waist(x, self.sex), "adiposity", state, True, overrides)
        whr = self._severity("whr", lambda x: sev_whr(x, self.sex), "adiposity", state, False, overrides)
        adiposity_r = max([x for x in [bmi, waist, whr] if x is not None] or [FIELD_PRIORS["adiposity"]])

        # Tobacco
        years_since_quit = self._optional_num_value("years_since_quit")
        smoking = self._severity("smoking_status", lambda x: sev_smoking_status(x, years_since_quit), "tobacco", state, True, overrides)
        pack_years = self._severity("pack_years", sev_pack_years, "tobacco", state, False, overrides)
        smokeless = self._severity("smokeless_tobacco", sev_yes_no, "tobacco", state, False, overrides)
        tobacco_r = headroom_aggregate(
            smoking if smoking is not None else FIELD_PRIORS["tobacco"],
            [(pack_years, TOBACCO_MODIFIER_WEIGHTS["pack_years"]), (smokeless, TOBACCO_MODIFIER_WEIGHTS["smokeless_tobacco"])],
        )

        # Activity and Diet are separate locked domains.
        activity_r = self._severity("physical_activity", sev_activity, "activity", state, True, overrides)
        diet_r = self._severity("diet_score", sev_diet_score, "diet", state, True, overrides)

        # Behavioral = alcohol + sleep + stress only.
        alcohol = self._severity("alcohol_audit", sev_alcohol_audit, "behavioral", state, True, overrides)
        sleep = self._severity("sleep_hours", sev_sleep_hours, "behavioral", state, True, overrides)
        stress = self._severity("stress_score", sev_stress, "behavioral", state, True, overrides)
        behavioral_components = {
            "alcohol_audit": alcohol if alcohol is not None else FIELD_PRIORS["behavioral"],
            "sleep_hours": sleep if sleep is not None else FIELD_PRIORS["behavioral"],
            "stress_score": stress if stress is not None else FIELD_PRIORS["behavioral"],
        }
        behavioral_r = clamp(sum(BEHAVIORAL_COMPONENT_WEIGHTS[k] * behavioral_components[k] for k in BEHAVIORAL_COMPONENT_WEIGHTS))

        # Inherited risk with mutation coupling.
        family_history = None
        family_specialist_flag = False
        if "family_history" in overrides:
            family_history = overrides["family_history"]
        elif self._is_available("family_history"):
            family_history, family_specialist_flag = sev_family_history(self._raw("family_history"))
            c = measurement_confidence(self._months("family_history"), FIELD_HALF_LIFE_MONTHS.get("family_history", 9999))
            if state == "optimistic":
                family_history = clamp(c * family_history)
            elif state == "floor":
                family_history = clamp(c * family_history + (1.0 - c) * 1.0)
            else:
                family_history = clamp(c * family_history + (1.0 - c) * FIELD_PRIORS["inherited"])
        else:
            family_history = {"optimistic": 0.0, "expected": FIELD_PRIORS["inherited"], "floor": 1.0}[state]

        genetic_mutation = self._severity("genetic_mutation", sev_yes_no, "inherited", state, False, overrides)
        prs = self._severity("prs_percentile", sev_prs, "inherited", state, False, overrides)
        inherited_anchor = max([x for x in [family_history, genetic_mutation] if x is not None] or [FIELD_PRIORS["inherited"]])
        inherited_r = headroom_aggregate(inherited_anchor, [(prs, INHERITED_MODIFIER_WEIGHTS["prs_percentile"])])

        return {
            "Lipids": clamp(lipid_r),
            "Blood Pressure": clamp(bp_r),
            "Glucose": clamp(glucose_r),
            "Tobacco": clamp(tobacco_r),
            "Adiposity": clamp(adiposity_r),
            "Kidney": clamp(kidney_r),
            "Activity": clamp(activity_r if activity_r is not None else FIELD_PRIORS["activity"]),
            "Diet": clamp(diet_r if diet_r is not None else FIELD_PRIORS["diet"]),
            "Behavioral": clamp(behavioral_r),
            "Inherited Risk": clamp(inherited_r),
        }

    def treatment_values(self, state: str = "expected") -> Dict[str, float]:
        mapping = {
            "Blood Pressure": "bp_treatment",
            "Lipids": "lipid_treatment",
            "Glucose": "glucose_treatment",
            "Kidney": "kidney_treatment",
        }
        out = {}
        for domain, field in mapping.items():
            if self._is_available(field):
                out[domain] = 1.0 if bool_yes(self._raw(field)) else 0.0
            else:
                out[domain] = {
                    "optimistic": 0.0,
                    "expected": self._prior_treatment(domain),
                    "floor": 1.0,
                }[state]
        return out

    def burden(self, severities: Dict[str, float], treatment_values: Dict[str, float]) -> Tuple[float, Dict[str, Any]]:
        rows = []
        treatment_rows = []
        interaction_rows = []
        main_burden = 0.0
        treatment_burden = 0.0
        interaction_burden = 0.0

        for domain, weight in DOMAIN_WEIGHTS.items():
            severity = severities[domain]
            main = weight * severity
            main_burden += main

            treatment = 0.0
            if domain in TREATMENT_RHO:
                t = treatment_values.get(domain, 0.0)
                treatment = TREATMENT_RHO[domain] * t * (1.0 - severity)
                treatment_burden += treatment
                if treatment > 0.0001:
                    treatment_rows.append({
                        "Domain": domain,
                        "Treatment residual": round(treatment, 3),
                        "Treatment coefficient rho": TREATMENT_RHO[domain],
                        "Treatment value T_g": round(t, 3),
                    })

            rows.append({
                "Domain": domain,
                "Weight": round(weight, 2),
                "Severity": round(severity, 3),
                "Main contribution": round(main, 3),
                "Treatment contribution": round(treatment, 3),
                "Total domain contribution": round(main + treatment, 3),
                "Status": severity_status(severity),
            })

        for (u, v), lam in INTERACTION_WEIGHTS.items():
            c = lam * severities.get(u, 0.0) * severities.get(v, 0.0)
            interaction_burden += c
            if c > 0.0001:
                interaction_rows.append({"Pair": f"{u} × {v}", "Points": round(c, 3), "Lambda": lam})

        total = main_burden + treatment_burden + interaction_burden
        return total, {
            "main": main_burden,
            "treatment": treatment_burden,
            "interaction": interaction_burden,
            "domain_rows": sorted(rows, key=lambda x: x["Total domain contribution"], reverse=True),
            "treatment_rows": sorted(treatment_rows, key=lambda x: x["Treatment residual"], reverse=True),
            "interaction_rows": sorted(interaction_rows, key=lambda x: x["Points"], reverse=True),
        }

    def domain_quality_Q(self, domain: str) -> float:
        anchors = DOMAIN_ANCHORS_FOR_Q.get(domain, [])
        sum_conf = 0.0
        n_obs = 0
        for key in anchors:
            if self._is_available(key):
                sum_conf += measurement_confidence(self._months(key), FIELD_HALF_LIFE_MONTHS.get(key, 12.0))
                n_obs += 1
        return clamp(sum_conf / max(1, n_obs))

    def core_coverage(self) -> float:
        num = 0.0
        den = 0.0
        for domain, weight in DOMAIN_WEIGHTS.items():
            q = self.domain_quality_Q(domain)
            num += weight * q
            den += weight
        return clamp(num / den if den else 0.0)

    def recommended_inputs(self) -> List[Dict[str, Any]]:
        # Simulation-based VOI approximation: set missing field to optimistic severity and recompute expected burden.
        R_exp = self.domain_severities("expected")
        T_exp = self.treatment_values("expected")
        B_exp, _ = self.burden(R_exp, T_exp)
        out = []
        for key, (domain, label, _prior_key) in REQUIRED_OR_PREFERRED_FIELDS.items():
            if self._is_available(key):
                continue
            R_override = self.domain_severities("expected", overrides={key: 0.0})
            B_override, _ = self.burden(R_override, T_exp)
            delta = max(0.0, B_exp - B_override)
            out.append({
                "Field": label,
                "Domain": domain,
                "Expected impact points": round(delta, 3),
                "Priority": "High" if delta >= 2 else "Medium" if delta >= 0.75 else "Low",
            })

        for domain, field in {
            "Blood Pressure": "bp_treatment",
            "Lipids": "lipid_treatment",
            "Glucose": "glucose_treatment",
            "Kidney": "kidney_treatment",
        }.items():
            if not self._is_available(field):
                r = R_exp.get(domain, 0.0)
                voi = TREATMENT_RHO[domain] * self._prior_treatment(domain) * (1.0 - r)
                out.append({
                    "Field": f"{domain} treatment status",
                    "Domain": domain,
                    "Expected impact points": round(max(0.0, voi), 3),
                    "Priority": "Medium" if voi >= 0.75 else "Low",
                })

        return sorted(out, key=lambda x: x["Expected impact points"], reverse=True)[:8]

    def detect_red_flags(self) -> List[Dict[str, Any]]:
        flags: List[Dict[str, Any]] = []

        def available_value(key: str) -> Optional[Any]:
            rec = self.fields.get(key)
            if rec and rec.status == "Available":
                return rec.value
            return None

        sbp = available_value("sbp")
        dbp = available_value("dbp")
        if (sbp is not None and float(sbp) >= 180) or (dbp is not None and float(dbp) >= 120):
            flags.append({"flag": "hypertensive_crisis_range", "message": "SBP ≥180 or DBP ≥120", "suppress_score": False})

        ldl = available_value("ldl")
        if ldl is not None and float(ldl) >= 190:
            flags.append({"flag": "severe_ldl_range", "message": "LDL-C ≥190 mg/dL", "suppress_score": False})

        hba1c = available_value("hba1c")
        if hba1c is not None and float(hba1c) >= 9:
            flags.append({"flag": "very_poor_glycemic_control", "message": "HbA1c ≥9%", "suppress_score": False})

        cac = available_value("cac")
        if cac is not None and float(cac) >= 300:
            flags.append({"flag": "high_cac_burden", "message": "CAC ≥300 — optional imaging high-burden flag", "suppress_score": False})

        family_history = available_value("family_history")
        genetic_mutation = available_value("genetic_mutation")
        if str(family_history).strip().lower() == "pathogenic mutation" or bool_yes(genetic_mutation):
            flags.append({
                "flag": "pathogenic_mutation",
                "message": "Known or reported pathogenic cardiovascular mutation — inherited-risk specialist pathway",
                "suppress_score": False,
            })

        for key, label in [("chest_pain", "Active chest pain"), ("syncope", "Syncope"), ("severe_dyspnea", "Severe dyspnea"), ("neuro_deficit", "Neurologic deficit symptoms")]:
            if bool_yes(available_value(key)):
                flags.append({"flag": key, "message": label, "suppress_score": True})

        for key, label in [
            ("known_mi", "Known myocardial infarction"),
            ("known_stroke", "Known stroke"),
            ("known_hf", "Known heart failure"),
            ("known_pad", "Known peripheral artery disease"),
        ]:
            if bool_yes(available_value(key)):
                flags.append({"flag": key, "message": f"{label} — secondary-prevention pathway", "suppress_score": False})

        return flags

    def calculate(self) -> Dict[str, Any]:
        R_opt = self.domain_severities("optimistic")
        R_exp = self.domain_severities("expected")
        R_floor = self.domain_severities("floor")

        T_opt = self.treatment_values("optimistic")
        T_exp = self.treatment_values("expected")
        T_floor = self.treatment_values("floor")

        B_opt, parts_opt = self.burden(R_opt, T_opt)
        B_exp, parts_exp = self.burden(R_exp, T_exp)
        B_floor, parts_floor = self.burden(R_floor, T_floor)

        S_opt = clamp_score(100.0 - B_opt)
        S_exp = clamp_score(100.0 - B_exp)
        S_floor = clamp_score(100.0 - B_floor)

        W = max(0.0, S_opt - S_exp)
        W_full = max(0.0, S_opt - S_floor)
        D = clamp((B_floor - B_opt) / 100.0)
        C_core = self.core_coverage()
        confidence = clamp_score(100.0 * (0.70 * (1.0 - D) + 0.30 * C_core))

        red_flags = self.detect_red_flags()
        abstained = (D > D_STAR) or (W > W_STAR) or any(flag.get("suppress_score") for flag in red_flags)
        reasons = []
        if D > D_STAR:
            reasons.append(f"Information Deficit D={D:.3f} exceeds d*={D_STAR}")
        if W > W_STAR:
            reasons.append(f"Optimistic-to-expected width W={W:.2f} exceeds w*={W_STAR}")
        if any(flag.get("suppress_score") for flag in red_flags):
            reasons.append("Acute red flag suppresses routine interpretation")

        result = {
            "metadata": {
                "model_version": MODEL_VERSION,
                "profile_id": PROFILE_ID,
                "weight_profile_type": WEIGHT_PROFILE_TYPE,
                "interaction_mode": INTERACTION_MODE,
                "clinician_profile_id": CLINICIAN_PROFILE_ID,
            },
            "hhs": round(S_exp, 1),
            "category": score_category(S_exp, red_flags, abstained),
            "data_confidence": round(confidence, 1),
            "confidence_label": confidence_label(confidence),
            "score_interval": {
                "floor": round(S_floor, 1),
                "expected": round(S_exp, 1),
                "optimistic": round(S_opt, 1),
                "optimistic_to_expected_width_W": round(W, 2),
                "full_width": round(W_full, 2),
            },
            "information_deficit_D": round(D, 4),
            "core_freshness_C_core": round(C_core, 4),
            "burden": {
                "total": round(B_exp, 2),
                "main": round(parts_exp["main"], 2),
                "treatment": round(parts_exp["treatment"], 2),
                "interaction": round(parts_exp["interaction"], 2),
            },
            "domain_rows": parts_exp["domain_rows"],
            "treatment_rows": parts_exp["treatment_rows"],
            "interaction_rows": parts_exp["interaction_rows"],
            "domain_severities": {k: round(v, 4) for k, v in R_exp.items()},
            "red_flags": red_flags,
            "recommended_inputs": self.recommended_inputs(),
            "abstained": abstained,
            "abstention_reasons": reasons,
            "notes": [
                "Research prototype only; not validated for clinical decision-making.",
                "Age and sex are context variables for priors/audit, not scored burden domains in HHS-v1.2.",
                "Interaction burden is architecturally supported but zero by default in HHS-v1.2.",
            ],
        }
        return result


def severity_status(severity: float) -> str:
    if severity >= 0.75:
        return "High"
    if severity >= 0.45:
        return "Moderate"
    if severity >= 0.20:
        return "Mild"
    return "Low"


def score_category(score: float, red_flags: List[Dict[str, Any]], abstained: bool) -> str:
    if any(flag.get("suppress_score") for flag in red_flags):
        return "Routine score interpretation suppressed"
    if abstained:
        return "Abstained / provisional due to uncertainty"
    if score >= 80:
        return "Favorable cardiovascular health profile"
    if score >= 65:
        return "Mildly elevated cardiovascular burden"
    if score >= 50:
        return "Moderate cardiovascular burden"
    if score >= 30:
        return "High cardiovascular burden"
    return "Very high cardiovascular burden"


def confidence_label(value: float) -> str:
    if value >= 85:
        return "High"
    if value >= 70:
        return "Moderate-high"
    if value >= 55:
        return "Moderate"
    if value >= 40:
        return "Low"
    return "Very low"


# =============================================================================
# CLI helpers
# =============================================================================


def sample_payload() -> Dict[str, Any]:
    return {
        "visit": {"patient_id": "HHS-DEMO-0001", "age": 54, "biological_sex": "Male"},
        "fields": {
            "sbp": {"domain": "Blood Pressure", "label": "Systolic BP", "value": 146, "unit": "mmHg", "status": "Available", "months_old": 1},
            "dbp": {"domain": "Blood Pressure", "label": "Diastolic BP", "value": 92, "unit": "mmHg", "status": "Available", "months_old": 1},
            "ldl": {"domain": "Lipids", "label": "LDL-C", "value": 156, "unit": "mg/dL", "status": "Available", "months_old": 3},
            "hba1c": {"domain": "Glucose", "label": "HbA1c", "value": 6.8, "unit": "%", "status": "Available", "months_old": 2},
            "egfr": {"domain": "Kidney", "label": "eGFR", "value": 82, "unit": "mL/min/1.73m²", "status": "Available", "months_old": 4},
            "uacr": {"domain": "Kidney", "label": "UACR", "value": 18, "unit": "mg/g", "status": "Available", "months_old": 4},
            "bmi": {"domain": "Adiposity", "label": "BMI", "value": 27.4, "unit": "kg/m²", "status": "Available", "months_old": 2},
            "waist": {"domain": "Adiposity", "label": "Waist circumference", "value": 98, "unit": "cm", "status": "Available", "months_old": 2},
            "smoking_status": {"domain": "Tobacco", "label": "Smoking status", "value": "Former", "unit": "", "status": "Available", "months_old": 2},
            "years_since_quit": {"domain": "Tobacco", "label": "Years since quit", "value": 5, "unit": "years", "status": "Available", "months_old": 0},
            "pack_years": {"domain": "Tobacco", "label": "Pack-years", "value": 14, "unit": "pack-years", "status": "Available", "months_old": 0},
            "physical_activity": {"domain": "Activity", "label": "Physical activity", "value": 60, "unit": "min/week", "status": "Available", "months_old": 1},
            "diet_score": {"domain": "Diet", "label": "Diet score", "value": 62, "unit": "/100", "status": "Available", "months_old": 1},
            "sleep_hours": {"domain": "Behavioral", "label": "Sleep duration", "value": 6.2, "unit": "hours/night", "status": "Available", "months_old": 1},
            "alcohol_audit": {"domain": "Behavioral", "label": "Alcohol AUDIT", "value": 6, "unit": "score", "status": "Available", "months_old": 1},
            "stress_score": {"domain": "Behavioral", "label": "Stress score", "value": 5, "unit": "score", "status": "Unknown", "months_old": None},
            "family_history": {"domain": "Inherited Risk", "label": "Premature family history", "value": "One first-degree relative", "unit": "", "status": "Available", "months_old": 0},
            "bp_treatment": {"domain": "Treatment", "label": "On BP treatment", "value": "Yes", "unit": "", "status": "Available", "months_old": 0},
            "lipid_treatment": {"domain": "Treatment", "label": "On lipid-lowering treatment", "value": "No", "unit": "", "status": "Available", "months_old": 0},
            "glucose_treatment": {"domain": "Treatment", "label": "On glucose treatment", "value": "No", "unit": "", "status": "Available", "months_old": 0},
        },
        "lpa_unit": "mg/dL",
    }


def fields_from_payload(payload: Dict[str, Any]) -> Dict[str, FieldRecord]:
    raw_fields = payload.get("fields", {})
    return {k: FieldRecord(**v) for k, v in raw_fields.items()}


def run_cli(payload: Dict[str, Any]) -> Dict[str, Any]:
    visit = payload.get("visit", {})
    fields = fields_from_payload(payload)
    scorer = HHSManualScorer(fields, int(visit.get("age", 54)), str(visit.get("biological_sex", "Male")), str(payload.get("lpa_unit", "mg/dL")))
    result = scorer.calculate()
    return {"visit": visit, "assessment": result}


# =============================================================================
# Streamlit UI
# =============================================================================



# =============================================================================
# Restored Streamlit UI: previous visual layout + fixed HHS-v1.2 backend
# =============================================================================

def run_streamlit_app() -> None:
    if st is None or pd is None:
        raise RuntimeError("Streamlit and pandas are required for UI mode.")

    st.set_page_config(
        page_title="Cardiovascular Health Score",
        page_icon="🫀",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    with st.sidebar:
        appearance = st.radio("Appearance", ["Clinical light", "Clinical dark"], index=0)
        st.divider()
        st.markdown("### Model")
        st.caption(MODEL_VERSION)
        st.caption(PROFILE_ID)
        st.caption(f"Interaction mode: {INTERACTION_MODE}")
        st.caption(f"Domain weight total: {sum(DOMAIN_WEIGHTS.values()):.0f}")
        st.divider()
        st.caption("Research prototype only. Not validated for clinical decisions.")

    is_dark = appearance == "Clinical dark"

    palette = {
        "light": {
            "app_bg": "#f4f7fb",
            "panel": "#ffffff",
            "panel_2": "#f8fafc",
            "panel_3": "#eef4fb",
            "text": "#0f172a",
            "muted": "#64748b",
            "border": "#d8e2ef",
            "soft_border": "#e8eef6",
            "primary": "#173b57",
            "primary_2": "#0f4c81",
            "good_bg": "#ecfdf5",
            "good_text": "#047857",
            "good_border": "#a7f3d0",
            "warn_bg": "#fff7ed",
            "warn_text": "#9a3412",
            "warn_border": "#fed7aa",
            "danger_bg": "#fef2f2",
            "danger_text": "#991b1b",
            "danger_border": "#fecaca",
            "info_bg": "#eff6ff",
            "info_text": "#1d4ed8",
            "info_border": "#bfdbfe",
            "shadow": "0 18px 42px rgba(15, 23, 42, 0.07)",
            "bar_bg": "#e2e8f0",
        },
        "dark": {
            "app_bg": "#081120",
            "panel": "#101b2d",
            "panel_2": "#0d1728",
            "panel_3": "#14243a",
            "text": "#edf4ff",
            "muted": "#a6b6cd",
            "border": "#25364d",
            "soft_border": "#1d2d42",
            "primary": "#8fc7ff",
            "primary_2": "#5ea8ee",
            "good_bg": "#08291f",
            "good_text": "#5ee6ae",
            "good_border": "#145c47",
            "warn_bg": "#2b1b07",
            "warn_text": "#ffc36b",
            "warn_border": "#704613",
            "danger_bg": "#2b0d12",
            "danger_text": "#ff9eaa",
            "danger_border": "#72202b",
            "info_bg": "#0b2441",
            "info_text": "#93c5fd",
            "info_border": "#255b91",
            "shadow": "0 18px 42px rgba(0, 0, 0, 0.30)",
            "bar_bg": "#1c2c42",
        },
    }
    P = palette["dark" if is_dark else "light"]

    st.markdown(
        f"""
<style>
    :root {{
        --app-bg: {P['app_bg']}; --panel: {P['panel']}; --panel-2: {P['panel_2']}; --panel-3: {P['panel_3']};
        --text: {P['text']}; --muted: {P['muted']}; --border: {P['border']}; --soft-border: {P['soft_border']};
        --primary: {P['primary']}; --primary-2: {P['primary_2']}; --good-bg: {P['good_bg']}; --good-text: {P['good_text']};
        --good-border: {P['good_border']}; --warn-bg: {P['warn_bg']}; --warn-text: {P['warn_text']}; --warn-border: {P['warn_border']};
        --danger-bg: {P['danger_bg']}; --danger-text: {P['danger_text']}; --danger-border: {P['danger_border']};
        --info-bg: {P['info_bg']}; --info-text: {P['info_text']}; --info-border: {P['info_border']}; --shadow: {P['shadow']}; --bar-bg: {P['bar_bg']};
    }}
    .stApp {{ background: var(--app-bg); color: var(--text); }}
    .main .block-container {{ max-width: 1500px; padding-top: 1.15rem; padding-bottom: 3rem; }}
    html, body, [class*="css"] {{ font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    section[data-testid="stSidebar"] {{ background: var(--panel); border-right: 1px solid var(--border); }}
    section[data-testid="stSidebar"] * {{ color: var(--text); }}
    .app-header {{ background: radial-gradient(circle at top right, rgba(79,140,201,0.12), transparent 34%), linear-gradient(135deg, var(--panel) 0%, var(--panel-2) 100%); border: 1px solid var(--border); border-radius: 22px; padding: 1.25rem 1.35rem; box-shadow: var(--shadow); margin-bottom: 0.85rem; }}
    .header-row {{ display: flex; justify-content: space-between; gap: 1.2rem; align-items: flex-start; flex-wrap: wrap; }}
    .eyebrow {{ color: var(--primary); text-transform: uppercase; letter-spacing: 0.09em; font-size: 0.75rem; font-weight: 850; margin-bottom: 0.35rem; }}
    .page-title {{ color: var(--text); font-size: 2rem; line-height: 1.1; font-weight: 860; margin: 0; }}
    .page-subtitle {{ color: var(--muted); font-size: 0.96rem; line-height: 1.65; margin-top: 0.65rem; max-width: 980px; }}
    .badge-row {{ display:flex; gap:0.45rem; flex-wrap:wrap; margin-top:0.85rem; }}
    .badge {{ display:inline-flex; align-items:center; padding:0.35rem 0.65rem; border-radius:999px; font-size:0.74rem; font-weight:800; border:1px solid var(--border); background:var(--panel-2); color:var(--muted); white-space:nowrap; }}
    .badge.info {{ color:var(--info-text); background:var(--info-bg); border-color:var(--info-border); }}
    .badge.good {{ color:var(--good-text); background:var(--good-bg); border-color:var(--good-border); }}
    .badge.warn {{ color:var(--warn-text); background:var(--warn-bg); border-color:var(--warn-border); }}
    .section-card {{ background:var(--panel); border:1px solid var(--border); border-radius:20px; padding:1.05rem; box-shadow:var(--shadow); height:100%; margin-bottom:1rem; }}
    .section-title {{ color:var(--text); font-size:1.03rem; font-weight:850; margin:0 0 0.25rem 0; }}
    .section-caption {{ color:var(--muted); font-size:0.84rem; line-height:1.55; margin:0 0 0.9rem 0; }}
    .input-group {{ border:1px solid var(--soft-border); border-radius:18px; background:var(--panel-2); padding:0.95rem; margin-bottom:0.85rem; }}
    .input-group-title {{ font-size:0.9rem; font-weight:830; color:var(--text); margin-bottom:0.2rem; }}
    .input-group-note {{ font-size:0.78rem; color:var(--muted); margin-bottom:0.7rem; line-height:1.5; }}
    .metric-card {{ background:var(--panel); border:1px solid var(--border); border-radius:20px; padding:1.05rem; box-shadow:var(--shadow); min-height:128px; }}
    .metric-card.good {{ background:var(--good-bg); border-color:var(--good-border); }}
    .metric-card.warn {{ background:var(--warn-bg); border-color:var(--warn-border); }}
    .metric-card.danger {{ background:var(--danger-bg); border-color:var(--danger-border); }}
    .metric-label {{ color:var(--muted); font-size:0.76rem; text-transform:uppercase; letter-spacing:0.06em; font-weight:850; }}
    .metric-value {{ color:var(--text); font-size:1.8rem; line-height:1.1; font-weight:880; margin-top:0.58rem; }}
    .metric-subtitle {{ color:var(--muted); font-size:0.83rem; line-height:1.45; margin-top:0.42rem; }}
    .feed-row {{ display:grid; grid-template-columns:1fr auto; align-items:center; gap:0.75rem; padding:0.74rem 0.8rem; border:1px solid var(--soft-border); border-radius:16px; background:var(--panel-2); margin-bottom:0.55rem; }}
    .feed-name {{ color:var(--text); font-weight:820; font-size:0.87rem; }}
    .feed-meta {{ color:var(--muted); font-size:0.77rem; line-height:1.45; margin-top:0.15rem; }}
    .pill {{ display:inline-flex; border-radius:999px; padding:0.28rem 0.55rem; font-size:0.72rem; font-weight:820; border:1px solid var(--border); background:var(--panel-3); color:var(--muted); white-space:nowrap; }}
    .pill.good {{ background:var(--good-bg); border-color:var(--good-border); color:var(--good-text); }}
    .pill.warn {{ background:var(--warn-bg); border-color:var(--warn-border); color:var(--warn-text); }}
    .pill.danger {{ background:var(--danger-bg); border-color:var(--danger-border); color:var(--danger-text); }}
    .bar-outer {{ width:100%; height:10px; border-radius:999px; background:var(--bar-bg); overflow:hidden; margin-top:0.38rem; }}
    .bar-inner {{ height:100%; border-radius:999px; background:linear-gradient(90deg,var(--primary),var(--primary-2)); }}
    .review-box {{ border:1px solid var(--border); border-radius:18px; padding:0.95rem; background:var(--panel-2); margin-bottom:0.78rem; }}
    .review-box.warn {{ border-color:var(--warn-border); background:var(--warn-bg); }}
    .review-box.good {{ border-color:var(--good-border); background:var(--good-bg); }}
    .review-title {{ color:var(--text); font-size:0.92rem; font-weight:850; margin-bottom:0.25rem; }}
    .review-text {{ color:var(--muted); font-size:0.83rem; line-height:1.55; }}
    label[data-testid="stWidgetLabel"] p {{ color:var(--text) !important; font-weight:680; }}
    div[data-baseweb="input"], div[data-baseweb="select"] > div, textarea, input {{ background-color:var(--panel-2) !important; color:var(--text) !important; border-color:var(--border) !important; border-radius:12px !important; }}
    div[data-baseweb="select"] span {{ color:var(--text) !important; }}
    [data-testid="stDataFrame"] {{ border:1px solid var(--border); border-radius:16px; overflow:hidden; }}
    .stButton > button, .stDownloadButton > button {{ border-radius:12px; border:1px solid var(--border); font-weight:800; background:var(--panel-2); color:var(--text); }}
    .stButton > button[kind="primary"] {{ background:var(--primary); color:white; border-color:var(--primary); }}
    div[data-testid="stTabs"] button {{ font-weight:780; color:var(--muted); }}
    div[data-testid="stTabs"] button[aria-selected="true"] {{ color:var(--primary); }}
    @media (max-width:900px) {{ .page-title {{ font-size:1.45rem; }} .metric-value {{ font-size:1.45rem; }} .feed-row {{ grid-template-columns:1fr; }} }}
</style>
""",
        unsafe_allow_html=True,
    )

    def html(text: str) -> None:
        st.markdown(text, unsafe_allow_html=True)

    def section_header(title: str, caption: str | None = None) -> None:
        html(f'<p class="section-title">{title}</p>')
        if caption:
            html(f'<p class="section-caption">{caption}</p>')

    def metric_card(label: str, value: str, subtitle: str, variant: str = "") -> None:
        html(
            f"""
            <div class="metric-card {variant}">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{value}</div>
                <div class="metric-subtitle">{subtitle}</div>
            </div>
            """
        )

    def input_group_start(title: str, note: str | None = None) -> None:
        html('<div class="input-group">')
        html(f'<div class="input-group-title">{title}</div>')
        if note:
            html(f'<div class="input-group-note">{note}</div>')

    def input_group_end() -> None:
        html("</div>")

    fields: Dict[str, FieldRecord] = {}
    feeds: List[Dict[str, Any]] = []

    def register_field(key: str, domain: str, label: str, value: Any, unit: str, status: str, months_old: Optional[float]) -> None:
        fields[key] = FieldRecord(domain, label, value, unit, status, months_old)
        feeds.append({"Domain": domain, "Field": label, "Value": value, "Unit": unit, "Status": status, "Months old": months_old})

    def availability(label: str, key: str, default: str = "Available") -> str:
        options = ["Available", "Unknown", "Not measured"]
        return st.selectbox(label, options, index=options.index(default), key=key)

    def number_input_field(
        key: str,
        domain: str,
        label: str,
        min_value: float,
        max_value: float,
        default: float,
        step: float,
        unit: str,
        default_status: str = "Available",
        months_default: float = 0.0,
    ) -> None:
        status = availability(f"{label} status", f"{key}_status", default_status)
        if status != "Available":
            register_field(key, domain, label, None, unit, status, None)
            return
        c1, c2 = st.columns([1.25, 0.75])
        with c1:
            value = st.number_input(f"{label} ({unit})", min_value=min_value, max_value=max_value, value=default, step=step, key=f"{key}_value")
        with c2:
            months = st.number_input("Months old", min_value=0.0, max_value=240.0, value=months_default, step=1.0, key=f"{key}_months")
        register_field(key, domain, label, value, unit, "Available", months)

    def categorical_field(key: str, domain: str, label: str, options: List[str], default: str) -> None:
        value = st.selectbox(label, options, index=options.index(default), key=f"{key}_value")
        status = "Unknown" if value == "Unknown" else "Available"
        register_field(key, domain, label, value, "", status, 0.0 if status == "Available" else None)

    def yes_no_field(key: str, domain: str, label: str, default: str = "Unknown") -> None:
        value = st.selectbox(label, ["Unknown", "No", "Yes"], index=["Unknown", "No", "Yes"].index(default), key=f"{key}_value")
        status = "Unknown" if value == "Unknown" else "Available"
        register_field(key, domain, label, value, "", status, 0.0 if status == "Available" else None)

    def status_badge(status: str) -> str:
        if status == "Available":
            return '<span class="pill good">Available</span>'
        if status == "Unknown":
            return '<span class="pill warn">Unknown</span>'
        return '<span class="pill">Not measured</span>'

    def render_feed_rows(rows: List[Dict[str, Any]], limit: int = 40) -> None:
        for row in rows[:limit]:
            value = row["Status"] if row["Value"] is None else f'{row["Value"]} {row["Unit"]}'.strip()
            html(
                f"""
                <div class="feed-row">
                    <div>
                        <div class="feed-name">{row['Field']}</div>
                        <div class="feed-meta">{row['Domain']} · {value}</div>
                    </div>
                    <div>{status_badge(row['Status'])}</div>
                </div>
                """
            )

    def contribution_bars(domain_rows: List[Dict[str, Any]]) -> None:
        max_value = max(float(row["Total domain contribution"]) for row in domain_rows) if domain_rows else 1.0
        for row in domain_rows:
            pct = int(100 * float(row["Total domain contribution"]) / max_value) if max_value else 0
            html(
                f"""
                <div style="margin-bottom:0.88rem;">
                    <div style="display:flex; justify-content:space-between; gap:1rem; font-size:0.88rem;">
                        <strong style="color:var(--text);">{row['Domain']}</strong>
                        <span style="color:var(--muted);">{row['Total domain contribution']:.2f} pts</span>
                    </div>
                    <div class="bar-outer"><div class="bar-inner" style="width:{pct}%"></div></div>
                </div>
                """
            )

    html(
        f"""
        <div class="app-header">
            <div class="header-row">
                <div>
                    <div class="eyebrow">Clinical Decision Support Workspace</div>
                    <h1 class="page-title">Cardiovascular Health Score</h1>
                    <div class="page-subtitle">
                        Patient-level cardiovascular health assessment with structured clinical inputs,
                        data-quality tracking, domain-level burden decomposition, safety flags, and model auditability.
                    </div>
                    <div class="badge-row">
                        <span class="badge info">{MODEL_VERSION}</span>
                        <span class="badge good">{PROFILE_ID}</span>
                        <span class="badge">{INTERACTION_MODE}</span>
                        <span class="badge warn">Research prototype</span>
                    </div>
                </div>
            </div>
        </div>
        """
    )

    tabs = st.tabs([
        "Patient & Visit",
        "Vitals + Labs",
        "Lifestyle + History",
        "Treatment + Safety",
        "Assessment Review",
        "Model Audit",
        "Export",
    ])

    with tabs[0]:
        left, right = st.columns([1.25, 0.75], gap="large")
        with left:
            html('<div class="section-card">')
            section_header("Patient and visit details", "Core administrative and demographic fields for the active encounter.")
            c1, c2, c3 = st.columns(3)
            with c1:
                patient_id = st.text_input("Patient ID / MRN", value="HHS-DEMO-0001")
            with c2:
                visit_id = st.text_input("Visit ID", value="VISIT-2026-001")
            with c3:
                visit_date = st.date_input("Visit date", value=date.today())
            c4, c5, c6 = st.columns(3)
            with c4:
                age = st.number_input("Age", min_value=18, max_value=110, value=54, step=1)
            with c5:
                sex = st.selectbox("Biological sex", ["Male", "Female", "Intersex / other", "Unknown"], index=0)
            with c6:
                region = st.selectbox("Region profile", ["India default", "South Asia", "Global default", "Custom"], index=0)
            c7, c8 = st.columns(2)
            with c7:
                clinical_setting = st.selectbox("Clinical setting", ["OPD / routine review", "Preventive screening", "Cardiology clinic", "Occupational health", "Research cohort"], index=0)
            with c8:
                reviewed_by = st.text_input("Reviewed by", value="Clinician / Research user")
            st.caption("Age and sex are used as context variables for priors/audit, not as scored burden domains in HHS-v1.2.")
            html("</div>")
        with right:
            html('<div class="section-card">')
            section_header("Encounter summary", "Assessment configuration for this visit.")
            html(f'<div class="feed-row"><div><div class="feed-name">Model version</div><div class="feed-meta">{MODEL_VERSION}</div></div><span class="pill good">Active</span></div>')
            html(f'<div class="feed-row"><div><div class="feed-name">Weight profile</div><div class="feed-meta">{PROFILE_ID}</div></div><span class="pill good">Selected</span></div>')
            html(f'<div class="feed-row"><div><div class="feed-name">Interaction mode</div><div class="feed-meta">{INTERACTION_MODE}</div></div><span class="pill">Default</span></div>')
            html(f'<div class="feed-row"><div><div class="feed-name">Domain weight total</div><div class="feed-meta">{sum(DOMAIN_WEIGHTS.values()):.0f} points</div></div><span class="pill">Main burden</span></div>')
            html("</div>")

    with tabs[1]:
        col_a, col_b = st.columns(2, gap="large")
        with col_a:
            html('<div class="section-card">')
            section_header("Blood pressure and hemodynamic inputs")
            input_group_start("Vital signs", "Unknown and not measured values are handled separately from normal values.")
            number_input_field("sbp", "Blood Pressure", "Systolic BP", 70.0, 260.0, 146.0, 1.0, "mmHg", "Available", 1.0)
            number_input_field("dbp", "Blood Pressure", "Diastolic BP", 40.0, 160.0, 92.0, 1.0, "mmHg", "Available", 1.0)
            number_input_field("resting_hr", "Blood Pressure", "Resting heart rate", 35.0, 180.0, 88.0, 1.0, "bpm", "Available", 0.0)
            yes_no_field("lvh", "Blood Pressure", "LVH present", "Unknown")
            input_group_end()

            section_header("Glucose and diabetes inputs")
            input_group_start("Glycemic markers")
            number_input_field("hba1c", "Glucose", "HbA1c", 3.0, 16.0, 6.8, 0.1, "%", "Available", 2.0)
            number_input_field("fasting_glucose", "Glucose", "Fasting glucose", 40.0, 500.0, 110.0, 1.0, "mg/dL", "Unknown", 1.0)
            yes_no_field("diabetes", "Glucose", "Known diabetes", "Unknown")
            input_group_end()

            section_header("Kidney inputs")
            input_group_start("Renal function and albuminuria")
            number_input_field("egfr", "Kidney", "eGFR", 1.0, 160.0, 82.0, 1.0, "mL/min/1.73m²", "Available", 4.0)
            number_input_field("uacr", "Kidney", "UACR", 0.0, 2000.0, 18.0, 1.0, "mg/g", "Available", 4.0)
            yes_no_field("ckd", "Kidney", "Known CKD", "Unknown")
            input_group_end()
            html("</div>")
        with col_b:
            html('<div class="section-card">')
            section_header("Lipid and atherogenic particle inputs")
            input_group_start("Lipid panel", "Lp(a) unit selection is explicit because mg/dL and nmol/L are not interchangeable.")
            number_input_field("ldl", "Lipids", "LDL-C", 20.0, 350.0, 156.0, 1.0, "mg/dL", "Available", 3.0)
            number_input_field("hdl", "Lipids", "HDL-C", 10.0, 150.0, 42.0, 1.0, "mg/dL", "Unknown", 3.0)
            number_input_field("total_cholesterol", "Lipids", "Total cholesterol", 50.0, 500.0, 224.0, 1.0, "mg/dL", "Unknown", 3.0)
            number_input_field("non_hdl", "Lipids", "Non-HDL-C", 50.0, 400.0, 180.0, 1.0, "mg/dL", "Unknown", 3.0)
            number_input_field("tc_hdl_ratio", "Lipids", "TC/HDL ratio", 1.0, 15.0, 4.8, 0.1, "ratio", "Unknown", 3.0)
            number_input_field("triglycerides", "Lipids", "Triglycerides", 30.0, 1500.0, 180.0, 1.0, "mg/dL", "Unknown", 3.0)
            number_input_field("apob", "Lipids", "ApoB", 20.0, 250.0, 110.0, 1.0, "mg/dL", "Unknown", 3.0)
            lpa_unit = st.selectbox("Lp(a) unit", ["mg/dL", "nmol/L"], index=0)
            number_input_field("lpa", "Lipids", "Lp(a)", 0.0, 500.0, 35.0, 1.0, lpa_unit, "Unknown", 0.0)
            input_group_end()

            section_header("Adiposity inputs")
            input_group_start("Anthropometry")
            number_input_field("bmi", "Adiposity", "BMI", 10.0, 60.0, 27.4, 0.1, "kg/m²", "Available", 2.0)
            number_input_field("waist", "Adiposity", "Waist circumference", 40.0, 180.0, 98.0, 0.5, "cm", "Available", 2.0)
            number_input_field("whr", "Adiposity", "Waist-hip ratio", 0.4, 1.5, 0.94, 0.01, "ratio", "Unknown", 2.0)
            input_group_end()
            html("</div>")

    with tabs[2]:
        col_a, col_b = st.columns(2, gap="large")
        with col_a:
            html('<div class="section-card">')
            section_header("Tobacco exposure")
            input_group_start("Smoking and tobacco history")
            categorical_field("smoking_status", "Tobacco", "Smoking status", ["Never", "Former", "Current", "Current heavy", "Unknown"], "Former")
            number_input_field("pack_years", "Tobacco", "Pack-years", 0.0, 120.0, 14.0, 0.5, "pack-years", "Available", 0.0)
            number_input_field("years_since_quit", "Tobacco", "Years since quit", 0.0, 80.0, 5.0, 0.5, "years", "Available", 0.0)
            yes_no_field("smokeless_tobacco", "Tobacco", "Smokeless tobacco", "Unknown")
            input_group_end()

            section_header("Activity and diet")
            input_group_start("Lifestyle questionnaire", "Activity and diet are separate scored domains in HHS-v1.2.")
            number_input_field("physical_activity", "Activity", "Physical activity", 0.0, 1000.0, 60.0, 5.0, "min/week", "Available", 1.0)
            diet_status = availability("Diet score status", "diet_score_status", "Available")
            if diet_status == "Available":
                c1, c2 = st.columns([1.25, 0.75])
                with c1:
                    diet_score = st.slider("Diet score 0–100", min_value=0, max_value=100, value=62)
                with c2:
                    diet_months = st.number_input("Months old", min_value=0.0, max_value=60.0, value=1.0, step=1.0, key="diet_score_months")
                register_field("diet_score", "Diet", "Diet score", diet_score, "/100", "Available", diet_months)
            else:
                register_field("diet_score", "Diet", "Diet score", None, "/100", diet_status, None)
            input_group_end()
            html("</div>")
        with col_b:
            html('<div class="section-card">')
            section_header("Behavioral risk inputs")
            input_group_start("Sleep, stress, and alcohol", "Behavioral domain contains sleep, alcohol, and stress only. Activity and diet are separate domains.")
            number_input_field("sleep_hours", "Behavioral", "Sleep duration", 0.0, 16.0, 6.2, 0.1, "hours/night", "Available", 1.0)
            number_input_field("alcohol_audit", "Behavioral", "Alcohol AUDIT-C / AUDIT", 0.0, 40.0, 6.0, 1.0, "score", "Available", 1.0)
            number_input_field("stress_score", "Behavioral", "Stress score", 0.0, 10.0, 5.0, 1.0, "score", "Unknown", 1.0)
            input_group_end()

            section_header("Inherited and genetic risk")
            input_group_start("Family history and genetic markers")
            categorical_field("family_history", "Inherited Risk", "Premature family history", ["None", "One first-degree relative", "Multiple first-degree relatives", "Pathogenic mutation", "Unknown"], "One first-degree relative")
            yes_no_field("genetic_mutation", "Inherited Risk", "Known pathogenic cardiovascular mutation", "Unknown")
            number_input_field("prs_percentile", "Inherited Risk", "Polygenic risk score percentile", 0.0, 100.0, 80.0, 1.0, "percentile", "Unknown", 0.0)
            input_group_end()

            section_header("Optional advanced markers")
            input_group_start("Research/advanced review fields", "Recorded for flags/review; not active burden domains in default profile.")
            number_input_field("cac", "Optional Imaging", "Coronary artery calcium score", 0.0, 5000.0, 0.0, 1.0, "Agatston", "Unknown", 12.0)
            number_input_field("hscrp", "Optional Inflammation", "hsCRP", 0.0, 100.0, 2.0, 0.1, "mg/L", "Unknown", 1.0)
            input_group_end()
            html("</div>")

    with tabs[3]:
        col_a, col_b = st.columns(2, gap="large")
        with col_a:
            html('<div class="section-card">')
            section_header("Treatment status")
            input_group_start("Medication and treatment status", "Unknown treatment status uses optimistic/expected/floor states; it is not treated as no treatment.")
            yes_no_field("bp_treatment", "Treatment", "On BP treatment", "Yes")
            yes_no_field("lipid_treatment", "Treatment", "On lipid-lowering treatment", "No")
            yes_no_field("glucose_treatment", "Treatment", "On glucose treatment", "No")
            yes_no_field("kidney_treatment", "Treatment", "On kidney-specific treatment", "Unknown")
            yes_no_field("adherence_concern", "Treatment", "Medication adherence concern", "Unknown")
            input_group_end()
            html("</div>")
        with col_b:
            html('<div class="section-card">')
            section_header("Safety and pathway flags")
            input_group_start("Acute symptoms", "Positive acute symptoms should route the encounter away from routine score interpretation.")
            yes_no_field("chest_pain", "Safety", "Active chest pain", "No")
            yes_no_field("syncope", "Safety", "Syncope", "No")
            yes_no_field("severe_dyspnea", "Safety", "Severe dyspnea", "No")
            yes_no_field("neuro_deficit", "Safety", "Neurologic deficit symptoms", "No")
            input_group_end()
            input_group_start("Known cardiovascular disease")
            yes_no_field("known_mi", "Clinical History", "Known MI", "No")
            yes_no_field("known_stroke", "Clinical History", "Known stroke", "No")
            yes_no_field("known_hf", "Clinical History", "Known heart failure", "No")
            yes_no_field("known_pad", "Clinical History", "Known PAD", "Unknown")
            input_group_end()
            input_group_start("Clinician note")
            clinician_note = st.text_area("Clinical note", value="No active chest pain. Review lipid pathway due to LDL-C value.", height=120)
            input_group_end()
            html("</div>")

    scorer = HHSManualScorer(fields, int(age), str(sex), str(locals().get("lpa_unit", "mg/dL")))
    result = scorer.calculate()

    with tabs[4]:
        m1, m2, m3, m4, m5 = st.columns(5)
        with m1:
            metric_card("HHS Score", f"{result['hhs']} / 100", result["category"], "danger" if any(f.get("suppress_score") for f in result["red_flags"]) else "")
        with m2:
            metric_card("Data Confidence", f"{result['data_confidence']} / 100", result["confidence_label"], "good" if result["data_confidence"] >= 70 else "warn")
        with m3:
            metric_card("Score Status", "Provisional" if result["abstained"] else "Available", "Routine interpretation status")
        with m4:
            metric_card("Score Interval", f"{result['score_interval']['floor']}–{result['score_interval']['optimistic']}", "Floor to optimistic")
        with m5:
            metric_card("Safety Flags", str(len(result["red_flags"])), result["red_flags"][0]["message"] if result["red_flags"] else "No active safety flag", "warn" if result["red_flags"] else "good")

        if result["abstention_reasons"]:
            st.warning("; ".join(result["abstention_reasons"]))

        left, right = st.columns([1.2, 0.8], gap="large")
        with left:
            html('<div class="section-card">')
            section_header("Domain burden contributors", "Ranked contribution to total modeled burden.")
            contribution_bars(result["domain_rows"])
            html("</div>")
        with right:
            html('<div class="section-card">')
            section_header("Clinical review summary", "Concise interpretation for clinician review.")
            if result["red_flags"]:
                for flag in result["red_flags"]:
                    html(f'<div class="review-box warn"><div class="review-title">{flag["flag"].replace("_", " ").title()}</div><div class="review-text">{flag["message"]}</div></div>')
            else:
                html('<div class="review-box good"><div class="review-title">No acute suppression</div><div class="review-text">Routine score interpretation is available for the current encounter.</div></div>')
            if result["recommended_inputs"]:
                rec = result["recommended_inputs"][0]
                html(f'<div class="review-box"><div class="review-title">Recommended next input</div><div class="review-text">{rec["Field"]} may improve the {rec["Domain"]} assessment.</div></div>')
            html(f'<div class="review-box"><div class="review-title">Burden summary</div><div class="review-text">Total burden {result["burden"]["total"]}; main burden {result["burden"]["main"]}; treatment residual {result["burden"]["treatment"]}; interaction {result["burden"]["interaction"]}.</div></div>')
            html("</div>")

        col_a, col_b = st.columns([0.85, 1.15], gap="large")
        with col_a:
            html('<div class="section-card">')
            section_header("Current input feed", "Structured field state for the active encounter.")
            render_feed_rows(feeds, limit=45)
            html("</div>")
        with col_b:
            html('<div class="section-card">')
            section_header("Domain burden table", "Domain-level decomposition.")
            st.dataframe(pd.DataFrame(result["domain_rows"]), use_container_width=True, hide_index=True)
            section_header("Treatment residual")
            if result["treatment_rows"]:
                st.dataframe(pd.DataFrame(result["treatment_rows"]), use_container_width=True, hide_index=True)
            else:
                st.write("No treatment residual contribution in current expected state.")
            section_header("Recommended additional inputs")
            st.dataframe(pd.DataFrame(result["recommended_inputs"]), use_container_width=True, hide_index=True)
            html("</div>")

    with tabs[5]:
        col_a, col_b = st.columns([0.9, 1.1], gap="large")
        with col_a:
            html('<div class="section-card">')
            section_header("Model identity", "Versioning and configuration for auditability.")
            rows = [
                ("Model version", MODEL_VERSION),
                ("Selected profile", PROFILE_ID),
                ("Weight profile type", WEIGHT_PROFILE_TYPE),
                ("Interaction mode", INTERACTION_MODE),
                ("Main burden cap", "75 points"),
                ("Treatment residual cap", "10 points"),
                ("Output type", "0–100 cardiovascular health score"),
                ("Information deficit D", str(result["information_deficit_D"])),
                ("Core freshness C_core", str(result["core_freshness_C_core"])),
            ]
            for k, v in rows:
                html(f'<div class="feed-row"><div class="feed-name">{k}</div><div class="pill">{v}</div></div>')
            html("</div>")
        with col_b:
            html('<div class="section-card">')
            section_header("Weight profile", "Clinician-visible domain weights for the selected profile.")
            weights = pd.DataFrame([{"Domain": k, "Weight": v} for k, v in DOMAIN_WEIGHTS.items()])
            st.dataframe(weights, use_container_width=True, hide_index=True)
            section_header("Formula status")
            st.markdown(
                """
                - Main burden: `sum(W_g * R_g)`
                - Interaction burden: zero in `v1_zero_default`
                - Treatment residual: `rho_g * T_g * (1 - R_g)`
                - Score: `HHS = max(0, 100 - B)`
                - Confidence: `100 * [0.70(1-D) + 0.30*C_core]`
                - Age/sex: context variables, not scored burden domains
                """
            )
            section_header("Modifier and treatment weights")
            modifier_rows = [
                {"Component": "Behavioral: alcohol", "Weight": BEHAVIORAL_COMPONENT_WEIGHTS["alcohol_audit"]},
                {"Component": "Behavioral: sleep", "Weight": BEHAVIORAL_COMPONENT_WEIGHTS["sleep_hours"]},
                {"Component": "Behavioral: stress", "Weight": BEHAVIORAL_COMPONENT_WEIGHTS["stress_score"]},
                {"Component": "Lipid modifier: triglycerides", "Weight": LIPID_MODIFIER_WEIGHTS["triglycerides"]},
                {"Component": "Lipid modifier: Lp(a)", "Weight": LIPID_MODIFIER_WEIGHTS["lpa"]},
                {"Component": "Tobacco modifier: pack-years", "Weight": TOBACCO_MODIFIER_WEIGHTS["pack_years"]},
                {"Component": "Tobacco modifier: smokeless tobacco", "Weight": TOBACCO_MODIFIER_WEIGHTS["smokeless_tobacco"]},
                {"Component": "Inherited modifier: PRS", "Weight": INHERITED_MODIFIER_WEIGHTS["prs_percentile"]},
                {"Component": "Treatment residual: BP", "Weight": TREATMENT_RHO["Blood Pressure"]},
                {"Component": "Treatment residual: Lipids", "Weight": TREATMENT_RHO["Lipids"]},
                {"Component": "Treatment residual: Glucose", "Weight": TREATMENT_RHO["Glucose"]},
                {"Component": "Treatment residual: Kidney", "Weight": TREATMENT_RHO["Kidney"]},
            ]
            st.dataframe(pd.DataFrame(modifier_rows), use_container_width=True, hide_index=True)
            html("</div>")

    with tabs[6]:
        html('<div class="section-card">')
        section_header("Encounter export", "Structured encounter payload for scoring, audit, or report generation.")
        payload = {
            "visit": {
                "patient_id": patient_id,
                "visit_id": visit_id,
                "visit_date": str(visit_date),
                "age": int(age),
                "biological_sex": sex,
                "region_profile": region,
                "clinical_setting": clinical_setting,
                "reviewed_by": reviewed_by,
            },
            "input_feeds": [asdict(rec) for rec in fields.values()],
            "assessment": result,
            "clinician_note": locals().get("clinician_note", ""),
            "lpa_unit": locals().get("lpa_unit", "mg/dL"),
        }
        st.json(payload)
        c1, c2 = st.columns(2)
        with c1:
            st.download_button("Download encounter JSON", data=json.dumps(payload, indent=2, default=str), file_name="hhs_encounter_payload.json", mime="application/json")
        with c2:
            st.button("Finalize encounter", type="primary")
        html("</div>")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run HHS v1.2 restored UI app in CLI mode.")
    parser.add_argument("--sample", action="store_true", help="Run built-in sample payload and print JSON.")
    parser.add_argument("--cli", default=None, help="Path to a JSON payload to score.")
    args = parser.parse_args()

    if args.sample or args.cli:
        if args.cli:
            payload = json.loads(Path(args.cli).read_text(encoding="utf-8"))
        else:
            payload = sample_payload()
        print(json.dumps(run_cli(payload), indent=2, default=str))
        return

    if st is None:
        print("Streamlit not installed. Use --sample/--cli or install streamlit and run: streamlit run hhs_v1_2_restored_ui_app.py")
        return
    run_streamlit_app()


if __name__ == "__main__":
    main()

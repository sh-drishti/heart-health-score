"""
Declarative port of the Streamlit intake form (hhs_v1_2_ui_app.run_streamlit_app).

Served to the frontend via GET /api/intake/schema so field bounds, defaults,
units and labels live in one place instead of being hand-copied into
TypeScript. The root engine file stays untouched; this is a transcription of
its form definitions, not an import of them.

Widget kinds:
    number   value + "months old" pair, gated by an availability select
    slider   same, rendered as a slider (diet score)
    select   categorical, "Unknown" implies status Unknown
    yes_no   select over Unknown / No / Yes
    text     visit metadata, not a scored field
    date     visit metadata

`label` MUST match mapping.HHS_FIELD_METADATA[key]["label"] for fields that
need to survive the payload -> dashboard round trip. See LABEL_TO_KEY in
payload_convert.py.
"""

from typing import Any, Dict, List

AVAILABILITY_OPTIONS = ["Available", "Unknown", "Not measured"]
YES_NO_OPTIONS = ["Unknown", "No", "Yes"]


def _num(
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
    months_max: float = 240.0,
    widget: str = "number",
) -> Dict[str, Any]:
    return {
        "widget": widget,
        "key": key,
        "domain": domain,
        "label": label,
        "unit": unit,
        "min": min_value,
        "max": max_value,
        "default": default,
        "step": step,
        "default_status": default_status,
        "months_default": months_default,
        "months_max": months_max,
    }


def _select(key: str, domain: str, label: str, options: List[str], default: str) -> Dict[str, Any]:
    return {
        "widget": "select",
        "key": key,
        "domain": domain,
        "label": label,
        "unit": "",
        "options": options,
        "default": default,
    }


def _yes_no(key: str, domain: str, label: str, default: str = "Unknown") -> Dict[str, Any]:
    return {
        "widget": "yes_no",
        "key": key,
        "domain": domain,
        "label": label,
        "unit": "",
        "options": YES_NO_OPTIONS,
        "default": default,
    }


# --- Tab 1: Patient & Visit -------------------------------------------------
# Visit metadata. Not scored fields; feeds payload["visit"].

VISIT_FIELDS: List[Dict[str, Any]] = [
    {"widget": "text", "key": "patient_id", "label": "Patient ID / MRN", "default": "HHS-DEMO-0001"},
    {"widget": "text", "key": "visit_id", "label": "Visit ID", "default": "VISIT-2026-001"},
    {"widget": "date", "key": "visit_date", "label": "Visit date", "default": None},
    {"widget": "number_plain", "key": "age", "label": "Age", "min": 18, "max": 110, "default": 54, "step": 1},
    {
        "widget": "select_plain",
        "key": "biological_sex",
        "label": "Biological sex",
        "options": ["Male", "Female", "Intersex / other", "Unknown"],
        "default": "Male",
    },
    {
        "widget": "select_plain",
        "key": "region_profile",
        "label": "Region profile",
        "options": ["India default", "South Asia", "Global default", "Custom"],
        "default": "India default",
    },
    {
        "widget": "select_plain",
        "key": "clinical_setting",
        "label": "Clinical setting",
        "options": [
            "OPD / routine review",
            "Preventive screening",
            "Cardiology clinic",
            "Occupational health",
            "Research cohort",
        ],
        "default": "OPD / routine review",
    },
    {"widget": "text", "key": "reviewed_by", "label": "Reviewed by", "default": "Clinician / Research user"},
]

VISIT_NOTE = (
    "Age and sex are used as context variables for priors/audit, "
    "not as scored burden domains in HHS-v1.2."
)


# --- Tabs 2-4: the 48 scored input feeds ------------------------------------

TABS: List[Dict[str, Any]] = [
    {
        "id": "vitals",
        "title": "Vitals + Labs",
        "columns": [
            [
                {
                    "section": "Blood pressure and hemodynamic inputs",
                    "groups": [
                        {
                            "title": "Vital signs",
                            "note": "Unknown and not measured values are handled separately from normal values.",
                            "fields": [
                                _num("sbp", "Blood Pressure", "Systolic BP", 70.0, 260.0, 146.0, 1.0, "mmHg", "Available", 1.0),
                                _num("dbp", "Blood Pressure", "Diastolic BP", 40.0, 160.0, 92.0, 1.0, "mmHg", "Available", 1.0),
                                _num("resting_hr", "Blood Pressure", "Resting heart rate", 35.0, 180.0, 88.0, 1.0, "bpm", "Available", 0.0),
                                _yes_no("lvh", "Blood Pressure", "LVH present", "Unknown"),
                            ],
                        }
                    ],
                },
                {
                    "section": "Glucose and diabetes inputs",
                    "groups": [
                        {
                            "title": "Glycemic markers",
                            "note": None,
                            "fields": [
                                _num("hba1c", "Glucose", "HbA1c", 3.0, 16.0, 6.8, 0.1, "%", "Available", 2.0),
                                _num("fasting_glucose", "Glucose", "Fasting glucose", 40.0, 500.0, 110.0, 1.0, "mg/dL", "Unknown", 1.0),
                                _yes_no("diabetes", "Glucose", "Known diabetes", "Unknown"),
                            ],
                        }
                    ],
                },
                {
                    "section": "Kidney inputs",
                    "groups": [
                        {
                            "title": "Renal function and albuminuria",
                            "note": None,
                            "fields": [
                                _num("egfr", "Kidney", "eGFR", 1.0, 160.0, 82.0, 1.0, "mL/min/1.73m²", "Available", 4.0),
                                _num("uacr", "Kidney", "UACR", 0.0, 2000.0, 18.0, 1.0, "mg/g", "Available", 4.0),
                                _yes_no("ckd", "Kidney", "Known CKD", "Unknown"),
                            ],
                        }
                    ],
                },
            ],
            [
                {
                    "section": "Lipid and atherogenic particle inputs",
                    "groups": [
                        {
                            "title": "Lipid panel",
                            "note": "Lp(a) unit selection is explicit because mg/dL and nmol/L are not interchangeable.",
                            "fields": [
                                _num("ldl", "Lipids", "LDL-C", 20.0, 350.0, 156.0, 1.0, "mg/dL", "Available", 3.0),
                                _num("hdl", "Lipids", "HDL-C", 10.0, 150.0, 42.0, 1.0, "mg/dL", "Unknown", 3.0),
                                _num("total_cholesterol", "Lipids", "Total cholesterol", 50.0, 500.0, 224.0, 1.0, "mg/dL", "Unknown", 3.0),
                                _num("non_hdl", "Lipids", "Non-HDL-C", 50.0, 400.0, 180.0, 1.0, "mg/dL", "Unknown", 3.0),
                                _num("tc_hdl_ratio", "Lipids", "TC/HDL ratio", 1.0, 15.0, 4.8, 0.1, "ratio", "Unknown", 3.0),
                                _num("triglycerides", "Lipids", "Triglycerides", 30.0, 1500.0, 180.0, 1.0, "mg/dL", "Unknown", 3.0),
                                _num("apob", "Lipids", "ApoB", 20.0, 250.0, 110.0, 1.0, "mg/dL", "Unknown", 3.0),
                                {
                                    "widget": "lpa_unit",
                                    "key": "lpa_unit",
                                    "label": "Lp(a) unit",
                                    "options": ["mg/dL", "nmol/L"],
                                    "default": "mg/dL",
                                },
                                # unit is overridden at render time by the lpa_unit select
                                _num("lpa", "Lipids", "Lp(a)", 0.0, 500.0, 35.0, 1.0, "mg/dL", "Unknown", 0.0),
                            ],
                        }
                    ],
                },
                {
                    "section": "Adiposity inputs",
                    "groups": [
                        {
                            "title": "Anthropometry",
                            "note": None,
                            "fields": [
                                _num("bmi", "Adiposity", "BMI", 10.0, 60.0, 27.4, 0.1, "kg/m²", "Available", 2.0),
                                _num("waist", "Adiposity", "Waist circumference", 40.0, 180.0, 98.0, 0.5, "cm", "Available", 2.0),
                                _num("whr", "Adiposity", "Waist-hip ratio", 0.4, 1.5, 0.94, 0.01, "ratio", "Unknown", 2.0),
                            ],
                        }
                    ],
                },
            ],
        ],
    },
    {
        "id": "lifestyle",
        "title": "Lifestyle + History",
        "columns": [
            [
                {
                    "section": "Tobacco exposure",
                    "groups": [
                        {
                            "title": "Smoking and tobacco history",
                            "note": None,
                            "fields": [
                                _select(
                                    "smoking_status",
                                    "Tobacco",
                                    "Smoking status",
                                    ["Never", "Former", "Current", "Current heavy", "Unknown"],
                                    "Former",
                                ),
                                _num("pack_years", "Tobacco", "Pack-years", 0.0, 120.0, 14.0, 0.5, "pack-years", "Available", 0.0),
                                _num("years_since_quit", "Tobacco", "Years since quit", 0.0, 80.0, 5.0, 0.5, "years", "Available", 0.0),
                                _yes_no("smokeless_tobacco", "Tobacco", "Smokeless tobacco", "Unknown"),
                            ],
                        }
                    ],
                },
                {
                    "section": "Activity and diet",
                    "groups": [
                        {
                            "title": "Lifestyle questionnaire",
                            "note": "Activity and diet are separate scored domains in HHS-v1.2.",
                            "fields": [
                                _num("physical_activity", "Activity", "Physical activity", 0.0, 1000.0, 60.0, 5.0, "min/week", "Available", 1.0),
                                _num(
                                    "diet_score", "Diet", "Diet score", 0.0, 100.0, 62.0, 1.0, "/100",
                                    "Available", 1.0, months_max=60.0, widget="slider",
                                ),
                            ],
                        }
                    ],
                },
            ],
            [
                {
                    "section": "Behavioral risk inputs",
                    "groups": [
                        {
                            "title": "Sleep, stress, and alcohol",
                            "note": "Behavioral domain contains sleep, alcohol, and stress only. Activity and diet are separate domains.",
                            "fields": [
                                _num("sleep_hours", "Behavioral", "Sleep duration", 0.0, 16.0, 6.2, 0.1, "hours/night", "Available", 1.0),
                                _num("alcohol_audit", "Behavioral", "Alcohol AUDIT-C / AUDIT", 0.0, 40.0, 6.0, 1.0, "score", "Available", 1.0),
                                _num("stress_score", "Behavioral", "Stress score", 0.0, 10.0, 5.0, 1.0, "score", "Unknown", 1.0),
                            ],
                        }
                    ],
                },
                {
                    "section": "Inherited and genetic risk",
                    "groups": [
                        {
                            "title": "Family history and genetic markers",
                            "note": None,
                            "fields": [
                                _select(
                                    "family_history",
                                    "Inherited Risk",
                                    "Premature family history",
                                    [
                                        "None",
                                        "One first-degree relative",
                                        "Multiple first-degree relatives",
                                        "Pathogenic mutation",
                                        "Unknown",
                                    ],
                                    "One first-degree relative",
                                ),
                                _yes_no("genetic_mutation", "Inherited Risk", "Known pathogenic cardiovascular mutation", "Unknown"),
                                _num("prs_percentile", "Inherited Risk", "Polygenic risk score percentile", 0.0, 100.0, 80.0, 1.0, "percentile", "Unknown", 0.0),
                            ],
                        }
                    ],
                },
                {
                    "section": "Optional advanced markers",
                    "groups": [
                        {
                            "title": "Research/advanced review fields",
                            "note": "Recorded for flags/review; not active burden domains in default profile.",
                            "fields": [
                                _num("cac", "Optional Imaging", "Coronary artery calcium score", 0.0, 5000.0, 0.0, 1.0, "Agatston", "Unknown", 12.0),
                                _num("hscrp", "Optional Inflammation", "hsCRP", 0.0, 100.0, 2.0, 0.1, "mg/L", "Unknown", 1.0),
                            ],
                        }
                    ],
                },
            ],
        ],
    },
    {
        "id": "treatment",
        "title": "Treatment + Safety",
        "columns": [
            [
                {
                    "section": "Treatment status",
                    "groups": [
                        {
                            "title": "Medication and treatment status",
                            "note": "Unknown treatment status uses optimistic/expected/floor states; it is not treated as no treatment.",
                            "fields": [
                                _yes_no("bp_treatment", "Treatment", "On BP treatment", "Yes"),
                                _yes_no("lipid_treatment", "Treatment", "On lipid-lowering treatment", "No"),
                                _yes_no("glucose_treatment", "Treatment", "On glucose treatment", "No"),
                                _yes_no("kidney_treatment", "Treatment", "On kidney-specific treatment", "Unknown"),
                                _yes_no("adherence_concern", "Treatment", "Medication adherence concern", "Unknown"),
                            ],
                        }
                    ],
                }
            ],
            [
                {
                    "section": "Safety and pathway flags",
                    "groups": [
                        {
                            "title": "Acute symptoms",
                            "note": "Positive acute symptoms should route the encounter away from routine score interpretation.",
                            "fields": [
                                _yes_no("chest_pain", "Safety", "Active chest pain", "No"),
                                _yes_no("syncope", "Safety", "Syncope", "No"),
                                _yes_no("severe_dyspnea", "Safety", "Severe dyspnea", "No"),
                                _yes_no("neuro_deficit", "Safety", "Neurologic deficit symptoms", "No"),
                            ],
                        },
                        {
                            "title": "Known cardiovascular disease",
                            "note": None,
                            "fields": [
                                _yes_no("known_mi", "Clinical History", "Known MI", "No"),
                                _yes_no("known_stroke", "Clinical History", "Known stroke", "No"),
                                _yes_no("known_hf", "Clinical History", "Known heart failure", "No"),
                                _yes_no("known_pad", "Clinical History", "Known PAD", "Unknown"),
                            ],
                        },
                    ],
                }
            ],
        ],
    },
]

CLINICIAN_NOTE_DEFAULT = "No active chest pain. Review lipid pathway due to LDL-C value."


def all_fields() -> Dict[str, Dict[str, Any]]:
    """Flat {key: field_def} over every scored input feed."""

    out: Dict[str, Dict[str, Any]] = {}
    for tab in TABS:
        for column in tab["columns"]:
            for section in column:
                for group in section["groups"]:
                    for field in group["fields"]:
                        if field["widget"] == "lpa_unit":
                            continue
                        out[field["key"]] = field
    return out


def schema() -> Dict[str, Any]:
    """Full form schema for the frontend."""

    return {
        "visit_fields": VISIT_FIELDS,
        "visit_note": VISIT_NOTE,
        "tabs": TABS,
        "availability_options": AVAILABILITY_OPTIONS,
        "yes_no_options": YES_NO_OPTIONS,
        "clinician_note_default": CLINICIAN_NOTE_DEFAULT,
    }

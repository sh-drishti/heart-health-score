# ==============================
# Context Variables
# ==============================

CONTEXT_VARIABLES = [
    "age",
    "biological_sex"
]

# ==============================
# Main HHS Domains
# ==============================

DOMAINS = {

    "Lipid / Atherogenic Particle": {
        "weight": 13,
        "features": [
            "total_cholesterol",
            "ldl",
            "hdl",
            "non_hdl",
            "triglycerides",
            "tc_hdl_ratio",
            "apob",
            "lpa"
        ]
    },

    "Blood Pressure / Hemodynamic": {
        "weight": 10,
        "features": [
            "sbp",
            "dbp",
            "lvh",
            "resting_hr"
        ]
    },

    "Tobacco": {
        "weight": 9,
        "features": [
            "smoking_status",
            "pack_years",
            "years_since_quit",
            "smokeless_tobacco"
        ]
    },

    "Glucose / Diabetes": {
        "weight": 8,
        "features": [
            "fasting_glucose",
            "hba1c",
            "diabetes"
        ]
    },

    "Adiposity": {
        "weight": 8,
        "features": [
            "bmi",
            "waist",
            "whr"
        ]
    },

    "Inherited Risk": {
        "weight": 6,
        "features": [
            "family_history"
        ]
    },

    "Kidney / Vascular Damage": {
        "weight": 7,
        "features": [
            "egfr",
            "uacr",
            "ckd"
        ]
    },

    "Physical Activity": {
        "weight": 5,
        "features": [
            "physical_activity"
        ]
    },

    "Diet / Nutrition": {
        "weight": 5,
        "features": [
            "diet_score"
        ]
    },

    "Behavioral Risk": {
        "weight": 4,
        "features": [
            "alcohol_audit",
            "sleep_hours",
            "stress_score"
        ]
    }
}

OFFICIAL_DOMAIN_MAPPING = {
    "Lipid / Atherogenic Particle": "Lipids",
    "Blood Pressure / Hemodynamic": "Blood Pressure",
    "Glucose / Diabetes": "Glucose",
    "Kidney / Vascular Damage": "Kidney",
    "Adiposity": "Adiposity",
    "Tobacco": "Tobacco",
    "Physical Activity": "Activity",
    "Diet / Nutrition": "Diet",
    "Behavioral Risk": "Behavioral",
    "Inherited Risk": "Inherited Risk"
}

SECTION_FIELDS = {
    "Treatment Status": [
        ("BP Treatment", "bp_treatment"),
        ("Lipid Treatment", "lipid_treatment"),
        ("Glucose Treatment", "glucose_treatment"),
        ("Kidney Treatment", "kidney_treatment"),
        ("Medication Adherence", "adherence_concern")
    ],

    "Clinical History": [
        ("Known MI", "known_mi"),
        ("Known Stroke", "known_stroke"),
        ("Known Heart Failure", "known_hf"),
        ("Known PAD", "known_pad")
    ],

    "Safety Alerts": [
        ("Chest Pain", "chest_pain"),
        ("Syncope", "syncope"),
        ("Severe Dyspnea", "severe_dyspnea"),
        ("Neurologic Deficit", "neuro_deficit")
    ],

    "Optional Advanced Markers": [
        ("CAC", "cac"),
        ("hsCRP", "hscrp"),
        ("Genetic Mutation", "genetic_mutation"),
        ("PRS Percentile", "prs_percentile")
    ]
}
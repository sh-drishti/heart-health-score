# ==============================
# Context Variables
# ==============================

CONTEXT_VARIABLES = [
    "Age",
    "Biological_Sex"
]

# ==============================
# Main HHS Domains
# ==============================

DOMAINS = {

    "Lipid / Atherogenic Particle": {
        "weight": 13,
        "features": [
            "Total_Cholesterol",
            "LDL_C",
            "HDL_C",
            "Non_HDL_C",
            "Triglycerides",
            "TC_HDL_Ratio",
            "ApoB",
            "Lp_a"
        ]
    },

    "Blood Pressure / Hemodynamic": {
        "weight": 10,
        "features": [
            "Systolic_BP",
            "Diastolic_BP",
            "LVH",
            "Resting_Heart_Rate"
        ]
    },

    "Tobacco": {
        "weight": 9,
        "features": [
            "Smoking_Status",
            "Pack_Years",
            "Years_Since_Quit",
            "Smokeless_Tobacco"
        ]
    },

    "Glucose / Diabetes": {
        "weight": 8,
        "features": [
            "Fasting_Glucose",
            "HbA1c",
            "Diabetes_Status"
        ]
    },

    "Adiposity": {
        "weight": 8,
        "features": [
            "BMI",
            "Waist_Circumference",
            "Waist_Hip_Ratio"
        ]
    },

    "Inherited Risk": {
        "weight": 6,
        "features": [
            "Family_History_CVD",
            "Genetic_Mutation",
            "PRS_Percentile"
        ]
    },

    "Kidney / Vascular Damage": {
        "weight": 7,
        "features": [
            "eGFR",
            "UACR",
            "CKD"
        ]
    },

    "Physical Activity": {
        "weight": 5,
        "features": [
            "Physical_Activity"
        ]
    },

    "Diet / Nutrition": {
        "weight": 5,
        "features": [
            "Dietary_Quality"
        ]
    },

    "Behavioral Risk": {
        "weight": 4,
        "features": [
            "Alcohol",
            "Sleep_Duration",
            "Perceived_Stress"
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
        ("BP Treatment", "BP_Treatment"),
        ("Lipid Treatment", "Lipid_Treatment"),
        ("Glucose Treatment", "Glucose_Treatment"),
        ("Kidney Treatment", "Kidney_Treatment"),
        ("Medication Adherence", "Medication_Adherence_Concern")
    ],

    "Clinical History": [
        ("Known MI", "Known_MI"),
        ("Known Stroke", "Known_Stroke"),
        ("Known Heart Failure", "Known_Heart_Failure"),
        ("Known PAD", "Known_PAD")
    ],

    "Safety Alerts": [
        ("Chest Pain", "Chest_Pain"),
        ("Syncope", "Syncope"),
        ("Severe Dyspnea", "Severe_Dyspnea"),
        ("Neurologic Deficit", "Neurologic_Deficit")
    ],

    "Optional Advanced Markers": [
        ("CAC", "CAC"),
        ("hsCRP", "hsCRP"),
        ("Genetic Mutation", "Genetic_Mutation"),
        ("PRS Percentile", "PRS_Percentile")
    ]
}
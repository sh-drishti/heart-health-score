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
            "Pulse_Pressure",
            "LVH"

        ]

    },

    "Tobacco": {

        "weight": 9,

        "features": [

            "Smoking_Status"

        ]

    },

    "Glucose / Diabetes": {

        "weight": 8,

        "features": [

            "Fasting_Glucose",
            "HbA1c",
            "Diabetes_Status",
            "HOMA_IR"

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

            "Family_History_CVD"

        ]

    },

    "Kidney / Vascular Damage": {

        "weight": 7,

        "features": [

            "eGFR",
            "UACR"

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

# ==============================
# Optional Clinical Modules
# ==============================

OPTIONAL_MODULES = {

    "Inflammation": [

        "hs_CRP",
        "Homocysteine",
        "Fibrinogen"

    ],

    "Cardiac Biomarkers": [

        "NT_proBNP",
        "hs_Troponin"

    ],

    "Imaging": [

        "CAC_Score",
        "Carotid_IMT"

    ]

}
DOMAINS = {

    "Demographic": {
        "weight": 0,
        "features": [
            "Age",
            "Biological_Sex"
        ]
    },

    "Blood Pressure": {
        "weight": 10,
        "features": [
            "Systolic_BP",
            "Diastolic_BP"
        ]
    },

    "Lipid": {
        "weight": 13,
        "features": [
            "Total_Cholesterol",
            "LDL",
            "HDL",
            "Triglycerides",
            "ApoB"
        ]
    },

    "Glycaemic": {
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

    "Inflammation / Biomarkers": {
        "weight": 6,
        "features": [
            "hs_CRP",
            "NT_proBNP",
            "hs_Troponin_I",
            "Lp_a",
            "IL_6"
        ]
    },

    "Lifestyle": {
        "weight": 5,
        "features": [
            "Smoking_Status",
            "Alcohol",
            "Physical_Activity",
            "Sleep_Duration",
            "Dietary_Quality"
        ]
    },

    "Psychosocial": {
        "weight": 4,
        "features": [
            "Perceived_Stress",
            "PHQ9"
        ]
    },

    "Renal": {
        "weight": 7,
        "features": [
            "eGFR"
        ]
    },

    "Clinical": {
        "weight": 6,
        "features": [
            "Family_History_CVD",
            "Atrial_Fibrillation",
            "ECG_Abnormalities",
            "Prior_ASCVD",
            "SES_Deprivation_Index"
        ]
    }

}
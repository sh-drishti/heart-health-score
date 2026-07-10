FIELD_MAPPING = {

    # ----------------------------
    # Blood Pressure
    # ----------------------------

    "Systolic_BP": "sbp",
    "Diastolic_BP": "dbp",
    "Resting_Heart_Rate": "resting_hr",
    "LVH": "lvh",

    # ----------------------------
    # Glucose
    # ----------------------------

    "HbA1c": "hba1c",
    "Fasting_Glucose": "fasting_glucose",
    "Diabetes_Status": "diabetes",

    # ----------------------------
    # Kidney
    # ----------------------------

    "eGFR": "egfr",
    "UACR": "uacr",
    "CKD": "ckd",

    # ----------------------------
    # Lipids
    # ----------------------------

    "LDL_C": "ldl",
    "HDL_C": "hdl",
    "Total_Cholesterol": "total_cholesterol",
    "Non_HDL_C": "non_hdl",
    "TC_HDL_Ratio": "tc_hdl_ratio",
    "Triglycerides": "triglycerides",
    "ApoB": "apob",
    "Lp_a": "lpa",

    # ----------------------------
    # Adiposity
    # ----------------------------

    "BMI": "bmi",
    "Waist_Circumference": "waist",
    "Waist_Hip_Ratio": "whr",

    # ----------------------------
    # Tobacco
    # ----------------------------

    "Smoking_Status": "smoking_status",
    "Pack_Years": "pack_years",
    "Years_Since_Quit": "years_since_quit",
    "Smokeless_Tobacco": "smokeless_tobacco",

    # ----------------------------
    # Lifestyle
    # ----------------------------

    "Physical_Activity": "physical_activity",
    "Dietary_Quality": "diet_score",
    "Sleep_Duration": "sleep_hours",
    "Alcohol": "alcohol_audit",
    "Perceived_Stress": "stress_score",

    # ----------------------------
    # Inherited Risk
    # ----------------------------

    "Family_History_CVD": "family_history",
    "Genetic_Mutation": "genetic_mutation",
    "PRS_Percentile": "prs_percentile",

    # ----------------------------
    # Treatments
    # ----------------------------

    "BP_Treatment": "bp_treatment",
    "Lipid_Treatment": "lipid_treatment",
    "Glucose_Treatment": "glucose_treatment",
    "Kidney_Treatment": "kidney_treatment",
    "Medication_Adherence_Concern": "adherence_concern",

    # ----------------------------
    # Red Flags
    # ----------------------------

    "Chest_Pain": "chest_pain",
    "Syncope": "syncope",
    "Severe_Dyspnea": "severe_dyspnea",
    "Neurologic_Deficit": "neuro_deficit",
    "Known_MI": "known_mi",
    "Known_Stroke": "known_stroke",
    "Known_Heart_Failure": "known_hf",
    "Known_PAD": "known_pad",

    # ----------------------------
    # Additional Risk Markers
    # ----------------------------

    "CAC": "cac",
    "hsCRP": "hscrp"

}

HHS_FIELD_METADATA = {
    "sbp": {"domain": "Blood Pressure", "label": "Systolic BP", "unit": "mmHg"},
    "dbp": {"domain": "Blood Pressure", "label": "Diastolic BP", "unit": "mmHg"},
    "lvh": {"domain": "Blood Pressure", "label": "LVH present", "unit": ""},

    "ldl": {"domain": "Lipids", "label": "LDL-C", "unit": "mg/dL"},
    "non_hdl": {"domain": "Lipids", "label": "Non-HDL-C", "unit": "mg/dL"},
    "tc_hdl_ratio": {"domain": "Lipids", "label": "TC/HDL ratio", "unit": "ratio"},
    "apob": {"domain": "Lipids", "label": "ApoB", "unit": "mg/dL"},
    "triglycerides": {"domain": "Lipids", "label": "Triglycerides", "unit": "mg/dL"},
    "lpa": {"domain": "Lipids", "label": "Lp(a)", "unit": "mg/dL or nmol/L"},

    "hba1c": {"domain": "Glucose", "label": "HbA1c", "unit": "%"},
    "fasting_glucose": {"domain": "Glucose", "label": "Fasting glucose", "unit": "mg/dL"},
    "diabetes": {"domain": "Glucose", "label": "Known diabetes", "unit": ""},

    "egfr": {"domain": "Kidney", "label": "eGFR", "unit": "mL/min/1.73m^2"},
    "uacr": {"domain": "Kidney", "label": "UACR", "unit": "mg/g"},
    "ckd": {"domain": "Kidney", "label": "Known CKD", "unit": ""},

    "bmi": {"domain": "Adiposity", "label": "BMI", "unit": "kg/m^2"},
    "waist": {"domain": "Adiposity", "label": "Waist circumference", "unit": "cm"},
    "whr": {"domain": "Adiposity", "label": "Waist-hip ratio", "unit": "ratio"},

    "smoking_status": {"domain": "Tobacco", "label": "Smoking status", "unit": ""},
    "pack_years": {"domain": "Tobacco", "label": "Pack-years", "unit": "pack-years"},
    "years_since_quit": {"domain": "Tobacco", "label": "Years since quit", "unit": "years"},
    "smokeless_tobacco": {"domain": "Tobacco", "label": "Smokeless tobacco", "unit": ""},

    "physical_activity": {"domain": "Activity", "label": "Physical activity", "unit": "min/week"},
    "diet_score": {"domain": "Diet", "label": "Diet score", "unit": "/100"},

    "sleep_hours": {"domain": "Behavioral", "label": "Sleep duration", "unit": "hours/night"},
    "alcohol_audit": {"domain": "Behavioral", "label": "Alcohol AUDIT-C / AUDIT", "unit": "score"},
    "stress_score": {"domain": "Behavioral", "label": "Stress score", "unit": "score"},

    "family_history": {"domain": "Inherited Risk", "label": "Premature family history", "unit": ""},
    "genetic_mutation": {"domain": "Inherited Risk", "label": "Known pathogenic cardiovascular mutation", "unit": ""},
    "prs_percentile": {"domain": "Inherited Risk", "label": "Polygenic risk score percentile", "unit": "percentile"},

    "bp_treatment": {"domain": "Treatment", "label": "On BP treatment", "unit": ""},
    "lipid_treatment": {"domain": "Treatment", "label": "On lipid-lowering treatment", "unit": ""},
    "glucose_treatment": {"domain": "Treatment", "label": "On glucose treatment", "unit": ""},
    "kidney_treatment": {"domain": "Treatment", "label": "On kidney-specific treatment", "unit": ""},

    "cac": {"domain": "Optional Imaging", "label": "Coronary artery calcium score", "unit": "Agatston"},

    "chest_pain": {"domain": "Safety", "label": "Active chest pain", "unit": ""},
    "syncope": {"domain": "Safety", "label": "Syncope", "unit": ""},
    "severe_dyspnea": {"domain": "Safety", "label": "Severe dyspnea", "unit": ""},
    "neuro_deficit": {"domain": "Safety", "label": "Neurologic deficit symptoms", "unit": ""},

    "known_mi": {"domain": "Clinical History", "label": "Known MI", "unit": ""},
    "known_stroke": {"domain": "Clinical History", "label": "Known stroke", "unit": ""},
    "known_hf": {"domain": "Clinical History", "label": "Known heart failure", "unit": ""},
    "known_pad": {"domain": "Clinical History", "label": "Known PAD", "unit": ""},
}
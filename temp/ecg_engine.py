import json
import os
import joblib
import pandas as pd

# =========================================================
# CONFIG
# =========================================================

MODEL_PATH = os.path.join(
    "ecg_models",
    "ecg_v1_hr500_official_selected.joblib"
)

METADATA_PATH = os.path.join(
    "ecg_models",
    "ecg_v1_hr500_official_metadata.json"
)


# =========================================================
# LOAD MODEL + METADATA
# =========================================================

model=joblib.load(MODEL_PATH)
with open(METADATA_PATH, "r", encoding="utf-8") as f:
    metadata=json.load(f)

FEATURES = metadata["features"]
TARGETS = metadata["targets"]
THRESHOLDS = metadata["thresholds"]
MODEL_VERSION = metadata["model_version"]


# =========================================================
# ECG PREDICTION FUNCTION
# =========================================================

def predict_ecg(ecg_input:dict)->dict:
    """
    Predict PTB-XL ECG superclasses from five ECG measurements.
    INPUT: HR, PR, QRS, QT, QTC
    OUTPUT: Structured JSON- compatible dictionary
    """
    missing_features=[feature for feature in FEATURES if feature not in ecg_input]
    if missing_features:
        raise ValueError(f"Missing ECG Features: {missing_features}")
    
    input_df=pd.DataFrame([[ecg_input[feature] for feature in FEATURES]], columns=FEATURES)
    probabilities=model.predict_proba(input_df)
    
    predictions={}
    abnormalities=[]
    
    for index,target in enumerate(TARGETS):
        probability=float(probabilities[index][0][1])
        threshold=float(THRESHOLDS[target])
        is_positive=(probability>=threshold)
        predictions[target] = {
            "probability": round(probability, 4),
            "threshold": round(threshold, 4),
            "positive": bool(is_positive)
        }
        if is_positive:
            if target!="NORM":
                abnormalities.append({
                    "type": target,
                    "probability":round(probability,4)
                })
    if abnormalities:
        status="abnormal"
    else:
        status="normal"

    result={
        "model_version": MODEL_VERSION,
        "status": status,
        "input_features": {
            feature: ecg_input[feature]
            for feature in FEATURES
        },
        "predictions": predictions,
        "abnormalities": abnormalities
    }
    return result

if __name__ == "__main__":

    test_ecg = {
        "heart_rate": 103,
        "pr_interval": 138,
        "qrs_duration": 80,
        "qt_interval": 323,
        "qtc_interval": 423
    }

    result = predict_ecg(test_ecg)

    print(
        json.dumps(
            result,
            indent=4
        )
    )

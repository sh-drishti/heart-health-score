import streamlit as st
import pandas as pd

from streamlit_extras.stylable_container import stylable_container
from severity import calculate_patient_severity
from ui import show_domain_summary
from navigation import patient_navigation
from config import DOMAINS, CONTEXT_VARIABLES, OPTIONAL_MODULES
from hhs_calc import calculate_hhs

st.set_page_config(
    page_title="Healthy Heart Score Dashboard",
    layout="wide"
)

st.title("Healthy Heart Score Dashboard")

df = pd.read_csv("data/cardio_hhs.csv", keep_default_na=False)

patient_ids = df["Patient_ID"].tolist()

with st.form("patient_search"):

    col1, col2 = st.columns([8,1])

    with col1:

        search = st.text_input(
            "Search Patient",
            placeholder="e.g. P001"
        )

    with col2:

        st.write("")
        st.write("")

        submitted = st.form_submit_button(
            "Go",
            use_container_width=True
        )

if submitted:

    patient_id = search.strip()

    if patient_id in patient_ids:

        st.session_state.selected_patient = patient_id
        st.session_state.current_start = patient_id

        st.rerun()

    else:

        st.error("Patient not found.")

selected_patient = patient_navigation(patient_ids)
patient = df[df["Patient_ID"] == selected_patient].iloc[0]
patient_data = calculate_patient_severity(patient)
hhs_result = calculate_hhs(patient_data)

st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Patient ID",
        patient["Patient_ID"]
    )

with col2:
    st.metric(
        "Age",
        patient["Age"]
    )

with col3:
    sex = "Male" if patient["Biological_Sex"] == "Male" else "Female"

    st.metric(
        "Biological Sex",
        sex
    )

st.markdown("---")

tab1, tab2, tab3 = st.tabs(
    [
        "Domain Summary",
        "All Parameters",
        "Doctor HHS"
    ]
)

with tab1:

    show_domain_summary(
        patient_data
    )

with tab2:

    table = []

    severity_map = {
        0: "🟩 Normal",
        0.5: "🟨 Borderline",
        1: "🟥 Risk"
    }

    for domain, info in DOMAINS.items():

        for feature in info["features"]:

            if feature not in patient_data:
                continue

            severity = patient_data[feature]["severity"]

            table.append({

                "Domain": domain,

                "Parameter": patient_data[feature]["excel_name"],

                "Value": patient_data[feature]["value"],

                "Severity": severity_map[severity],

                "Severity_Score": severity,

                "Domain_Weight": info["weight"]

            })

    table = pd.DataFrame(table)

    table = table.sort_values(

        by=["Severity_Score", "Domain_Weight"],

        ascending=[False, False]

    )

    table = table.drop(

        columns=["Severity_Score", "Domain_Weight"]

    )

    st.dataframe(

        table,

        use_container_width=True,

        hide_index=True

    )
    
with tab3:

    st.subheader("Calculated Healthy Heart Score")

    col1, col2 = st.columns([1, 1])

    with col1:

        st.metric(

            "Calculated HHS",

            f"{hhs_result['hhs']}"

        )

    with col2:

        category = hhs_result["category"]

        if category == "Healthy":
            st.success(f"🟢 {category}")

        elif category == "Borderline":
            st.warning(f"🟡 {category}")

        else:
            st.error(f"🔴 {category}")

    st.markdown("---")

    agree = st.radio(

        "Do you agree with the predicted category?",

        ["Yes", "No"]

    )

    expected_category = ""

    if agree == "No":

        expected_category = st.radio(

            "Expected Category",

            [

                "Healthy",

                "Borderline",

                "High Risk"

            ]

        )

    remarks = st.text_area(

        "Doctor Remarks"

    )

    if st.button("Save Assessment"):

        new_row = pd.DataFrame([{

            "Patient_ID": patient["Patient_ID"],

            "Calculated_HHS": hhs_result["hhs"],

            "Predicted_Category": hhs_result["category"],

            "Doctor_Agreement": agree,

            "Doctor_Category": expected_category if agree == "No" else hhs_result["category"],

            "Remarks": remarks

        }])

        try:

            saved = pd.read_csv("saved_hhs.csv")

            if patient["Patient_ID"] in saved["Patient_ID"].values:

                saved.loc[

                    saved["Patient_ID"] == patient["Patient_ID"],

                    [

                        "Calculated_HHS",

                        "Predicted_Category",

                        "Doctor_Agreement",

                        "Doctor_Category",

                        "Remarks"

                    ]

                ] = [

                    hhs_result["hhs"],

                    hhs_result["category"],

                    agree,

                    expected_category if agree == "No" else hhs_result["category"],

                    remarks

                ]

            else:

                saved = pd.concat(

                    [saved, new_row],

                    ignore_index=True

                )

        except FileNotFoundError:

            saved = new_row

        saved.to_csv(

            "saved_hhs.csv",

            index=False

        )

        st.success("Assessment saved successfully!")
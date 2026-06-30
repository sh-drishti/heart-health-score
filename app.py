import streamlit as st
import pandas as pd

from severity import calculate_patient_severity
from ui import show_domain_summary
from navigation import patient_navigation
from config import DOMAINS

st.set_page_config(
    page_title="Healthy Heart Score Dashboard",
    layout="wide"
)

st.title("Healthy Heart Score Dashboard")

df = pd.read_csv("cardio_synthetic_50pts_v2.csv")

patient_ids = df["Patient_ID"].tolist()

col1, col2 = st.columns([8,1])

with col1:
    search = st.text_input("Search Patient")

with col2:
    st.write("")
    st.write("")
    if st.button("Go"):

        patient_id = int(search)

        if patient_id in patient_ids:

            st.session_state.selected_patient = patient_id
            st.session_state.current_start = patient_id

            st.rerun()

selected_patient = patient_navigation(patient_ids)

patient = df[df["Patient_ID"] == selected_patient].iloc[0]

patient_data = calculate_patient_severity(patient)

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

    sex = "Male" if patient["Biological_Sex"] == 1 else "Female"

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
        1: "🟨 Borderline",
        2: "🟥 Risk"
    }

    for domain, info in DOMAINS.items():

        for feature in info["features"]:

            if feature not in patient_data:
                continue

            table.append({

                "Domain": domain,

                "Parameter": patient_data[feature]["excel_name"],

                "Value": patient_data[feature]["value"],

                "Severity": severity_map[
                    patient_data[feature]["severity"]
                ]

            })

    table = pd.DataFrame(table)

    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True
    )
    
with tab3:

    st.subheader(
        "Doctor Calculated HHS"
    )

    hhs = st.number_input(

        "Enter HHS",

        min_value=0,

        max_value=100,

        value=0

    )

    remarks = st.text_area(

        "Doctor Remarks"

    )

    if st.button("Save"):

        new_row = pd.DataFrame([{
        "Patient_ID": patient["Patient_ID"],
        "HHS": hhs,
        "Remarks": remarks
        }])

        try:
            saved = pd.read_csv("saved_hhs.csv")

            if patient["Patient_ID"] in saved["Patient_ID"].values:

                saved.loc[
                    saved["Patient_ID"] == patient["Patient_ID"],
                    ["HHS", "Remarks"]
                ] = [hhs, remarks]

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
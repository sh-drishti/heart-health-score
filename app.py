import streamlit as st
import pandas as pd

from streamlit_extras.stylable_container import stylable_container
from adapter import calculate_hhs
from severity import calculate_patient_severity
from ui import show_domain_summary, show_additional_information, show_clinical_validation
from navigation import patient_navigation
from config import DOMAINS, CONTEXT_VARIABLES
from tab2 import show_tab2
from tab3 import show_tab3

st.set_page_config(
    page_title="Healthy Heart Score Dashboard",
    layout="wide"
)

st.markdown("""
<style>

/* Sticky Patient Header */
.stMainBlockContainer > div > div:nth-child(8) {
    position: sticky;
    top: 3.8rem;
    background:black;
    z-index: 1000;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    margin-bottom: 5px;
}

</style>
""", unsafe_allow_html=True)

# st.markdown("""
# <style>
# .sticky-header {
#     position: sticky;
#     top: 0;
#     z-index: 999;
#     background-color: white;
#     padding: 0.5rem 0;
#     border-bottom: 1px solid #ddd;
# }
# </style>
# """, unsafe_allow_html=True)

st.title("Healthy Heart Score Dashboard")

df = pd.read_csv("data/cardio_hhs_2.csv")

patient_ids = df["Patient_ID"].tolist()

with st.form("patient_search"):

    col1, col2 = st.columns([8,1])
    with col1:
        search = st.text_input(
            "Search Patient",
            placeholder="e.g. SYN-0001"
        )

    with col2:
        st.write("")
        st.write("")
        submitted = st.form_submit_button("Go", use_container_width=True)

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
# hhs_result = calculate_hhs(patient_data)
official_result = calculate_hhs(patient)
st.markdown("---")
st.markdown('<div class="sticky-header>', unsafe_allow_html=True)

st.markdown(
    '<div id="patient-header-anchor"></div>',
    unsafe_allow_html=True
)

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(
        "Patient ID",
        patient["Patient_ID"]
    )

with col2:
    st.metric(
        "Age",
        patient["age"]
    )

with col3:
    sex = "Male" if patient["biological_sex"] == "Male" else "Female"

    st.metric(
        "Biological Sex",
        sex
    )
with col4:
    st.metric("Healthy Heart Score", official_result["hhs"])
    
with col5:
    st.metric("Confidence",f'{official_result["data_confidence"]}%')
    
st.markdown("</div>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(
    [
        "Domain Summary",
        "All Parameters"
    ]
)

with tab1:
    show_domain_summary(patient_data, official_result)
    show_additional_information(patient)
    show_clinical_validation(official_result)

with tab2:
    show_tab2(patient_data,official_result)
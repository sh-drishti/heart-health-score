import streamlit as st
import pandas as pd

from severity import calculate_patient_severity
from ui import show_domain_summary

st.set_page_config(layout="wide")

df = pd.read_csv("cardio_synthetic_50pts_v2.csv")

patient = df.iloc[0]

patient_data = calculate_patient_severity(patient)

st.title("Testing UI")

show_domain_summary(patient_data)
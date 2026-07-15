import pandas as pd
import streamlit as st

def show_tab3(official_result):
    show_score_card(official_result)
    st.divider()
    show_assessment_status(official_result)
    st.divider()
    show_clinical_remarks()
    st.divider()
    show_save_assessment()
    
def show_score_card(official_result):
    st.subheader("Healthy Heart Score Assessment")
    col1,col2=st.columns(2)
    with col1:
        st.metric("Healthy Heart Score", official_result["hhs"])
    with col2:
        st.metric("Data Confidence",f'{official_result["data_confidence"]}%')    
def show_assessment_status(official_result):
    st.subheader("Assessment Status")
    confidence = official_result["confidence_label"]
    abstained = official_result["abstained"]
    st.write(f"**Confidence Level:** {confidence}")

    if abstained:
        st.warning("Assessment Status : Provisional")

    else:
        st.success("Assessment Status : Valid")

    reasons = official_result["abstention_reasons"]
    if len(reasons) > 0:
        st.markdown("#### Remarks")
        for reason in reasons:
            st.write(f"• {reason}")

    else:
        st.info("No assessment concerns detected.")
    
def show_clinical_remarks():
    st.subheader("Clinical Remarks")
    st.text_area("Doctor's Remarks",placeholder="Enter your assessment here...", height=180)
    
def show_save_assessment():
    col1,col2=st.columns([2,1])
    with col1:
        st.button("Save Assessment", use_container_width=True)
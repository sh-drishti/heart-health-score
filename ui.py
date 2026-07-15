import streamlit as st
from config import DOMAINS, OFFICIAL_DOMAIN_MAPPING, SECTION_FIELDS
import pandas as pd
from adapter import calculate_hhs

def get_color(severity):

    if severity is None:
        return "#9E9E9E"

    if severity <= 1:
        if severity < 0.33:
            return "#4CAF50"
        elif severity < 0.67:
            return "#FFC107"
        else:
            return "#F44336"

    return "#9E9E9E"


def get_label(severity):

    if severity is None:
        return "N/A"

    if severity <= 1:
        if severity < 0.33:
            return "Low"
        elif severity < 0.67:
            return "Moderate"
        else:
            return "High"

    return "N/A"


def draw_rectangles(scores):

    html = ""

    for score in scores:

        color = get_color(score)

        html += f"""
        <div style="
            width:22px;
            height:18px;
            background:{color};
            display:inline-block;
            margin-right:4px;
            border-radius:3px;
        "></div>
        """

    return html

def show_parameter_table(features, patient_data):

    def severity_key(feature):

        severity = patient_data[feature]["severity"]

        if severity is None:
            return (1, 0)

        return (0, -severity)


    available_features = [
        feature for feature in features
        if feature in patient_data
    ]

    sorted_features = sorted(
        available_features,
        key=severity_key
    )

    # Column headings
    st.markdown(
        """
        <div style="
            display:grid;
            grid-template-columns:4fr 2fr 2fr;
            font-weight:bold;
            margin-bottom:5px;
        ">
            <div>Parameter</div>
            <div>Value</div>
            <div align="center">Severity</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("---")

    for feature in sorted_features:

        info = patient_data[feature]

        severity = info["severity"]

        value = info["value"]

        severity = info["severity"]
        if pd.isna(value):
            color = "#9E9E9E"
            label = "Missing"
        elif severity is None:
            color = "#9E9E9E"      # Grey
            label = "N/A"
        else:
            color = get_color(severity)
            label = get_label(severity)

        c1, c2, c3 = st.columns([4,2,2])

        with c1:
            st.write(info["excel_name"])

        with c2:
            unit = info.get("unit", "")
            if pd.isna(value):
                st.write("--")
            elif unit:
                st.write(f"{value} {unit}")
            else:
                st.write(value)

        with c3:

            st.markdown(
                f"""
                <div style="
                    background:{color};
                    color:white;
                    text-align:center;
                    border-radius:5px;
                    padding:4px;
                    font-weight:bold;
                ">
                    {label}
                </div>
                """,
                unsafe_allow_html=True
            )
    
def show_domain_card(domain_name,weight,features,patient_data, official_result):

    scores = []
    available_features = []

    for feature in features:
        if feature not in patient_data:
            continue
        available_features.append(feature)
        severity = patient_data[feature]["severity"]
        if severity is None:
            continue
        scores.append(severity)

    normal_count = scores.count(0)
    borderline_count = scores.count(0.5)
    risk_count = scores.count(1)

    if len(available_features) == 0:
        return

    official_domain=OFFICIAL_DOMAIN_MAPPING[domain_name]
    domain_severity = official_result["domain_severities"][official_domain]
    contribution = round(weight * domain_severity, 2)
    color = get_color(domain_severity)

    rectangles = draw_rectangles(scores)
    parameter_count = len(available_features)

    if weight is not None:

        weight_html = (
            f'<div style="'
            f'padding:5px 10px;'
            f'border-radius:15px;'
            f'font-size:18px;'
            f'display:inline-block;'
            f'">'
            f'Weight : {weight}'
            f'</div>'
        )

    else:

        weight_html = ""
        
    background_color = ("76,175,80" if domain_severity < 0.33
        else "255,193,7" if domain_severity < 0.67
        else "244,67,54"
    )
        
    st.markdown(

        f"""

        <div style="
        padding:12px;
        border-radius:10px;
        box-shadow:0px 0px 8px rgba(0,0,0,0.15);
        margin-bottom:20px;
        background: rgba({background_color}, 0.12);
        border:2px solid {color};
        ">

        <div style="
        display:flex;
        justify-content:space-between;
        align-items:flex-start;
        ">

        <div>

        <h4 style="
        margin:0;
        ">
        {domain_name}
        {f'({parameter_count} Parameters)' if parameter_count > 1 else f'({parameter_count} Parameter)'}
        </h4>

        <div style="
        margin-top:-7px;
        font-size:15px;
        ">

        <b>HHS Domain Severity :</b>
        {domain_severity:.2f}

        </div>

        </div>

        {weight_html}

        </div>


        {rectangles}

        <div style="
        display:flex;
        gap:25px;
        font-weight:bold;
        ">

        <span style="color:#4CAF50;">
        🟩 {normal_count}
        </span>

        <span style="color:#FFC107;">
        🟨 {borderline_count}
        </span>

        <span style="color:#F44336;">
        🟥 {risk_count}
        </span>

        </div>

        </div>

        """,

        unsafe_allow_html=True

        )
    with st.expander("View Parameters", expanded=st.session_state.expand_all):

        show_parameter_table(
            available_features,
            patient_data
        )
        
def get_domain_severity(features, patient_data):

    severities = []

    for feature in features:

        if feature not in patient_data:
            continue

        severity = patient_data[feature]["severity"]

        if severity is None:
            continue

        severities.append(severity)

    if len(severities) == 0:
        return -1

    return max(severities)

def show_domain_summary(patient_data, official_result):
    
    col1, col2 = st.columns([1,1])

    with col1:

        if st.button("Expand All"):

            st.session_state.expand_all = True

    with col2:

        if st.button("Collapse All"):

            st.session_state.expand_all = False

    if "expand_all" not in st.session_state:

        st.session_state.expand_all = False

    sort_mode = st.selectbox(

    "Sort Domains By",

    [

        "Clinical Priority",

        "HHS Report Weight"

    ],

    index=0

    )
    
    if sort_mode == "HHS Report Weight":

        ordered_domains = sorted(

            DOMAINS.items(),

            key=lambda x: x[1]["weight"],

            reverse=True

        )

    else:

        ordered_domains = sorted(

            DOMAINS.items(),

            key=lambda x: (

                get_domain_severity(
                    x[1]["features"],
                    patient_data
                ),

                x[1]["weight"]

            ),

            reverse=True

        )


    legend1, legend2, legend3 = st.columns(3)

    with legend1:
        st.success("Normal")

    with legend2:
        st.warning("Borderline")

    with legend3:
        st.error("Risk")

    st.markdown("---")

    for domain_name, info in ordered_domains:

        show_domain_card(

            domain_name,

            info["weight"],

            info["features"],

            patient_data,
            official_result

        )
        
OPTIONAL_MARKER_UNITS = {
    "CAC": "Agatston",
    "hsCRP": "mg/L",
    "PRS_Percentile": "%",
    "Genetic_Mutation": ""
}

def show_info_card(title, fields, patient):

    st.subheader(title)
    st.markdown("---")
    for label, column in fields:
        if column not in patient.index:
            continue
        value = patient[column]
        color, display = get_badge(value)
        c1, c2 = st.columns([3,2])
        with c1:
            st.write(label)

        with c2:
            if color is None:
                unit = OPTIONAL_MARKER_UNITS.get(column, "")
                if display == "Missing":
                    st.write(display)
                elif unit:
                    st.write(f"{display} {unit}")
                else:
                    st.write(display)
            else:
                st.markdown(
                    f"""
                    <div style="
                        background:{color};
                        color:white;
                        text-align:center;
                        border-radius:5px;
                        padding:4px;
                        font-weight:bold;
                    ">
                        {display}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    
def show_additional_information(patient):

    st.markdown("---")
    st.subheader("Additional Clinical Information")
    col1, col2 = st.columns(2)
    section_names = list(SECTION_FIELDS.keys())
    with col1:
        show_info_card(
            section_names[0],
            SECTION_FIELDS[section_names[0]],
            patient
        )
    with col2:
        show_info_card(
            section_names[2],
            SECTION_FIELDS[section_names[2]],
            patient
        )
    col3,col4=st.columns(2)
    with col3:
        show_info_card(
            section_names[1],
            SECTION_FIELDS[section_names[1]],
            patient
        )
    with col4:
        show_info_card(
            section_names[3],
            SECTION_FIELDS[section_names[3]],
            patient
        )    

def get_badge(value):

    if pd.isna(value):
        return None, "Missing"

    value = str(value).strip()

    colors = {
        "Yes": "#F44336",
        "No": "#4CAF50",
        "Unknown": "#9E9E9E",
        "Concern": "#FFC107",
        "Available": "#4CAF50",
        "Not Measured": "#FFC107"
    }

    if value in colors:
        return colors[value], value

    return None, value
import streamlit as st
from config import DOMAINS, OPTIONAL_MODULES

COLORS = {
    0: "#4CAF50",
    1: "#FFC107",
    2: "#F44336"
}

LABELS = {
    0: "Normal",
    1: "Borderline",
    2: "Risk"
}


def draw_rectangles(scores):

    html = ""

    for score in scores:

        color = COLORS[score]

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

    sorted_features = sorted(
        [
            feature for feature in features
            if feature in patient_data
        ],
        key=lambda feature: patient_data[feature]["severity"],
        reverse=True
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

        color = COLORS[severity]

        label = LABELS[severity]

        c1, c2, c3 = st.columns([4,2,2])

        with c1:
            st.write(info["excel_name"])

        with c2:
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
    
def show_domain_card(domain_name,weight,features,patient_data):

    scores = []

    for feature in features:

        if feature not in patient_data:
            continue

        severity = patient_data[feature]["severity"]

        if severity is None:
            print(f"{feature} returned None severity")
            continue

        scores.append(severity)

    normal_count = scores.count(0)
    borderline_count = scores.count(1)
    risk_count = scores.count(2)
    
    if len(scores) == 0:

        return

    domain_severity = max(scores)

    color = COLORS[domain_severity]

    rectangles = draw_rectangles(scores)
    parameter_count = len(scores)

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
        
    st.markdown(

        f"""

        <div style="
        padding:12px;
        border-radius:10px;
        box-shadow:0px 0px 8px rgba(0,0,0,0.15);
        margin-bottom:20px;
        background:rgba(
            { '76,175,80' if domain_severity==0 else '255,193,7' if domain_severity==1 else '244,67,54' },
            0.12
        );
        border:2px solid {color};
        ">

        <div style="
        display:flex;
        justify-content:space-between;
        align-items:center;
        ">

        <h4 style="
        margin:0;
        ">
        {domain_name} {f'({parameter_count} Parameters)' if parameter_count > 1 else f'({parameter_count} Parameter)'}
        </h4>
        
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
            features,
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

def show_domain_summary(patient_data):
    
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

            patient_data

        )
        
    st.markdown("---")

    st.header("Optional Clinical Modules")

    for module, features in OPTIONAL_MODULES.items():

        show_domain_card(
            domain_name=module,
            weight=None,
            features=features,
            patient_data=patient_data
        )
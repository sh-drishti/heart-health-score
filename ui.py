import streamlit as st
from config import DOMAINS

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

    st.markdown("---")

    sorted_features = sorted(
        [
            feature for feature in features
            if feature in patient_data
        ],
        key=lambda feature: patient_data[feature]["severity"],
        reverse=True
    )

    for feature in sorted_features:

        if feature not in patient_data:
            continue

        info = patient_data[feature]

        severity = info["severity"]

        value = info["value"]

        color = COLORS[severity]

        label = LABELS[severity]

        c1, c2, c3 = st.columns([4,2,2])

        with c1:

            st.write(feature.replace("_"," "))

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
                ">

                {label}

                </div>
                """,

                unsafe_allow_html=True

            )

    st.markdown("---")
    
def show_domain_card(domain_name,weight,features,patient_data):

    scores = []

    for feature in features:

        if feature in patient_data:

            scores.append(
                patient_data[feature]["severity"]
            )

    normal_count = scores.count(0)
    borderline_count = scores.count(1)
    risk_count = scores.count(2)
    
    if len(scores) == 0:

        return

    domain_severity = max(scores)

    color = COLORS[domain_severity]

    rectangles = draw_rectangles(scores)

    st.markdown(

        f"""

        <div style="
        border-left:6px solid {color};
        padding:12px;
        border-radius:10px;
        box-shadow:0px 0px 8px rgba(0,0,0,0.15);
        margin-bottom:20px;
        ">

        <div style="
        display:flex;
        justify-content:space-between;
        align-items:center;
        ">

        <h4 style="
        margin:0;
        ">
        {domain_name}
        </h4>

        <span style="
        background:#eeeeee;
        padding:5px 10px;
        border-radius:15px;
        font-weight:bold;
        font-size:14px;
        ">

        Weight : {weight}

        </span>

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
    with st.expander("View Parameters"):

        show_parameter_table(
            features,
            patient_data
        )
        
def show_domain_summary(patient_data):

    ordered_domains = sorted(

        DOMAINS.items(),

        key=lambda x: x[1]["weight"],

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
        

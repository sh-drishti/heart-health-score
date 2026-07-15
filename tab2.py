import pandas as pd
import streamlit as st
from ui import get_color, get_label
from config import DOMAINS
import plotly.express as px

FEATURE_TO_DOMAIN={}
for domain,info in DOMAINS.items():
    for feature in info["features"]:
        FEATURE_TO_DOMAIN[feature]=domain

def show_tab2(patient_data, official_result):
    show_parameter_summary(patient_data)
    st.divider()
    
    show_domain_contribution_chart(official_result)
    st.divider()
    
    show_domain_severity_chart(official_result)
    st.divider()

    show_burden_breakdown(official_result)
    st.divider()

    show_red_flags(official_result)
    
def show_parameter_summary(patient_data):
    st.subheader("Complete Parameter Summary")
    rows=[]
    severity_order={1:0, 0.5:1, 0:2, None:3}
    for feature, info in patient_data.items():
        severity=info["severity"]
        rows.append({
            "Parameter":info["excel_name"],
            "Domain": FEATURE_TO_DOMAIN.get(feature, "Other"),
            "Value":info["value"],
            "Unit":info["unit"],
            "Severity":get_label(severity),
            "Severity Score":severity,
            "Sort":severity_order.get(severity,3)
        })
    df=pd.DataFrame(rows)
    df=df.sort_values(by=["Sort","Domain","Parameter"])
    df=df.drop(columns=["Sort","Severity Score"])
    st.dataframe(df,use_container_width=True, hide_index=True)
    
def show_domain_contribution_chart(official_result):
    st.subheader("Domain Contribution to HHS")
    df=pd.DataFrame(official_result["domain_rows"])
    df=df[df["Total domain contribution"]>0]
    fig=px.pie(
        df,
        names="Domain",
        values="Total domain contribution",
        hole=0.45
    )
    total_burden=official_result["burden"]["total"]
    fig.update_traces(
        textposition="outside",
        textinfo="percent+label",
        hovertemplate=
        "<b>%{label}</b><br>" +
        "Contribution: %{value:.2f}<br>" +
        "Percentage: %{percent}<extra></extra>"
    )

    fig.update_layout(
        annotations=[
            dict(
                text=f"<b>Total<br>{total_burden:.2f}</b>",
                x=0.5,
                y=0.5,
                font_size=18,
                showarrow=False
            )
        ],
        height=500,
        margin=dict(
            t=20,
            b=20,
            l=20,
            r=20
        ),
        legend_title="Domains"
    )
    st.plotly_chart(fig, use_container_width=True)

def show_domain_severity_chart(official_result):
    st.subheader("Domain Severity Overview")
    df=pd.DataFrame({
        "Domain":list(official_result["domain_severities"].keys()),
        "Severity":list(official_result["domain_severities"].values())
    })
    def severity_color(value):
        if value < 0.33:
            return "Low"
        elif value < 0.67:
            return "Moderate"
        return "High"
    df["Status"]=df["Severity"].apply(severity_color)
    df=df.sort_values("Severity", ascending=True)
    colormap={ "Low": "#4CAF50","Moderate": "#FFC107","High": "#F44336"}
    fig = px.bar(
        df,
        x="Severity",
        y="Domain",
        orientation="h",
        text="Severity",
        color="Status",
        color_discrete_map=colormap
    )

    fig.update_traces(
        texttemplate="%{text:.2f}",
        textposition="outside"
    )
    fig.update_layout(
        height=450,
        showlegend=False,
        xaxis=dict(
            title="Severity",
            range=[0, 1]
        ),
        yaxis_title="",
        margin=dict(
            t=20,
            b=20,
            l=20,
            r=20
        )
    )
    st.plotly_chart(
        fig,
        use_container_width=True
    )

def show_burden_breakdown(official_result):
    st.subheader("Burden Breakdown")
    burden=official_result["burden"]
    rows=[
        {
            "Component":"Main Burden",
            "Value":burden["main"]
        },
        {
            "Component":"Treatment Residual",
            "Value":burden["treatment"]
        },
        {
            "Component":"Interaction Burden",
            "Value":burden["interaction"]
        },
        {
            "Component":"Total Burden",
            "Value":burden["total"]
        }
    ]
    df=pd.DataFrame(rows)
    st.dataframe(
        df,
        hide_index=True,
        use_container_width=True
    )


def show_red_flags(official_result):
    st.subheader("Critical Red Flags")
    flags=official_result["red_flags"]
    if len(flags)==0:
        st.success("No critical red flags detected.")
        return
    for flag in flags:
        st.error(flag)
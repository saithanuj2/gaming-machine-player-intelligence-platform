from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard.components.layout import (
    render_footer,
    render_last_updated,
    render_page_header,
    render_section_header,
)
from src.dashboard.components.metrics import render_metric_grid


# =========================================================
# SAMPLE MACHINE DATA
# Replace with FastAPI responses later.
# =========================================================

def build_machine_health_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Health Status": [
                "Healthy",
                "Warning",
                "High Risk",
                "Offline",
            ],
            "Machines": [
                62,
                18,
                8,
                4,
            ],
        }
    )


def build_utilization_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Location": [
                "Buffalo Central",
                "Niagara East",
                "Rochester North",
                "Buffalo West",
                "Syracuse Central",
            ],
            "Utilization Rate": [
                0.86,
                0.81,
                0.78,
                0.74,
                0.69,
            ],
            "Active Machines": [
                24,
                19,
                18,
                16,
                15,
            ],
        }
    )


def build_downtime_trend() -> pd.DataFrame:
    today = datetime.now().date()

    dates = [
        today - timedelta(days=index)
        for index in range(29, -1, -1)
    ]

    downtime_minutes = [
        920,
        880,
        950,
        810,
        790,
        840,
        760,
        730,
        775,
        690,
        710,
        665,
        640,
        680,
        620,
        590,
        610,
        560,
        545,
        520,
        500,
        485,
        470,
        455,
        440,
        425,
        410,
        395,
        380,
        365,
    ]

    return pd.DataFrame(
        {
            "Date": dates,
            "Downtime Minutes": downtime_minutes,
        }
    )


def build_failure_risk_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Machine ID": [
                "GM-0044",
                "GM-0012",
                "GM-0078",
                "GM-0091",
                "GM-0037",
                "GM-0066",
                "GM-0104",
                "GM-0025",
                "GM-0083",
                "GM-0112",
            ],
            "Location": [
                "Buffalo Central",
                "Niagara East",
                "Rochester North",
                "Buffalo West",
                "Syracuse Central",
                "Buffalo Central",
                "Niagara East",
                "Rochester North",
                "Buffalo West",
                "Syracuse Central",
            ],
            "Game Type": [
                "Video Slot",
                "Progressive",
                "Video Slot",
                "Electronic Table",
                "Progressive",
                "Video Slot",
                "Electronic Table",
                "Progressive",
                "Video Slot",
                "Electronic Table",
            ],
            "Failure Probability": [
                0.96,
                0.92,
                0.89,
                0.86,
                0.81,
                0.78,
                0.74,
                0.69,
                0.64,
                0.58,
            ],
            "Critical Events": [
                18,
                15,
                13,
                11,
                9,
                8,
                7,
                6,
                5,
                4,
            ],
            "Downtime Minutes": [
                780,
                640,
                590,
                520,
                470,
                420,
                380,
                335,
                290,
                245,
            ],
            "Last Service Days": [
                74,
                68,
                63,
                59,
                54,
                49,
                45,
                41,
                38,
                35,
            ],
            "Recommended Action": [
                "Immediate inspection",
                "Schedule emergency service",
                "Replace cooling module",
                "Inspect power supply",
                "Review sensor alerts",
                "Schedule maintenance",
                "Inspect bill validator",
                "Monitor event frequency",
                "Run diagnostics",
                "Preventive maintenance",
            ],
        }
    )


def build_event_type_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Event Type": [
                "Bill Validator",
                "Door Sensor",
                "Network Loss",
                "Printer Fault",
                "Temperature Alert",
                "Power Supply",
            ],
            "Events": [
                92,
                71,
                64,
                48,
                37,
                26,
            ],
        }
    )


def build_machine_revenue_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Machine ID": [
                "GM-0021",
                "GM-0048",
                "GM-0063",
                "GM-0071",
                "GM-0097",
                "GM-0108",
                "GM-0115",
                "GM-0123",
            ],
            "Revenue": [
                18650,
                17480,
                16920,
                16110,
                15780,
                14960,
                14220,
                13650,
            ],
        }
    )


# =========================================================
# PAGE HEADER
# =========================================================

render_page_header(
    title="Machine Analytics",
    subtitle=(
        "Track machine health, utilization, downtime, "
        "anomalies, and predicted failure risk."
    ),
    badge_text="Machine Monitoring",
)


# =========================================================
# LOAD DATA
# =========================================================

machine_health_dataframe = build_machine_health_data()
utilization_dataframe = build_utilization_data()
downtime_dataframe = build_downtime_trend()
failure_risk_dataframe = build_failure_risk_data()
event_type_dataframe = build_event_type_data()
machine_revenue_dataframe = build_machine_revenue_data()


# =========================================================
# KPI CARDS
# =========================================================

render_metric_grid(
    metrics=[
        {
            "label": "Total Machines",
            "value": "100",
            "delta": "92 currently active",
        },
        {
            "label": "Machine Availability",
            "value": "92.0%",
            "delta": "1.6% improvement",
        },
        {
            "label": "High-Risk Machines",
            "value": "8",
            "delta": "Maintenance required",
            "delta_color": "inverse",
        },
        {
            "label": "Offline Machines",
            "value": "4",
            "delta": "Service queue",
            "delta_color": "inverse",
        },
        {
            "label": "Average Utilization",
            "value": "78.6%",
            "delta": "2.4% increase",
        },
        {
            "label": "Critical Events",
            "value": "338",
            "delta": "8.3% decrease",
            "delta_color": "inverse",
        },
        {
            "label": "Monthly Downtime",
            "value": "384,905 min",
            "delta": "2.5% decrease",
            "delta_color": "inverse",
        },
        {
            "label": "Preventive Maintenance",
            "value": "87.4%",
            "delta": "4.1% increase",
        },
    ],
    columns=4,
)


# =========================================================
# FILTERS
# =========================================================

st.divider()

filter_column_1, filter_column_2, filter_column_3 = st.columns(3)

with filter_column_1:
    selected_location = st.selectbox(
        "Location",
        [
            "All Locations",
            *failure_risk_dataframe["Location"]
            .drop_duplicates()
            .tolist(),
        ],
    )

with filter_column_2:
    selected_game_type = st.selectbox(
        "Game type",
        [
            "All Game Types",
            *failure_risk_dataframe["Game Type"]
            .drop_duplicates()
            .tolist(),
        ],
    )

with filter_column_3:
    minimum_failure_probability = st.slider(
        "Minimum failure probability",
        min_value=0.0,
        max_value=1.0,
        value=0.70,
        step=0.05,
    )


# =========================================================
# MACHINE HEALTH AND UTILIZATION
# =========================================================

render_section_header(
    title="Machine Health and Utilization",
    description=(
        "Monitor the operational condition and "
        "utilization of machines across locations."
    ),
)

left_column, right_column = st.columns(
    2,
    gap="large",
)

with left_column:
    machine_health_figure = px.bar(
        machine_health_dataframe,
        x="Health Status",
        y="Machines",
        text="Machines",
        title="Machine Health Distribution",
        color="Health Status",
        color_discrete_map={
            "Healthy": "#22c55e",
            "Warning": "#facc15",
            "High Risk": "#f97316",
            "Offline": "#ef4444",
        },
    )

    machine_health_figure.update_layout(
        height=390,
        margin=dict(
            l=20,
            r=20,
            t=60,
            b=20,
        ),
        xaxis_title=None,
        yaxis_title="Number of Machines",
        showlegend=False,
    )

    machine_health_figure.update_traces(
        textposition="outside",
    )

    st.plotly_chart(
        machine_health_figure,
        use_container_width=True,
    )

with right_column:
    utilization_figure = px.bar(
        utilization_dataframe.sort_values(
            "Utilization Rate",
            ascending=True,
        ),
        x="Utilization Rate",
        y="Location",
        orientation="h",
        text="Utilization Rate",
        title="Machine Utilization by Location",
    )

    utilization_figure.update_layout(
        height=390,
        margin=dict(
            l=20,
            r=20,
            t=60,
            b=20,
        ),
        xaxis_title="Utilization Rate",
        yaxis_title=None,
        xaxis_tickformat=".0%",
        showlegend=False,
    )

    utilization_figure.update_traces(
        texttemplate="%{text:.1%}",
        textposition="outside",
    )

    st.plotly_chart(
        utilization_figure,
        use_container_width=True,
    )


# =========================================================
# DOWNTIME AND EVENTS
# =========================================================

render_section_header(
    title="Downtime and Event Monitoring",
    description=(
        "Track downtime trends and recurring "
        "machine event categories."
    ),
)

left_column, right_column = st.columns(
    [2, 1],
    gap="large",
)

with left_column:
    downtime_figure = px.area(
        downtime_dataframe,
        x="Date",
        y="Downtime Minutes",
        markers=True,
        title="30-Day Machine Downtime Trend",
    )

    downtime_figure.update_layout(
        height=390,
        margin=dict(
            l=20,
            r=20,
            t=60,
            b=20,
        ),
        hovermode="x unified",
        xaxis_title=None,
        yaxis_title="Downtime Minutes",
    )

    downtime_figure.update_traces(
        line_width=3,
    )

    st.plotly_chart(
        downtime_figure,
        use_container_width=True,
    )

with right_column:
    event_figure = px.pie(
        event_type_dataframe,
        names="Event Type",
        values="Events",
        hole=0.58,
        title="Critical Events by Type",
    )

    event_figure.update_layout(
        height=390,
        margin=dict(
            l=10,
            r=10,
            t=60,
            b=10,
        ),
        legend_title=None,
    )

    event_figure.update_traces(
        textinfo="percent+label",
    )

    st.plotly_chart(
        event_figure,
        use_container_width=True,
    )


# =========================================================
# MACHINE REVENUE PERFORMANCE
# =========================================================

render_section_header(
    title="Machine Revenue Performance",
    description=(
        "Identify top-performing machines and "
        "compare revenue contribution."
    ),
)

machine_revenue_figure = px.bar(
    machine_revenue_dataframe.sort_values(
        "Revenue",
        ascending=True,
    ),
    x="Revenue",
    y="Machine ID",
    orientation="h",
    text="Revenue",
    title="Top Revenue-Generating Machines",
)

machine_revenue_figure.update_layout(
    height=410,
    margin=dict(
        l=20,
        r=20,
        t=60,
        b=20,
    ),
    xaxis_title="Revenue ($)",
    yaxis_title=None,
    showlegend=False,
)

machine_revenue_figure.update_traces(
    texttemplate="$%{text:,.0f}",
    textposition="outside",
)

st.plotly_chart(
    machine_revenue_figure,
    use_container_width=True,
)


# =========================================================
# FAILURE RISK QUEUE
# =========================================================

render_section_header(
    title="Predictive Maintenance Queue",
    description=(
        "Machines ranked by predicted failure risk, "
        "critical events, downtime, and service age."
    ),
)

filtered_failure_risk = failure_risk_dataframe.copy()

filtered_failure_risk = filtered_failure_risk[
    filtered_failure_risk["Failure Probability"]
    >= minimum_failure_probability
]

if selected_location != "All Locations":
    filtered_failure_risk = filtered_failure_risk[
        filtered_failure_risk["Location"]
        == selected_location
    ]

if selected_game_type != "All Game Types":
    filtered_failure_risk = filtered_failure_risk[
        filtered_failure_risk["Game Type"]
        == selected_game_type
    ]

filtered_failure_risk = filtered_failure_risk.sort_values(
    [
        "Failure Probability",
        "Critical Events",
        "Downtime Minutes",
    ],
    ascending=[
        False,
        False,
        False,
    ],
)

download_dataframe = filtered_failure_risk.copy()

download_dataframe["Failure Probability"] = (
    download_dataframe["Failure Probability"]
    .mul(100)
    .round(1)
    .astype(str)
    .add("%")
)

download_data = download_dataframe.to_csv(
    index=False
).encode("utf-8")

st.download_button(
    label="Download Maintenance Queue",
    data=download_data,
    file_name="predictive_maintenance_queue.csv",
    mime="text/csv",
)

st.dataframe(
    filtered_failure_risk,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Machine ID": st.column_config.TextColumn(
            "Machine ID"
        ),
        "Location": st.column_config.TextColumn(
            "Location"
        ),
        "Game Type": st.column_config.TextColumn(
            "Game Type"
        ),
        "Failure Probability": st.column_config.ProgressColumn(
            "Failure Probability",
            min_value=0.0,
            max_value=1.0,
            format="%.0f%%",
        ),
        "Critical Events": st.column_config.NumberColumn(
            "Critical Events",
            format="%d",
        ),
        "Downtime Minutes": st.column_config.NumberColumn(
            "Downtime Minutes",
            format="%d min",
        ),
        "Last Service Days": st.column_config.NumberColumn(
            "Last Service",
            format="%d days",
        ),
        "Recommended Action": st.column_config.TextColumn(
            "Recommended Action"
        ),
    },
)

if filtered_failure_risk.empty:
    st.info(
        "No machines match the selected filters."
    )
else:
    st.success(
        f"{len(filtered_failure_risk)} machines require "
        "review based on the selected failure-risk criteria."
    )


# =========================================================
# OPERATIONAL RECOMMENDATION
# =========================================================

st.warning(
    "Prioritize machines with failure probabilities above "
    "90%, repeated critical events, and extended periods "
    "since the last preventive service."
)


# =========================================================
# FOOTER
# =========================================================

render_last_updated()
render_footer()
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
from src.dashboard.components.metrics import (
    render_metric_grid,
)
from src.dashboard.components.tables import (
    render_data_table,
    render_table_toolbar,
)
from src.dashboard.utils import (
    format_currency,
    format_number,
    format_percentage,
)


# =========================================================
# PAGE HEADER
# =========================================================

render_page_header(
    title="Executive Overview",
    subtitle=(
        "Enterprise gaming revenue, player, "
        "machine, and operational intelligence."
    ),
    badge_text="Live Operations",
)


# =========================================================
# EXECUTIVE KPI CARDS
# =========================================================

render_metric_grid(
    metrics=[
        {
            "label": "Net Gaming Revenue",
            "value": format_currency(289281.25),
            "delta": "4.8% vs previous period",
        },
        {
            "label": "Active Players",
            "value": format_number(4706),
            "delta": "3.2% increase",
        },
        {
            "label": "Active Machines",
            "value": format_number(92),
            "delta": "92% availability",
        },
        {
            "label": "Actual Hold",
            "value": format_percentage(0.0903),
            "delta": "0.4% above target",
        },
        {
            "label": "Player Sessions",
            "value": format_number(20000),
            "delta": "6.1% increase",
        },
        {
            "label": "Transactions",
            "value": format_number(100000),
            "delta": "5.7% increase",
        },
        {
            "label": "Critical Events",
            "value": format_number(338),
            "delta": "8.3% decrease",
            "delta_color": "inverse",
        },
        {
            "label": "Total Downtime",
            "value": f"{format_number(384905)} min",
            "delta": "2.5% decrease",
            "delta_color": "inverse",
        },
    ],
    columns=4,
)


# =========================================================
# SAMPLE ANALYTICS DATA
# Replace these datasets with FastAPI responses later.
# =========================================================

today = datetime.now().date()

revenue_dates = [
    today - timedelta(days=index)
    for index in range(29, -1, -1)
]

revenue_values = [
    8350,
    8720,
    8100,
    9250,
    9480,
    9010,
    9800,
    10250,
    9950,
    10700,
    10550,
    11100,
    10950,
    11500,
    11800,
    11300,
    12150,
    12400,
    11950,
    12750,
    13000,
    12800,
    13450,
    13700,
    13250,
    13900,
    14250,
    14000,
    14600,
    14950,
]

revenue_dataframe = pd.DataFrame(
    {
        "Date": revenue_dates,
        "Net Gaming Revenue": revenue_values,
    }
)

player_risk_dataframe = pd.DataFrame(
    {
        "Risk Category": [
            "Low Risk",
            "Medium Risk",
            "High Risk",
            "Critical Risk",
        ],
        "Players": [
            3210,
            920,
            430,
            146,
        ],
    }
)

machine_health_dataframe = pd.DataFrame(
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

forecast_dataframe = pd.DataFrame(
    {
        "Week": [
            "Week 1",
            "Week 2",
            "Week 3",
            "Week 4",
            "Week 5",
            "Week 6",
        ],
        "Actual Revenue": [
            61200,
            63800,
            65100,
            66900,
            None,
            None,
        ],
        "Forecast Revenue": [
            60500,
            62900,
            65800,
            67400,
            69100,
            70800,
        ],
    }
)

maintenance_dataframe = pd.DataFrame(
    {
        "Machine ID": [
            "GM-0044",
            "GM-0012",
            "GM-0078",
            "GM-0091",
            "GM-0037",
        ],
        "Location": [
            "Buffalo Central",
            "Niagara East",
            "Rochester North",
            "Buffalo West",
            "Syracuse Central",
        ],
        "Failure Risk": [
            0.96,
            0.92,
            0.89,
            0.86,
            0.81,
        ],
        "Critical Events": [
            18,
            15,
            13,
            11,
            9,
        ],
        "Downtime Minutes": [
            780,
            640,
            590,
            520,
            470,
        ],
        "Priority": [
            "Critical",
            "Critical",
            "High",
            "High",
            "High",
        ],
    }
)


# =========================================================
# REVENUE AND PLAYER INTELLIGENCE
# =========================================================

render_section_header(
    title="Revenue and Player Intelligence",
    description=(
        "Monitor revenue performance and identify players "
        "requiring proactive retention action."
    ),
)

left_column, right_column = st.columns(
    [2, 1],
    gap="large",
)

with left_column:
    revenue_figure = px.line(
        revenue_dataframe,
        x="Date",
        y="Net Gaming Revenue",
        markers=True,
        title="30-Day Net Gaming Revenue Trend",
    )

    revenue_figure.update_layout(
        height=380,
        margin=dict(
            l=20,
            r=20,
            t=55,
            b=20,
        ),
        xaxis_title=None,
        yaxis_title="Revenue ($)",
        hovermode="x unified",
    )

    revenue_figure.update_traces(
        line_width=3,
    )

    st.plotly_chart(
        revenue_figure,
        use_container_width=True,
    )

with right_column:
    player_risk_figure = px.pie(
        player_risk_dataframe,
        names="Risk Category",
        values="Players",
        title="Player Churn-Risk Distribution",
        hole=0.62,
    )

    player_risk_figure.update_layout(
        height=380,
        margin=dict(
            l=10,
            r=10,
            t=55,
            b=10,
        ),
        legend_title=None,
    )

    st.plotly_chart(
        player_risk_figure,
        use_container_width=True,
    )


# =========================================================
# MACHINE HEALTH AND FORECASTING
# =========================================================

render_section_header(
    title="Operational Health and Forecasting",
    description=(
        "Track machine availability, failure exposure, "
        "and expected weekly revenue."
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
    )

    machine_health_figure.update_layout(
        height=360,
        margin=dict(
            l=20,
            r=20,
            t=55,
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
    player_risk_figure = px.pie(
        player_risk_dataframe,
        names="Risk Category",
        values="Players",
        title="Player Churn-Risk Distribution",
        hole=0.62,
        color="Risk Category",
        color_discrete_map={
            "Low Risk": "#22c55e",
            "Medium Risk": "#facc15",
            "High Risk": "#f97316",
            "Critical Risk": "#ef4444",
        },
    )

    player_risk_figure.update_layout(
        height=380,
        margin=dict(
            l=20,
            r=20,
            t=55,
            b=20,
        ),
        legend=dict(
            orientation="h",
            y=-0.15,
            x=0.5,
            xanchor="center",
        ),
    )

    player_risk_figure.update_traces(
        textinfo="percent+label",
        textfont_size=12,
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Players: %{value}<br>"
            "Percentage: %{percent}"
            "<extra></extra>"
        ),
    )

    st.plotly_chart(
        player_risk_figure,
        use_container_width=True,
    )


# =========================================================
# HIGH-PRIORITY MAINTENANCE TABLE
# =========================================================

render_section_header(
    title="High-Priority Maintenance",
    description=(
        "Machines ranked by predicted failure risk, "
        "critical events, and downtime exposure."
    ),
    action_text="Maintenance Operations",
)

maintenance_display = maintenance_dataframe.copy()

maintenance_display["Failure Risk"] = (
    maintenance_display["Failure Risk"]
    .mul(100)
    .round(1)
    .astype(str)
    .add("%")
)

render_table_toolbar(
    dataframe=maintenance_display,
    download_name="high_priority_maintenance.csv",
    download_key="executive_maintenance_download",
)

render_data_table(
    dataframe=maintenance_display,
    column_config={
        "Machine ID": st.column_config.TextColumn(
            "Machine ID"
        ),
        "Location": st.column_config.TextColumn(
            "Location"
        ),
        "Failure Risk": st.column_config.TextColumn(
            "Failure Risk"
        ),
        "Critical Events": st.column_config.NumberColumn(
            "Critical Events",
            format="%d",
        ),
        "Downtime Minutes": st.column_config.NumberColumn(
            "Downtime Minutes",
            format="%d min",
        ),
        "Priority": st.column_config.TextColumn(
            "Priority"
        ),
    },
    height=270,
    key="executive_maintenance_table",
)


# =========================================================
# EXECUTIVE MESSAGE
# =========================================================

st.success(
    "Executive monitoring is operational. "
    "Current priorities are high-risk machine maintenance, "
    "critical-event reduction, and retention outreach for "
    "high-risk players."
)


# =========================================================
# PAGE FOOTER
# =========================================================

render_last_updated()

render_footer()
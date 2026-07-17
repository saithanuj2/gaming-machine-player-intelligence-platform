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
# SAMPLE PLAYER DATA
# Replace with FastAPI responses later.
# =========================================================

def build_player_summary() -> pd.DataFrame:
    return pd.DataFrame(
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


def build_segment_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Segment": [
                "VIP",
                "Loyal",
                "Casual",
                "At Risk",
                "Dormant",
            ],
            "Players": [
                380,
                1420,
                1680,
                780,
                446,
            ],
            "Average Spend": [
                1240,
                640,
                310,
                255,
                95,
            ],
            "Average Visits": [
                18.4,
                11.2,
                6.8,
                4.1,
                1.7,
            ],
        }
    )


def build_engagement_trend() -> pd.DataFrame:
    today = datetime.now().date()

    dates = [
        today - timedelta(days=index)
        for index in range(29, -1, -1)
    ]

    active_players = [
        3810,
        3890,
        3760,
        3950,
        4010,
        3975,
        4080,
        4120,
        4050,
        4180,
        4210,
        4170,
        4260,
        4310,
        4250,
        4380,
        4410,
        4360,
        4470,
        4510,
        4460,
        4570,
        4620,
        4580,
        4660,
        4700,
        4640,
        4720,
        4680,
        4706,
    ]

    sessions = [
        14200,
        14600,
        13800,
        15100,
        15500,
        15300,
        16100,
        16500,
        15900,
        16900,
        17200,
        16800,
        17600,
        18100,
        17700,
        18500,
        18800,
        18400,
        19200,
        19600,
        19100,
        19900,
        20200,
        19800,
        20500,
        20800,
        20400,
        21100,
        20700,
        20000,
    ]

    return pd.DataFrame(
        {
            "Date": dates,
            "Active Players": active_players,
            "Sessions": sessions,
        }
    )


def build_retention_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Cohort": [
                "Week 1",
                "Week 2",
                "Week 3",
                "Week 4",
                "Week 5",
                "Week 6",
            ],
            "Retention Rate": [
                0.84,
                0.79,
                0.76,
                0.73,
                0.71,
                0.69,
            ],
        }
    )


def build_high_risk_players() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Player ID": [
                "PL-10231",
                "PL-10984",
                "PL-11576",
                "PL-12043",
                "PL-12790",
                "PL-13218",
                "PL-13845",
                "PL-14102",
            ],
            "Segment": [
                "VIP",
                "Loyal",
                "Casual",
                "VIP",
                "At Risk",
                "Loyal",
                "Casual",
                "At Risk",
            ],
            "Churn Probability": [
                0.96,
                0.93,
                0.91,
                0.89,
                0.87,
                0.84,
                0.82,
                0.81,
            ],
            "Lifetime Value": [
                18450,
                12600,
                6400,
                15200,
                4100,
                9800,
                5200,
                3900,
            ],
            "Days Since Last Visit": [
                34,
                29,
                31,
                27,
                25,
                22,
                20,
                19,
            ],
            "Recommended Action": [
                "VIP host outreach",
                "Personalized bonus",
                "Reactivation offer",
                "VIP retention call",
                "Free-play incentive",
                "Loyalty reward",
                "Targeted campaign",
                "Re-engagement email",
            ],
        }
    )


# =========================================================
# PAGE HEADER
# =========================================================

render_page_header(
    title="Player Intelligence",
    subtitle=(
        "Monitor player engagement, churn risk, "
        "lifetime value, segmentation, and retention."
    ),
    badge_text="Player Analytics",
)


# =========================================================
# LOAD DATA
# =========================================================

risk_dataframe = build_player_summary()
segment_dataframe = build_segment_data()
engagement_dataframe = build_engagement_trend()
retention_dataframe = build_retention_data()
high_risk_dataframe = build_high_risk_players()


# =========================================================
# KPI CARDS
# =========================================================

render_metric_grid(
    metrics=[
        {
            "label": "Active Players",
            "value": "4,706",
            "delta": "3.2% increase",
        },
        {
            "label": "High-Risk Players",
            "value": "430",
            "delta": "Requires outreach",
            "delta_color": "inverse",
        },
        {
            "label": "Critical-Risk Players",
            "value": "146",
            "delta": "Immediate action",
            "delta_color": "inverse",
        },
        {
            "label": "Retention Rate",
            "value": "91.4%",
            "delta": "1.8% improvement",
        },
        {
            "label": "Average Player Value",
            "value": "$614",
            "delta": "4.6% increase",
        },
        {
            "label": "VIP Players",
            "value": "380",
            "delta": "8.1% of active players",
        },
        {
            "label": "Monthly Sessions",
            "value": "20,000",
            "delta": "6.1% increase",
        },
        {
            "label": "Reactivation Rate",
            "value": "18.7%",
            "delta": "2.3% improvement",
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
    selected_segment = st.selectbox(
        "Player segment",
        [
            "All Segments",
            *segment_dataframe["Segment"].tolist(),
        ],
    )

with filter_column_2:
    selected_risk = st.selectbox(
        "Risk category",
        [
            "All Risk Levels",
            *risk_dataframe["Risk Category"].tolist(),
        ],
    )

with filter_column_3:
    minimum_probability = st.slider(
        "Minimum churn probability",
        min_value=0.0,
        max_value=1.0,
        value=0.80,
        step=0.05,
    )


# =========================================================
# ENGAGEMENT AND CHURN
# =========================================================

render_section_header(
    title="Engagement and Churn Intelligence",
    description=(
        "Track active-player behavior and identify "
        "players requiring proactive retention action."
    ),
)

left_column, right_column = st.columns(
    [2, 1],
    gap="large",
)

with left_column:
    engagement_figure = px.line(
        engagement_dataframe,
        x="Date",
        y="Active Players",
        markers=True,
        title="30-Day Active Player Trend",
    )

    engagement_figure.update_layout(
        height=390,
        margin=dict(
            l=20,
            r=20,
            t=60,
            b=20,
        ),
        hovermode="x unified",
        xaxis_title=None,
        yaxis_title="Active Players",
    )

    engagement_figure.update_traces(
        line_width=3,
    )

    st.plotly_chart(
        engagement_figure,
        use_container_width=True,
    )

with right_column:
    risk_figure = px.pie(
        risk_dataframe,
        names="Risk Category",
        values="Players",
        hole=0.62,
        title="Churn-Risk Distribution",
        color="Risk Category",
        color_discrete_map={
            "Low Risk": "#22c55e",
            "Medium Risk": "#facc15",
            "High Risk": "#f97316",
            "Critical Risk": "#ef4444",
        },
    )

    risk_figure.update_layout(
        height=390,
        margin=dict(
            l=10,
            r=10,
            t=60,
            b=10,
        ),
        legend_title=None,
    )

    risk_figure.update_traces(
        textinfo="percent+label",
    )

    st.plotly_chart(
        risk_figure,
        use_container_width=True,
    )


# =========================================================
# PLAYER SEGMENTS
# =========================================================

render_section_header(
    title="Player Segmentation",
    description=(
        "Compare segment size, average spend, "
        "and visit frequency."
    ),
)

left_column, right_column = st.columns(
    2,
    gap="large",
)

with left_column:
    segment_figure = px.bar(
        segment_dataframe,
        x="Segment",
        y="Players",
        text="Players",
        title="Players by Segment",
    )

    segment_figure.update_layout(
        height=380,
        margin=dict(
            l=20,
            r=20,
            t=60,
            b=20,
        ),
        xaxis_title=None,
        yaxis_title="Players",
        showlegend=False,
    )

    segment_figure.update_traces(
        textposition="outside",
    )

    st.plotly_chart(
        segment_figure,
        use_container_width=True,
    )

with right_column:
    spend_figure = px.scatter(
        segment_dataframe,
        x="Average Visits",
        y="Average Spend",
        size="Players",
        color="Segment",
        text="Segment",
        title="Segment Value and Engagement",
    )

    spend_figure.update_layout(
        height=380,
        margin=dict(
            l=20,
            r=20,
            t=60,
            b=20,
        ),
        xaxis_title="Average Visits",
        yaxis_title="Average Spend ($)",
        legend_title=None,
    )

    spend_figure.update_traces(
        textposition="top center",
    )

    st.plotly_chart(
        spend_figure,
        use_container_width=True,
    )


# =========================================================
# RETENTION ANALYTICS
# =========================================================

render_section_header(
    title="Retention Performance",
    description=(
        "Monitor cohort retention and identify "
        "long-term engagement decline."
    ),
)

retention_figure = px.area(
    retention_dataframe,
    x="Cohort",
    y="Retention Rate",
    markers=True,
    title="Player Retention by Cohort",
)

retention_figure.update_layout(
    height=360,
    margin=dict(
        l=20,
        r=20,
        t=60,
        b=20,
    ),
    xaxis_title=None,
    yaxis_title="Retention Rate",
    yaxis_tickformat=".0%",
)

retention_figure.update_traces(
    line_width=3,
)

st.plotly_chart(
    retention_figure,
    use_container_width=True,
)


# =========================================================
# HIGH-RISK PLAYER TABLE
# =========================================================

render_section_header(
    title="High-Priority Retention Queue",
    description=(
        "Players ranked by churn probability, "
        "lifetime value, and inactivity."
    ),
)

filtered_players = high_risk_dataframe.copy()

filtered_players = filtered_players[
    filtered_players["Churn Probability"]
    >= minimum_probability
]

if selected_segment != "All Segments":
    filtered_players = filtered_players[
        filtered_players["Segment"]
        == selected_segment
    ]

if selected_risk != "All Risk Levels":
    risk_thresholds = {
        "Low Risk": (0.0, 0.40),
        "Medium Risk": (0.40, 0.70),
        "High Risk": (0.70, 0.90),
        "Critical Risk": (0.90, 1.01),
    }

    lower_bound, upper_bound = risk_thresholds[
        selected_risk
    ]

    filtered_players = filtered_players[
        (
            filtered_players["Churn Probability"]
            >= lower_bound
        )
        & (
            filtered_players["Churn Probability"]
            < upper_bound
        )
    ]

download_dataframe = filtered_players.copy()

download_dataframe["Churn Probability"] = (
    download_dataframe["Churn Probability"]
    .mul(100)
    .round(1)
    .astype(str)
    .add("%")
)

download_data = download_dataframe.to_csv(
    index=False
).encode("utf-8")

st.download_button(
    label="Download Retention Queue",
    data=download_data,
    file_name="high_risk_players.csv",
    mime="text/csv",
)

st.dataframe(
    filtered_players,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Player ID": st.column_config.TextColumn(
            "Player ID"
        ),
        "Segment": st.column_config.TextColumn(
            "Segment"
        ),
        "Churn Probability": st.column_config.ProgressColumn(
            "Churn Probability",
            min_value=0.0,
            max_value=1.0,
            format="%.0f%%",
        ),
        "Lifetime Value": st.column_config.NumberColumn(
            "Lifetime Value",
            format="$%d",
        ),
        "Days Since Last Visit": st.column_config.NumberColumn(
            "Days Since Last Visit",
            format="%d days",
        ),
        "Recommended Action": st.column_config.TextColumn(
            "Recommended Action"
        ),
    },
)

if filtered_players.empty:
    st.info(
        "No players match the selected filters."
    )
else:
    st.success(
        f"{len(filtered_players)} high-priority players "
        "match the selected retention criteria."
    )


# =========================================================
# FOOTER
# =========================================================

render_last_updated()
render_footer()
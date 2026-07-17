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


def build_revenue_data() -> pd.DataFrame:
    today = datetime.now().date()

    dates = [
        today - timedelta(days=index)
        for index in range(29, -1, -1)
    ]

    revenue = [
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

    return pd.DataFrame(
        {
            "Date": dates,
            "Net Gaming Revenue": revenue,
        }
    )


def build_location_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Location": [
                "Buffalo Central",
                "Niagara East",
                "Rochester North",
                "Buffalo West",
                "Syracuse Central",
            ],
            "Revenue": [
                84200,
                67300,
                59200,
                46100,
                32481,
            ],
        }
    )


def build_game_type_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Game Type": [
                "Video Slots",
                "Progressive",
                "Table Games",
                "Electronic Tables",
            ],
            "Revenue": [
                142300,
                68100,
                49300,
                29581,
            ],
        }
    )


def build_hourly_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Hour": [
                "8 AM",
                "10 AM",
                "12 PM",
                "2 PM",
                "4 PM",
                "6 PM",
                "8 PM",
                "10 PM",
                "12 AM",
            ],
            "Revenue": [
                5200,
                7100,
                9400,
                11800,
                13700,
                16400,
                18900,
                17300,
                11200,
            ],
        }
    )


render_page_header(
    title="Revenue Analytics",
    subtitle=(
        "Analyze gaming revenue by location, machine, "
        "game type, hour, and reporting period."
    ),
    badge_text="Revenue Intelligence",
)

revenue_dataframe = build_revenue_data()
location_dataframe = build_location_data()
game_type_dataframe = build_game_type_data()
hourly_dataframe = build_hourly_data()

total_revenue = revenue_dataframe[
    "Net Gaming Revenue"
].sum()

average_daily_revenue = revenue_dataframe[
    "Net Gaming Revenue"
].mean()

peak_revenue = revenue_dataframe[
    "Net Gaming Revenue"
].max()

peak_date = revenue_dataframe.loc[
    revenue_dataframe[
        "Net Gaming Revenue"
    ].idxmax(),
    "Date",
]

render_metric_grid(
    metrics=[
        {
            "label": "30-Day Revenue",
            "value": f"${total_revenue:,.0f}",
            "delta": "8.7% growth",
        },
        {
            "label": "Average Daily Revenue",
            "value": f"${average_daily_revenue:,.0f}",
            "delta": "4.2% increase",
        },
        {
            "label": "Peak Daily Revenue",
            "value": f"${peak_revenue:,.0f}",
            "delta": str(peak_date),
        },
        {
            "label": "Actual Hold",
            "value": "9.0%",
            "delta": "0.4% above target",
        },
    ],
    columns=4,
)

st.divider()

filter_column_1, filter_column_2, filter_column_3 = st.columns(3)

with filter_column_1:
    selected_period = st.selectbox(
        "Reporting period",
        [
            "Last 7 days",
            "Last 14 days",
            "Last 30 days",
        ],
        index=2,
    )

with filter_column_2:
    selected_location = st.selectbox(
        "Location",
        [
            "All Locations",
            *location_dataframe["Location"].tolist(),
        ],
    )

with filter_column_3:
    selected_metric = st.selectbox(
        "Revenue metric",
        [
            "Net Gaming Revenue",
            "Gross Gaming Revenue",
            "Average Daily Revenue",
        ],
    )

period_days = {
    "Last 7 days": 7,
    "Last 14 days": 14,
    "Last 30 days": 30,
}[selected_period]

filtered_revenue = revenue_dataframe.tail(period_days)

render_section_header(
    title="Revenue Performance",
    description=(
        "Track daily gaming revenue performance and "
        "identify peak and declining periods."
    ),
)

revenue_figure = px.area(
    filtered_revenue,
    x="Date",
    y="Net Gaming Revenue",
    markers=True,
    title=f"{selected_period} Revenue Trend",
)

revenue_figure.update_layout(
    height=420,
    margin=dict(
        l=20,
        r=20,
        t=60,
        b=20,
    ),
    hovermode="x unified",
    xaxis_title=None,
    yaxis_title="Revenue ($)",
)

revenue_figure.update_traces(
    line_width=3,
)

st.plotly_chart(
    revenue_figure,
    use_container_width=True,
)

render_section_header(
    title="Revenue Breakdown",
    description=(
        "Compare revenue contribution by property "
        "and game category."
    ),
)

left_column, right_column = st.columns(
    2,
    gap="large",
)

with left_column:
    location_figure = px.bar(
        location_dataframe.sort_values(
            "Revenue",
            ascending=True,
        ),
        x="Revenue",
        y="Location",
        orientation="h",
        text="Revenue",
        title="Revenue by Location",
    )

    location_figure.update_layout(
        height=390,
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

    location_figure.update_traces(
        texttemplate="$%{text:,.0f}",
        textposition="outside",
    )

    st.plotly_chart(
        location_figure,
        use_container_width=True,
    )

with right_column:
    game_type_figure = px.pie(
        game_type_dataframe,
        names="Game Type",
        values="Revenue",
        hole=0.58,
        title="Revenue by Game Type",
    )

    game_type_figure.update_layout(
        height=390,
        margin=dict(
            l=20,
            r=20,
            t=60,
            b=20,
        ),
        legend_title=None,
    )

    game_type_figure.update_traces(
        textinfo="percent+label",
    )

    st.plotly_chart(
        game_type_figure,
        use_container_width=True,
    )

render_section_header(
    title="Hourly Revenue Pattern",
    description=(
        "Understand peak customer activity and "
        "high-revenue operating periods."
    ),
)

hourly_figure = px.line(
    hourly_dataframe,
    x="Hour",
    y="Revenue",
    markers=True,
    title="Revenue by Hour",
)

hourly_figure.update_layout(
    height=380,
    margin=dict(
        l=20,
        r=20,
        t=60,
        b=20,
    ),
    xaxis_title=None,
    yaxis_title="Revenue ($)",
)

hourly_figure.update_traces(
    line_width=3,
)

st.plotly_chart(
    hourly_figure,
    use_container_width=True,
)

render_section_header(
    title="Revenue Detail",
    description=(
        "Review daily revenue records and export "
        "the current reporting dataset."
    ),
)

download_data = filtered_revenue.to_csv(
    index=False
).encode("utf-8")

st.download_button(
    label="Download Revenue CSV",
    data=download_data,
    file_name="revenue_analytics.csv",
    mime="text/csv",
    use_container_width=False,
)

st.dataframe(
    filtered_revenue.sort_values(
        "Date",
        ascending=False,
    ),
    use_container_width=True,
    hide_index=True,
    column_config={
        "Date": st.column_config.DateColumn(
            "Date",
            format="MMM DD, YYYY",
        ),
        "Net Gaming Revenue": st.column_config.NumberColumn(
            "Net Gaming Revenue",
            format="$%.2f",
        ),
    },
)

st.success(
    "Revenue monitoring is operational. "
    "The strongest revenue window is currently "
    "between 6 PM and 10 PM."
)

render_last_updated()
render_footer()
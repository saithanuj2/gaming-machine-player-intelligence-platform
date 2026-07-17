from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


PLOTLY_CONFIG = {
    "displaylogo": False,
    "responsive": True,
    "modeBarButtonsToRemove": [
        "lasso2d",
        "select2d",
    ],
}


def apply_chart_layout(
    figure: go.Figure,
    title: str,
    height: int = 400,
) -> go.Figure:
    """Apply consistent business-dashboard chart styling."""

    figure.update_layout(
        title={
            "text": title,
            "x": 0.01,
            "xanchor": "left",
        },
        height=height,
        margin={
            "l": 20,
            "r": 20,
            "t": 60,
            "b": 20,
        },
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend_title_text="",
        hovermode="x unified",
    )

    figure.update_xaxes(
        showgrid=False,
    )

    figure.update_yaxes(
        gridcolor="rgba(148,163,184,0.20)",
    )

    return figure


def create_revenue_trend_chart(
    dataframe: pd.DataFrame,
    date_column: str,
    revenue_column: str,
    title: str = "Revenue Trend",
) -> go.Figure:
    """Create a revenue line and area chart."""

    figure = px.area(
        dataframe,
        x=date_column,
        y=revenue_column,
        markers=True,
    )

    figure.update_traces(
        line={
            "width": 3,
        },
        fill="tozeroy",
    )

    figure.update_yaxes(
        tickprefix="$",
        tickformat=",.0f",
    )

    return apply_chart_layout(
        figure,
        title,
        height=420,
    )


def create_actual_vs_forecast_chart(
    dataframe: pd.DataFrame,
    date_column: str,
    actual_column: str,
    forecast_column: str,
    title: str,
) -> go.Figure:
    """Create actual versus forecast line chart."""

    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=dataframe[date_column],
            y=dataframe[actual_column],
            mode="lines+markers",
            name="Actual Revenue",
            line={
                "width": 3,
            },
        )
    )

    figure.add_trace(
        go.Scatter(
            x=dataframe[date_column],
            y=dataframe[forecast_column],
            mode="lines+markers",
            name="Forecast Revenue",
            line={
                "width": 3,
                "dash": "dash",
            },
        )
    )

    figure.update_yaxes(
        tickprefix="$",
        tickformat=",.0f",
    )

    return apply_chart_layout(
        figure,
        title,
        height=430,
    )


def create_category_bar_chart(
    dataframe: pd.DataFrame,
    category_column: str,
    value_column: str,
    title: str,
    orientation: str = "v",
) -> go.Figure:
    """Create a reusable category bar chart."""

    if orientation == "h":
        figure = px.bar(
            dataframe,
            x=value_column,
            y=category_column,
            orientation="h",
        )
    else:
        figure = px.bar(
            dataframe,
            x=category_column,
            y=value_column,
        )

    figure.update_traces(
        texttemplate="%{y:,.0f}"
        if orientation == "v"
        else "%{x:,.0f}",
        textposition="outside",
    )

    return apply_chart_layout(
        figure,
        title,
        height=400,
    )


def create_donut_chart(
    dataframe: pd.DataFrame,
    name_column: str,
    value_column: str,
    title: str,
) -> go.Figure:
    """Create a reusable donut chart."""

    figure = px.pie(
        dataframe,
        names=name_column,
        values=value_column,
        hole=0.60,
    )

    figure.update_traces(
        textposition="inside",
        textinfo="percent+label",
    )

    return apply_chart_layout(
        figure,
        title,
        height=400,
    )


def create_risk_gauge(
    value: float,
    title: str,
    maximum: float = 1.0,
) -> go.Figure:
    """Create a risk or probability gauge."""

    figure = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            number={
                "valueformat": ".1%",
            },
            title={
                "text": title,
            },
            gauge={
                "axis": {
                    "range": [
                        0,
                        maximum,
                    ],
                    "tickformat": ".0%",
                },
                "steps": [
                    {
                        "range": [
                            0,
                            maximum * 0.40,
                        ],
                        "color": "#dcfce7",
                    },
                    {
                        "range": [
                            maximum * 0.40,
                            maximum * 0.70,
                        ],
                        "color": "#fef3c7",
                    },
                    {
                        "range": [
                            maximum * 0.70,
                            maximum,
                        ],
                        "color": "#fee2e2",
                    },
                ],
            },
        )
    )

    figure.update_layout(
        height=320,
        margin={
            "l": 20,
            "r": 20,
            "t": 60,
            "b": 20,
        },
        paper_bgcolor="rgba(0,0,0,0)",
    )

    return figure
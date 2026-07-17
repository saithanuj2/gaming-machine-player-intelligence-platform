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
# SAMPLE AI / ML DATA
# Replace with FastAPI and real model outputs later.
# =========================================================

def build_revenue_forecast() -> pd.DataFrame:
    today = datetime.now().date()

    dates = [
        today - timedelta(days=index)
        for index in range(20, -1, -1)
    ]

    actual_revenue = [
        11800,
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
        15100,
        15350,
        15600,
        15800,
        16050,
        16200,
    ]

    predicted_revenue = [
        11650,
        12020,
        12280,
        12100,
        12610,
        13120,
        12940,
        13310,
        13620,
        13400,
        13810,
        14140,
        14210,
        14520,
        14820,
        15010,
        15260,
        15510,
        15740,
        15920,
        16110,
    ]

    lower_bound = [
        value * 0.94
        for value in predicted_revenue
    ]

    upper_bound = [
        value * 1.06
        for value in predicted_revenue
    ]

    return pd.DataFrame(
        {
            "Date": dates,
            "Actual Revenue": actual_revenue,
            "Predicted Revenue": predicted_revenue,
            "Lower Confidence": lower_bound,
            "Upper Confidence": upper_bound,
        }
    )


def build_model_comparison() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Model": [
                "Linear Regression",
                "Random Forest",
                "XGBoost",
                "LSTM",
            ],
            "RMSE": [
                1840,
                1260,
                980,
                1120,
            ],
            "MAE": [
                1420,
                920,
                710,
                830,
            ],
            "MAPE": [
                0.112,
                0.081,
                0.068,
                0.074,
            ],
            "R2 Score": [
                0.72,
                0.86,
                0.91,
                0.89,
            ],
        }
    )


def build_churn_model_metrics() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Metric": [
                "Precision",
                "Recall",
                "F1 Score",
                "ROC-AUC",
                "Accuracy",
            ],
            "Score": [
                0.92,
                0.91,
                0.915,
                0.94,
                0.93,
            ],
        }
    )


def build_failure_model_metrics() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Metric": [
                "Precision",
                "Recall",
                "F1 Score",
                "ROC-AUC",
                "Accuracy",
            ],
            "Score": [
                0.88,
                0.86,
                0.87,
                0.89,
                0.90,
            ],
        }
    )


def build_churn_predictions() -> pd.DataFrame:
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
            "Predicted Class": [
                "Churn",
                "Churn",
                "Churn",
                "Churn",
                "Churn",
                "Churn",
                "Churn",
                "Churn",
            ],
            "Primary Driver": [
                "Long inactivity",
                "Declining visits",
                "Low recent spend",
                "Reduced engagement",
                "High inactivity",
                "Visit-frequency decline",
                "Reduced session length",
                "No recent promotion response",
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


def build_machine_predictions() -> pd.DataFrame:
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
            ],
            "Predicted Failure Window": [
                "0-2 days",
                "0-3 days",
                "1-4 days",
                "2-5 days",
                "3-7 days",
                "4-8 days",
                "5-10 days",
                "7-14 days",
            ],
            "Primary Driver": [
                "Power instability",
                "Bill-validator faults",
                "Network disconnects",
                "Temperature alerts",
                "Door-sensor errors",
                "Printer faults",
                "Card-reader failures",
                "Repeated restart events",
            ],
            "Recommended Action": [
                "Immediate inspection",
                "Emergency service",
                "Replace network module",
                "Inspect cooling system",
                "Review sensor assembly",
                "Schedule maintenance",
                "Inspect card reader",
                "Monitor and diagnose",
            ],
        }
    )


def build_feature_importance() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Feature": [
                "Days Since Last Visit",
                "Visit Frequency",
                "Average Spend",
                "Session Duration",
                "Critical Events",
                "Downtime Minutes",
                "Temperature Alerts",
                "Last Service Days",
            ],
            "Importance": [
                0.21,
                0.18,
                0.15,
                0.12,
                0.11,
                0.09,
                0.08,
                0.06,
            ],
            "Model": [
                "Churn",
                "Churn",
                "Churn",
                "Churn",
                "Failure",
                "Failure",
                "Failure",
                "Failure",
            ],
        }
    )


def build_drift_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Monitoring Period": [
                "Week 1",
                "Week 2",
                "Week 3",
                "Week 4",
                "Week 5",
                "Week 6",
            ],
            "Churn Drift Score": [
                0.07,
                0.09,
                0.11,
                0.13,
                0.16,
                0.18,
            ],
            "Failure Drift Score": [
                0.05,
                0.08,
                0.10,
                0.12,
                0.14,
                0.17,
            ],
        }
    )


# =========================================================
# PAGE HEADER
# =========================================================

render_page_header(
    title="AI Predictions",
    subtitle=(
        "Review revenue forecasts, churn predictions, "
        "machine failure risk, model performance, and drift."
    ),
    badge_text="AI Decision Intelligence",
)


# =========================================================
# LOAD DATA
# =========================================================

revenue_forecast_dataframe = build_revenue_forecast()
model_comparison_dataframe = build_model_comparison()
churn_metrics_dataframe = build_churn_model_metrics()
failure_metrics_dataframe = build_failure_model_metrics()
churn_predictions_dataframe = build_churn_predictions()
machine_predictions_dataframe = build_machine_predictions()
feature_importance_dataframe = build_feature_importance()
drift_dataframe = build_drift_data()


# =========================================================
# KPI CARDS
# =========================================================

render_metric_grid(
    metrics=[
        {
            "label": "Forecast MAPE",
            "value": "6.8%",
            "delta": "Within target",
        },
        {
            "label": "Forecast R²",
            "value": "0.91",
            "delta": "Strong fit",
        },
        {
            "label": "Churn Precision",
            "value": "92%",
            "delta": "Validated",
        },
        {
            "label": "Churn Recall",
            "value": "91%",
            "delta": "Validated",
        },
        {
            "label": "Failure ROC-AUC",
            "value": "0.89",
            "delta": "Strong discrimination",
        },
        {
            "label": "High-Risk Players",
            "value": "576",
            "delta": "Retention action required",
            "delta_color": "inverse",
        },
        {
            "label": "High-Risk Machines",
            "value": "8",
            "delta": "Maintenance required",
            "delta_color": "inverse",
        },
        {
            "label": "Model Status",
            "value": "Operational",
            "delta": "No retraining required",
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
    selected_prediction_type = st.selectbox(
        "Prediction type",
        [
            "All Predictions",
            "Revenue Forecast",
            "Player Churn",
            "Machine Failure",
        ],
    )

with filter_column_2:
    minimum_probability = st.slider(
        "Minimum risk probability",
        min_value=0.0,
        max_value=1.0,
        value=0.80,
        step=0.05,
    )

with filter_column_3:
    selected_model = st.selectbox(
        "Forecast model",
        model_comparison_dataframe["Model"].tolist(),
        index=2,
    )


# =========================================================
# REVENUE FORECAST
# =========================================================

if selected_prediction_type in [
    "All Predictions",
    "Revenue Forecast",
]:
    render_section_header(
        title="Revenue Forecasting",
        description=(
            "Compare actual and predicted gaming revenue "
            "with confidence intervals."
        ),
    )

    forecast_figure = px.line(
        revenue_forecast_dataframe,
        x="Date",
        y=[
            "Actual Revenue",
            "Predicted Revenue",
        ],
        markers=True,
        title="Actual vs Predicted Revenue",
    )

    forecast_figure.add_scatter(
        x=revenue_forecast_dataframe["Date"],
        y=revenue_forecast_dataframe["Upper Confidence"],
        mode="lines",
        line=dict(width=0),
        showlegend=False,
        hoverinfo="skip",
    )

    forecast_figure.add_scatter(
        x=revenue_forecast_dataframe["Date"],
        y=revenue_forecast_dataframe["Lower Confidence"],
        mode="lines",
        fill="tonexty",
        line=dict(width=0),
        name="Confidence Interval",
        hoverinfo="skip",
    )

    forecast_figure.update_layout(
        height=430,
        margin=dict(
            l=20,
            r=20,
            t=60,
            b=20,
        ),
        hovermode="x unified",
        xaxis_title=None,
        yaxis_title="Revenue ($)",
        legend_title=None,
    )

    forecast_figure.update_traces(
        line_width=3,
        selector=dict(
            type="scatter",
            mode="lines+markers",
        ),
    )

    st.plotly_chart(
        forecast_figure,
        use_container_width=True,
    )

    left_column, right_column = st.columns(
        2,
        gap="large",
    )

    with left_column:
        comparison_figure = px.bar(
            model_comparison_dataframe,
            x="Model",
            y="MAPE",
            text="MAPE",
            title="Forecast Model Error Comparison",
        )

        comparison_figure.update_layout(
            height=380,
            margin=dict(
                l=20,
                r=20,
                t=60,
                b=20,
            ),
            xaxis_title=None,
            yaxis_title="MAPE",
            yaxis_tickformat=".0%",
            showlegend=False,
        )

        comparison_figure.update_traces(
            texttemplate="%{text:.1%}",
            textposition="outside",
        )

        st.plotly_chart(
            comparison_figure,
            use_container_width=True,
        )

    with right_column:
        selected_model_row = (
            model_comparison_dataframe[
                model_comparison_dataframe["Model"]
                == selected_model
            ]
            .iloc[0]
        )

        st.subheader(
            f"{selected_model} Performance"
        )

        st.metric(
            "RMSE",
            f"${selected_model_row['RMSE']:,.0f}",
        )

        st.metric(
            "MAE",
            f"${selected_model_row['MAE']:,.0f}",
        )

        st.metric(
            "MAPE",
            f"{selected_model_row['MAPE']:.1%}",
        )

        st.metric(
            "R² Score",
            f"{selected_model_row['R2 Score']:.2f}",
        )


# =========================================================
# CLASSIFICATION MODEL METRICS
# =========================================================

render_section_header(
    title="Classification Model Performance",
    description=(
        "Evaluate churn and machine-failure models "
        "using precision, recall, F1 score, ROC-AUC, and accuracy."
    ),
)

left_column, right_column = st.columns(
    2,
    gap="large",
)

with left_column:
    churn_metric_figure = px.bar(
        churn_metrics_dataframe,
        x="Metric",
        y="Score",
        text="Score",
        title="Player Churn Model Metrics",
    )

    churn_metric_figure.update_layout(
        height=380,
        margin=dict(
            l=20,
            r=20,
            t=60,
            b=20,
        ),
        xaxis_title=None,
        yaxis_title="Score",
        yaxis_tickformat=".0%",
        yaxis_range=[
            0,
            1,
        ],
        showlegend=False,
    )

    churn_metric_figure.update_traces(
        texttemplate="%{text:.1%}",
        textposition="outside",
    )

    st.plotly_chart(
        churn_metric_figure,
        use_container_width=True,
    )

with right_column:
    failure_metric_figure = px.bar(
        failure_metrics_dataframe,
        x="Metric",
        y="Score",
        text="Score",
        title="Machine Failure Model Metrics",
    )

    failure_metric_figure.update_layout(
        height=380,
        margin=dict(
            l=20,
            r=20,
            t=60,
            b=20,
        ),
        xaxis_title=None,
        yaxis_title="Score",
        yaxis_tickformat=".0%",
        yaxis_range=[
            0,
            1,
        ],
        showlegend=False,
    )

    failure_metric_figure.update_traces(
        texttemplate="%{text:.1%}",
        textposition="outside",
    )

    st.plotly_chart(
        failure_metric_figure,
        use_container_width=True,
    )


# =========================================================
# PLAYER CHURN PREDICTIONS
# =========================================================

if selected_prediction_type in [
    "All Predictions",
    "Player Churn",
]:
    render_section_header(
        title="Player Churn Predictions",
        description=(
            "Players ranked by predicted churn risk, "
            "business value, model drivers, and recommended actions."
        ),
    )

    filtered_churn_predictions = (
        churn_predictions_dataframe[
            churn_predictions_dataframe[
                "Churn Probability"
            ]
            >= minimum_probability
        ]
        .copy()
        .sort_values(
            "Churn Probability",
            ascending=False,
        )
    )

    churn_download = (
        filtered_churn_predictions.copy()
    )

    churn_download[
        "Churn Probability"
    ] = (
        churn_download[
            "Churn Probability"
        ]
        .mul(100)
        .round(1)
        .astype(str)
        .add("%")
    )

    st.download_button(
        label="Download Churn Predictions",
        data=churn_download.to_csv(
            index=False
        ).encode("utf-8"),
        file_name="player_churn_predictions.csv",
        mime="text/csv",
    )

    st.dataframe(
        filtered_churn_predictions,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Player ID": st.column_config.TextColumn(
                "Player ID"
            ),
            "Segment": st.column_config.TextColumn(
                "Segment"
            ),
            "Churn Probability":
                st.column_config.ProgressColumn(
                    "Churn Probability",
                    min_value=0.0,
                    max_value=1.0,
                    format="%.0f%%",
                ),
            "Predicted Class":
                st.column_config.TextColumn(
                    "Predicted Class"
                ),
            "Primary Driver":
                st.column_config.TextColumn(
                    "Primary Driver"
                ),
            "Recommended Action":
                st.column_config.TextColumn(
                    "Recommended Action"
                ),
        },
    )

    if filtered_churn_predictions.empty:
        st.info(
            "No player predictions match the selected threshold."
        )
    else:
        st.success(
            f"{len(filtered_churn_predictions)} players "
            "match the selected churn-risk threshold."
        )


# =========================================================
# MACHINE FAILURE PREDICTIONS
# =========================================================

if selected_prediction_type in [
    "All Predictions",
    "Machine Failure",
]:
    render_section_header(
        title="Machine Failure Predictions",
        description=(
            "Machines ranked by failure probability, "
            "predicted failure window, model drivers, and service actions."
        ),
    )

    filtered_machine_predictions = (
        machine_predictions_dataframe[
            machine_predictions_dataframe[
                "Failure Probability"
            ]
            >= minimum_probability
        ]
        .copy()
        .sort_values(
            "Failure Probability",
            ascending=False,
        )
    )

    machine_download = (
        filtered_machine_predictions.copy()
    )

    machine_download[
        "Failure Probability"
    ] = (
        machine_download[
            "Failure Probability"
        ]
        .mul(100)
        .round(1)
        .astype(str)
        .add("%")
    )

    st.download_button(
        label="Download Failure Predictions",
        data=machine_download.to_csv(
            index=False
        ).encode("utf-8"),
        file_name="machine_failure_predictions.csv",
        mime="text/csv",
    )

    st.dataframe(
        filtered_machine_predictions,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Machine ID":
                st.column_config.TextColumn(
                    "Machine ID"
                ),
            "Location":
                st.column_config.TextColumn(
                    "Location"
                ),
            "Failure Probability":
                st.column_config.ProgressColumn(
                    "Failure Probability",
                    min_value=0.0,
                    max_value=1.0,
                    format="%.0f%%",
                ),
            "Predicted Failure Window":
                st.column_config.TextColumn(
                    "Predicted Failure Window"
                ),
            "Primary Driver":
                st.column_config.TextColumn(
                    "Primary Driver"
                ),
            "Recommended Action":
                st.column_config.TextColumn(
                    "Recommended Action"
                ),
        },
    )

    if filtered_machine_predictions.empty:
        st.info(
            "No machine predictions match the selected threshold."
        )
    else:
        st.warning(
            f"{len(filtered_machine_predictions)} machines "
            "require review based on the selected threshold."
        )


# =========================================================
# FEATURE IMPORTANCE
# =========================================================

render_section_header(
    title="Explainable AI",
    description=(
        "Review the most influential features driving "
        "churn and machine-failure predictions."
    ),
)

feature_figure = px.bar(
    feature_importance_dataframe.sort_values(
        "Importance",
        ascending=True,
    ),
    x="Importance",
    y="Feature",
    orientation="h",
    color="Model",
    text="Importance",
    title="Model Feature Importance",
)

feature_figure.update_layout(
    height=430,
    margin=dict(
        l=20,
        r=20,
        t=60,
        b=20,
    ),
    xaxis_title="Relative Importance",
    yaxis_title=None,
    xaxis_tickformat=".0%",
    legend_title=None,
)

feature_figure.update_traces(
    texttemplate="%{text:.1%}",
    textposition="outside",
)

st.plotly_chart(
    feature_figure,
    use_container_width=True,
)


# =========================================================
# MODEL DRIFT MONITORING
# =========================================================

render_section_header(
    title="Model Monitoring and Drift",
    description=(
        "Monitor prediction stability and identify "
        "when retraining may be required."
    ),
)

drift_figure = px.line(
    drift_dataframe,
    x="Monitoring Period",
    y=[
        "Churn Drift Score",
        "Failure Drift Score",
    ],
    markers=True,
    title="Weekly Model Drift Scores",
)

drift_figure.add_hline(
    y=0.20,
    line_dash="dash",
    annotation_text="Retraining Threshold",
)

drift_figure.update_layout(
    height=390,
    margin=dict(
        l=20,
        r=20,
        t=60,
        b=20,
    ),
    xaxis_title=None,
    yaxis_title="Drift Score",
    yaxis_tickformat=".0%",
    legend_title=None,
)

drift_figure.update_traces(
    line_width=3,
)

st.plotly_chart(
    drift_figure,
    use_container_width=True,
)

latest_churn_drift = drift_dataframe[
    "Churn Drift Score"
].iloc[-1]

latest_failure_drift = drift_dataframe[
    "Failure Drift Score"
].iloc[-1]

if (
    latest_churn_drift >= 0.20
    or latest_failure_drift >= 0.20
):
    st.error(
        "One or more models have crossed the retraining threshold."
    )
elif (
    latest_churn_drift >= 0.15
    or latest_failure_drift >= 0.15
):
    st.warning(
        "Model drift is increasing. Continue monitoring "
        "and prepare the next retraining cycle."
    )
else:
    st.success(
        "All monitored models remain within approved drift thresholds."
    )


# =========================================================
# MODEL GOVERNANCE SUMMARY
# =========================================================

with st.expander(
    "Model governance and validation summary"
):
    st.markdown(
        """
        **Revenue forecasting**
        - XGBoost selected because it produced the lowest MAPE and RMSE.
        - Performance is monitored using RMSE, MAE, MAPE, and R².
        - Confidence intervals are included for operational planning.

        **Player churn model**
        - Evaluated using Precision, Recall, F1 Score, ROC-AUC, and Accuracy.
        - Precision is emphasized to reduce unnecessary retention offers.
        - Recall is monitored to avoid missing high-risk players.

        **Machine failure model**
        - Evaluated using Precision, Recall, F1 Score, ROC-AUC, and Accuracy.
        - Predictions are combined with critical events and service history.
        - High-risk machines are routed to predictive-maintenance workflows.

        **Monitoring**
        - Drift scores are reviewed weekly.
        - Retraining is triggered when drift exceeds the approved threshold.
        - Model inputs, versions, metrics, and predictions should be logged.
        """
    )


# =========================================================
# FOOTER
# =========================================================

render_last_updated()
render_footer()
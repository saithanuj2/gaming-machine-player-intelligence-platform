from typing import Any

import streamlit as st


def render_metric_card(
    label: str,
    value: str,
    delta: str | None = None,
    help_text: str | None = None,
    delta_color: str = "normal",
) -> None:
    """Render one native Streamlit KPI card."""

    st.metric(
        label=label,
        value=value,
        delta=delta,
        help=help_text,
        delta_color=delta_color,
        border=True,
    )


def render_metric_grid(
    metrics: list[dict[str, Any]],
    columns: int = 4,
) -> None:
    """Render KPI cards in a responsive grid."""

    if not metrics:
        st.info("No KPI data is available.")
        return

    column_count = max(
        1,
        min(int(columns), 6),
    )

    for start_index in range(
        0,
        len(metrics),
        column_count,
    ):
        row_metrics = metrics[
            start_index:start_index + column_count
        ]

        metric_columns = st.columns(
            column_count,
            gap="medium",
        )

        for index, metric in enumerate(row_metrics):
            with metric_columns[index]:
                render_metric_card(
                    label=str(metric.get("label", "")),
                    value=str(metric.get("value", "0")),
                    delta=metric.get("delta"),
                    help_text=metric.get("help"),
                    delta_color=str(
                        metric.get(
                            "delta_color",
                            "normal",
                        )
                    ),
                )


def render_progress_kpi(
    label: str,
    value: float,
    display_value: str,
    threshold: float,
    help_text: str | None = None,
) -> None:
    """Render a KPI with a progress indicator."""

    normalized_value = max(
        0.0,
        min(float(value), 1.0),
    )

    with st.container(border=True):
        st.markdown(f"**{label}**")
        st.markdown(f"### {display_value}")
        st.progress(normalized_value)
        st.caption(f"Target: {threshold:.0%}")

        if help_text:
            st.caption(help_text)


def render_compact_metric(
    label: str,
    value: str,
    status: str | None = None,
) -> None:
    """Render a compact KPI card."""

    with st.container(border=True):
        st.caption(label)
        st.markdown(f"### {value}")

        if status:
            st.caption(status)
from datetime import datetime
from typing import Any

import streamlit as st


def render_page_header(
    title: str,
    subtitle: str,
    badge_text: str | None = None,
    badge_status: str = "live",
) -> None:
    """Render the main business-page header."""

    badge_class = {
        "live": "header-badge-live",
        "warning": "header-badge-warning",
        "critical": "header-badge-critical",
        "neutral": "header-badge-neutral",
    }.get(
        badge_status.lower(),
        "header-badge-neutral",
    )

    badge_html = ""

    if badge_text:
        badge_html = (
            f'<span class="{badge_class}">'
            f"{badge_text}"
            "</span>"
        )

    st.markdown(
        f"""
        <div class="dashboard-header">
            <div class="header-content">
                <div>
                    <h1 class="dashboard-title">
                        {title}
                    </h1>
                    <p class="dashboard-subtitle">
                        {subtitle}
                    </p>
                </div>
                {badge_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_header(
    title: str,
    description: str | None = None,
    action_text: str | None = None,
) -> None:
    """Render a consistent dashboard section heading."""

    description_html = ""

    if description:
        description_html = (
            f'<p class="section-description">'
            f"{description}"
            "</p>"
        )

    action_html = ""

    if action_text:
        action_html = (
            f'<span class="section-action">'
            f"{action_text}"
            "</span>"
        )

    st.markdown(
        f"""
        <div class="section-header">
            <div>
                <h3>{title}</h3>
                {description_html}
            </div>
            {action_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_status_badge(
    label: str,
    status: str,
    details: str | None = None,
) -> None:
    """Render a service or business-status badge."""

    normalized_status = status.lower()

    class_name = {
        "healthy": "status-success",
        "online": "status-success",
        "success": "status-success",
        "active": "status-success",
        "warning": "status-warning",
        "degraded": "status-warning",
        "medium": "status-warning",
        "critical": "status-error",
        "offline": "status-error",
        "failed": "status-error",
        "high": "status-error",
        "low": "status-neutral",
        "unknown": "status-neutral",
    }.get(
        normalized_status,
        "status-neutral",
    )

    details_html = ""

    if details:
        details_html = (
            f'<span class="status-details">'
            f"{details}"
            "</span>"
        )

    st.markdown(
        f"""
        <div class="status-row">
            <div>
                <span class="status-label">
                    {label}
                </span>
                {details_html}
            </div>

            <span class="{class_name}">
                ● {status.title()}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_filter_summary(
    filters: dict[str, Any],
) -> None:
    """Show currently applied dashboard filters."""

    active_filters = {
        key: value
        for key, value in filters.items()
        if value not in (
            None,
            "",
            "All",
            [],
        )
    }

    if not active_filters:
        return

    filter_text = " · ".join(
        f"{key.replace('_', ' ').title()}: {value}"
        for key, value in active_filters.items()
    )

    st.markdown(
        f"""
        <div class="filter-summary">
            <strong>Active Filters:</strong>
            {filter_text}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_last_updated(
    timestamp: Any = None,
) -> None:
    """Render a last-refreshed timestamp."""

    if timestamp is None:
        formatted_timestamp = datetime.now().strftime(
            "%b %d, %Y %I:%M:%S %p"
        )

    else:
        try:
            parsed_timestamp = datetime.fromisoformat(
                str(timestamp).replace(
                    "Z",
                    "+00:00",
                )
            )

            formatted_timestamp = (
                parsed_timestamp.strftime(
                    "%b %d, %Y %I:%M:%S %p"
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            formatted_timestamp = str(
                timestamp
            )

    st.markdown(
        f"""
        <div class="last-updated">
            Last updated: {formatted_timestamp}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state(
    title: str,
    message: str,
    icon: str = "📭",
) -> None:
    """Render a reusable no-data state."""

    st.markdown(
        f"""
        <div class="empty-state">
            <div class="empty-state-icon">
                {icon}
            </div>
            <h4>{title}</h4>
            <p>{message}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_alert_banner(
    message: str,
    severity: str = "info",
) -> None:
    """Render a reusable operational alert banner."""

    class_name = {
        "info": "alert-info",
        "success": "alert-success",
        "warning": "alert-warning",
        "critical": "alert-critical",
    }.get(
        severity.lower(),
        "alert-info",
    )

    st.markdown(
        f"""
        <div class="{class_name}">
            {message}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_two_column_section(
    left_ratio: int = 2,
    right_ratio: int = 1,
) -> tuple[Any, Any]:
    """Create a standard two-column business layout."""

    return st.columns(
        [
            left_ratio,
            right_ratio,
        ],
        gap="large",
    )


def render_three_column_section() -> tuple[Any, Any, Any]:
    """Create a standard three-column layout."""

    return st.columns(
        3,
        gap="large",
    )


def render_footer() -> None:
    """Render the platform footer."""

    st.markdown(
        """
        <div class="dashboard-footer">
            <strong>
                Gaming Machine Player Intelligence Platform
            </strong>
            <br>
            SQL Server · FastAPI · Scikit-learn · Streamlit · Plotly
        </div>
        """,
        unsafe_allow_html=True,
    )
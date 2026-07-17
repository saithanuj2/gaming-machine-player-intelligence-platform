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
# SAMPLE OPERATIONS DATA
# Replace these datasets with FastAPI responses later.
# =========================================================

def build_alert_summary() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Alert Severity": [
                "Critical",
                "High",
                "Medium",
                "Low",
            ],
            "Alerts": [
                6,
                12,
                24,
                18,
            ],
        }
    )


def build_incident_trend() -> pd.DataFrame:
    today = datetime.now().date()

    dates = [
        today - timedelta(days=index)
        for index in range(29, -1, -1)
    ]

    opened_incidents = [
        18,
        16,
        21,
        17,
        19,
        15,
        14,
        18,
        16,
        13,
        15,
        12,
        14,
        11,
        13,
        10,
        12,
        9,
        11,
        8,
        10,
        9,
        8,
        7,
        9,
        6,
        8,
        7,
        6,
        5,
    ]

    resolved_incidents = [
        12,
        14,
        15,
        16,
        17,
        16,
        15,
        17,
        18,
        15,
        16,
        14,
        15,
        13,
        14,
        12,
        13,
        11,
        12,
        10,
        11,
        10,
        9,
        9,
        10,
        8,
        9,
        8,
        8,
        7,
    ]

    return pd.DataFrame(
        {
            "Date": dates,
            "Opened Incidents": opened_incidents,
            "Resolved Incidents": resolved_incidents,
        }
    )


def build_location_operations() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Location": [
                "Buffalo Central",
                "Niagara East",
                "Rochester North",
                "Buffalo West",
                "Syracuse Central",
            ],
            "Open Alerts": [
                16,
                13,
                11,
                9,
                7,
            ],
            "Active Machines": [
                24,
                19,
                18,
                16,
                15,
            ],
            "Technicians": [
                4,
                3,
                3,
                2,
                2,
            ],
            "Average Response Minutes": [
                14,
                17,
                19,
                21,
                23,
            ],
        }
    )


def build_ticket_queue() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Ticket ID": [
                "INC-1045",
                "INC-1042",
                "INC-1039",
                "INC-1036",
                "INC-1032",
                "INC-1029",
                "INC-1026",
                "INC-1021",
                "INC-1018",
                "INC-1014",
            ],
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
            "Issue Type": [
                "Power Supply",
                "Bill Validator",
                "Network Loss",
                "Temperature Alert",
                "Door Sensor",
                "Printer Fault",
                "Card Reader",
                "System Restart",
                "Ticket Dispenser",
                "Performance Degradation",
            ],
            "Severity": [
                "Critical",
                "Critical",
                "High",
                "High",
                "High",
                "Medium",
                "Medium",
                "Medium",
                "Low",
                "Low",
            ],
            "Status": [
                "In Progress",
                "Assigned",
                "In Progress",
                "Open",
                "Assigned",
                "In Progress",
                "Open",
                "Assigned",
                "Open",
                "Monitoring",
            ],
            "Assigned Technician": [
                "Alex Morgan",
                "Jordan Lee",
                "Priya Shah",
                "Unassigned",
                "Chris Allen",
                "Taylor Kim",
                "Unassigned",
                "Morgan Reed",
                "Unassigned",
                "Sam Patel",
            ],
            "Age Minutes": [
                52,
                67,
                83,
                95,
                118,
                134,
                149,
                162,
                185,
                210,
            ],
            "SLA Target Minutes": [
                60,
                60,
                120,
                120,
                120,
                240,
                240,
                240,
                360,
                360,
            ],
        }
    )


def build_technician_workload() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Technician": [
                "Alex Morgan",
                "Jordan Lee",
                "Priya Shah",
                "Chris Allen",
                "Taylor Kim",
                "Morgan Reed",
                "Sam Patel",
            ],
            "Open Tickets": [
                5,
                4,
                4,
                3,
                3,
                2,
                2,
            ],
            "Completed Today": [
                6,
                5,
                7,
                4,
                5,
                3,
                4,
            ],
            "Average Resolution Minutes": [
                42,
                48,
                39,
                55,
                51,
                61,
                58,
            ],
        }
    )


def build_issue_type_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Issue Type": [
                "Network Loss",
                "Bill Validator",
                "Door Sensor",
                "Printer Fault",
                "Temperature Alert",
                "Power Supply",
            ],
            "Incidents": [
                64,
                58,
                47,
                39,
                31,
                24,
            ],
        }
    )


# =========================================================
# PAGE HEADER
# =========================================================

render_page_header(
    title="Operations Center",
    subtitle=(
        "Manage critical alerts, maintenance tickets, "
        "technician workloads, incident status, and service priorities."
    ),
    badge_text="Live Operations",
)


# =========================================================
# LOAD DATA
# =========================================================

alert_summary_dataframe = build_alert_summary()
incident_trend_dataframe = build_incident_trend()
location_operations_dataframe = build_location_operations()
ticket_queue_dataframe = build_ticket_queue()
technician_workload_dataframe = build_technician_workload()
issue_type_dataframe = build_issue_type_data()


# =========================================================
# CALCULATE OPERATIONAL METRICS
# =========================================================

ticket_queue_dataframe["SLA Remaining Minutes"] = (
    ticket_queue_dataframe["SLA Target Minutes"]
    - ticket_queue_dataframe["Age Minutes"]
)

ticket_queue_dataframe["SLA Status"] = (
    ticket_queue_dataframe["SLA Remaining Minutes"]
    .apply(
        lambda value: (
            "Breached"
            if value < 0
            else "At Risk"
            if value <= 30
            else "Within SLA"
        )
    )
)

sla_breaches = int(
    (
        ticket_queue_dataframe["SLA Status"]
        == "Breached"
    ).sum()
)

critical_tickets = int(
    (
        ticket_queue_dataframe["Severity"]
        == "Critical"
    ).sum()
)

average_response = (
    location_operations_dataframe[
        "Average Response Minutes"
    ].mean()
)


# =========================================================
# KPI CARDS
# =========================================================

render_metric_grid(
    metrics=[
        {
            "label": "Open Alerts",
            "value": "60",
            "delta": "7 resolved today",
        },
        {
            "label": "Critical Tickets",
            "value": str(critical_tickets),
            "delta": "Immediate action",
            "delta_color": "inverse",
        },
        {
            "label": "SLA Breaches",
            "value": str(sla_breaches),
            "delta": "Requires escalation",
            "delta_color": "inverse",
        },
        {
            "label": "Active Technicians",
            "value": "14",
            "delta": "Across 5 locations",
        },
        {
            "label": "Average Response",
            "value": f"{average_response:.0f} min",
            "delta": "3 min faster",
        },
        {
            "label": "Resolved Today",
            "value": "34",
            "delta": "12.4% increase",
        },
        {
            "label": "Machines Online",
            "value": "92",
            "delta": "92% availability",
        },
        {
            "label": "First-Time Fix Rate",
            "value": "86.7%",
            "delta": "2.1% improvement",
        },
    ],
    columns=4,
)


# =========================================================
# OPERATIONS FILTERS
# =========================================================

st.divider()

filter_column_1, filter_column_2, filter_column_3, filter_column_4 = (
    st.columns(4)
)

with filter_column_1:
    selected_location = st.selectbox(
        "Location",
        [
            "All Locations",
            *ticket_queue_dataframe[
                "Location"
            ].drop_duplicates().tolist(),
        ],
    )

with filter_column_2:
    selected_severity = st.selectbox(
        "Severity",
        [
            "All Severities",
            "Critical",
            "High",
            "Medium",
            "Low",
        ],
    )

with filter_column_3:
    selected_status = st.selectbox(
        "Ticket status",
        [
            "All Statuses",
            *ticket_queue_dataframe[
                "Status"
            ].drop_duplicates().tolist(),
        ],
    )

with filter_column_4:
    selected_sla = st.selectbox(
        "SLA status",
        [
            "All SLA Statuses",
            "Within SLA",
            "At Risk",
            "Breached",
        ],
    )


# =========================================================
# INCIDENT AND ALERT OVERVIEW
# =========================================================

render_section_header(
    title="Incident and Alert Overview",
    description=(
        "Track incident volume, resolution performance, "
        "and active-alert severity."
    ),
)

left_column, right_column = st.columns(
    [2, 1],
    gap="large",
)

with left_column:
    incident_figure = px.line(
        incident_trend_dataframe,
        x="Date",
        y=[
            "Opened Incidents",
            "Resolved Incidents",
        ],
        markers=True,
        title="30-Day Incident Trend",
    )

    incident_figure.update_layout(
        height=400,
        margin=dict(
            l=20,
            r=20,
            t=60,
            b=20,
        ),
        hovermode="x unified",
        xaxis_title=None,
        yaxis_title="Incidents",
        legend_title=None,
    )

    incident_figure.update_traces(
        line_width=3,
    )

    st.plotly_chart(
        incident_figure,
        use_container_width=True,
    )

with right_column:
    alert_figure = px.pie(
        alert_summary_dataframe,
        names="Alert Severity",
        values="Alerts",
        hole=0.60,
        title="Active Alerts by Severity",
        color="Alert Severity",
        color_discrete_map={
            "Critical": "#ef4444",
            "High": "#f97316",
            "Medium": "#facc15",
            "Low": "#22c55e",
        },
    )

    alert_figure.update_layout(
        height=400,
        margin=dict(
            l=10,
            r=10,
            t=60,
            b=10,
        ),
        legend_title=None,
    )

    alert_figure.update_traces(
        textinfo="percent+label",
    )

    st.plotly_chart(
        alert_figure,
        use_container_width=True,
    )


# =========================================================
# LOCATION OPERATIONS
# =========================================================

render_section_header(
    title="Location Operations",
    description=(
        "Compare alerts, technician coverage, "
        "machine activity, and response time by location."
    ),
)

left_column, right_column = st.columns(
    2,
    gap="large",
)

with left_column:
    location_alert_figure = px.bar(
        location_operations_dataframe.sort_values(
            "Open Alerts",
            ascending=True,
        ),
        x="Open Alerts",
        y="Location",
        orientation="h",
        text="Open Alerts",
        title="Open Alerts by Location",
    )

    location_alert_figure.update_layout(
        height=390,
        margin=dict(
            l=20,
            r=20,
            t=60,
            b=20,
        ),
        xaxis_title="Open Alerts",
        yaxis_title=None,
        showlegend=False,
    )

    location_alert_figure.update_traces(
        textposition="outside",
    )

    st.plotly_chart(
        location_alert_figure,
        use_container_width=True,
    )

with right_column:
    response_figure = px.bar(
        location_operations_dataframe.sort_values(
            "Average Response Minutes",
            ascending=True,
        ),
        x="Average Response Minutes",
        y="Location",
        orientation="h",
        text="Average Response Minutes",
        title="Average Response Time by Location",
    )

    response_figure.update_layout(
        height=390,
        margin=dict(
            l=20,
            r=20,
            t=60,
            b=20,
        ),
        xaxis_title="Response Time (Minutes)",
        yaxis_title=None,
        showlegend=False,
    )

    response_figure.update_traces(
        texttemplate="%{text} min",
        textposition="outside",
    )

    st.plotly_chart(
        response_figure,
        use_container_width=True,
    )


# =========================================================
# INCIDENT CATEGORY AND TECHNICIAN WORKLOAD
# =========================================================

render_section_header(
    title="Service Performance",
    description=(
        "Review recurring issue categories and "
        "technician workload distribution."
    ),
)

left_column, right_column = st.columns(
    2,
    gap="large",
)

with left_column:
    issue_figure = px.bar(
        issue_type_dataframe.sort_values(
            "Incidents",
            ascending=True,
        ),
        x="Incidents",
        y="Issue Type",
        orientation="h",
        text="Incidents",
        title="Incidents by Issue Type",
    )

    issue_figure.update_layout(
        height=400,
        margin=dict(
            l=20,
            r=20,
            t=60,
            b=20,
        ),
        xaxis_title="Incidents",
        yaxis_title=None,
        showlegend=False,
    )

    issue_figure.update_traces(
        textposition="outside",
    )

    st.plotly_chart(
        issue_figure,
        use_container_width=True,
    )

with right_column:
    workload_figure = px.scatter(
        technician_workload_dataframe,
        x="Open Tickets",
        y="Completed Today",
        size="Average Resolution Minutes",
        color="Technician",
        text="Technician",
        title="Technician Workload and Productivity",
    )

    workload_figure.update_layout(
        height=400,
        margin=dict(
            l=20,
            r=20,
            t=60,
            b=20,
        ),
        xaxis_title="Open Tickets",
        yaxis_title="Completed Today",
        legend_title=None,
        showlegend=False,
    )

    workload_figure.update_traces(
        textposition="top center",
    )

    st.plotly_chart(
        workload_figure,
        use_container_width=True,
    )


# =========================================================
# FILTER TICKET QUEUE
# =========================================================

filtered_ticket_queue = ticket_queue_dataframe.copy()

if selected_location != "All Locations":
    filtered_ticket_queue = filtered_ticket_queue[
        filtered_ticket_queue["Location"]
        == selected_location
    ]

if selected_severity != "All Severities":
    filtered_ticket_queue = filtered_ticket_queue[
        filtered_ticket_queue["Severity"]
        == selected_severity
    ]

if selected_status != "All Statuses":
    filtered_ticket_queue = filtered_ticket_queue[
        filtered_ticket_queue["Status"]
        == selected_status
    ]

if selected_sla != "All SLA Statuses":
    filtered_ticket_queue = filtered_ticket_queue[
        filtered_ticket_queue["SLA Status"]
        == selected_sla
    ]


# =========================================================
# PRIORITY TICKET QUEUE
# =========================================================

render_section_header(
    title="Priority Service Queue",
    description=(
        "Tickets prioritized by severity, age, "
        "SLA exposure, and operational impact."
    ),
)

severity_order = {
    "Critical": 1,
    "High": 2,
    "Medium": 3,
    "Low": 4,
}

filtered_ticket_queue = filtered_ticket_queue.assign(
    Severity_Order=filtered_ticket_queue[
        "Severity"
    ].map(severity_order)
)

filtered_ticket_queue = filtered_ticket_queue.sort_values(
    by=[
        "Severity_Order",
        "SLA Remaining Minutes",
        "Age Minutes",
    ],
    ascending=[
        True,
        True,
        False,
    ],
).drop(
    columns=[
        "Severity_Order",
    ]
)

download_dataframe = filtered_ticket_queue.copy()

download_data = download_dataframe.to_csv(
    index=False
).encode("utf-8")

queue_column, action_column = st.columns(
    [3, 1],
)

with queue_column:
    st.caption(
        f"{len(filtered_ticket_queue)} tickets match "
        "the selected operational filters."
    )

with action_column:
    st.download_button(
        label="Download Service Queue",
        data=download_data,
        file_name="operations_service_queue.csv",
        mime="text/csv",
        use_container_width=True,
    )

st.dataframe(
    filtered_ticket_queue,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Ticket ID": st.column_config.TextColumn(
            "Ticket ID"
        ),
        "Machine ID": st.column_config.TextColumn(
            "Machine ID"
        ),
        "Location": st.column_config.TextColumn(
            "Location"
        ),
        "Issue Type": st.column_config.TextColumn(
            "Issue Type"
        ),
        "Severity": st.column_config.TextColumn(
            "Severity"
        ),
        "Status": st.column_config.TextColumn(
            "Status"
        ),
        "Assigned Technician": st.column_config.TextColumn(
            "Assigned Technician"
        ),
        "Age Minutes": st.column_config.NumberColumn(
            "Ticket Age",
            format="%d min",
        ),
        "SLA Target Minutes": st.column_config.NumberColumn(
            "SLA Target",
            format="%d min",
        ),
        "SLA Remaining Minutes": st.column_config.NumberColumn(
            "SLA Remaining",
            format="%d min",
        ),
        "SLA Status": st.column_config.TextColumn(
            "SLA Status"
        ),
    },
)

if filtered_ticket_queue.empty:
    st.info(
        "No service tickets match the selected filters."
    )
else:
    filtered_breaches = int(
        (
            filtered_ticket_queue["SLA Status"]
            == "Breached"
        ).sum()
    )

    filtered_at_risk = int(
        (
            filtered_ticket_queue["SLA Status"]
            == "At Risk"
        ).sum()
    )

    if filtered_breaches > 0:
        st.error(
            f"{filtered_breaches} ticket(s) have breached "
            "their SLA and require immediate escalation."
        )
    elif filtered_at_risk > 0:
        st.warning(
            f"{filtered_at_risk} ticket(s) are approaching "
            "their SLA deadline."
        )
    else:
        st.success(
            "All displayed service tickets are currently "
            "within their SLA targets."
        )


# =========================================================
# TECHNICIAN WORKLOAD TABLE
# =========================================================

render_section_header(
    title="Technician Workload",
    description=(
        "Monitor ticket assignments, completed work, "
        "and average resolution performance."
    ),
)

st.dataframe(
    technician_workload_dataframe.sort_values(
        "Open Tickets",
        ascending=False,
    ),
    use_container_width=True,
    hide_index=True,
    column_config={
        "Technician": st.column_config.TextColumn(
            "Technician"
        ),
        "Open Tickets": st.column_config.NumberColumn(
            "Open Tickets",
            format="%d",
        ),
        "Completed Today": st.column_config.NumberColumn(
            "Completed Today",
            format="%d",
        ),
        "Average Resolution Minutes":
            st.column_config.NumberColumn(
                "Average Resolution",
                format="%d min",
            ),
    },
)


# =========================================================
# OPERATIONAL RECOMMENDATIONS
# =========================================================

st.success(
    "Operations monitoring is active. Prioritize critical "
    "tickets, SLA breaches, unassigned incidents, and "
    "locations with above-average response times."
)


# =========================================================
# FOOTER
# =========================================================

render_last_updated()
render_footer()
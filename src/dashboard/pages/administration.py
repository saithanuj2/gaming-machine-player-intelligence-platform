from __future__ import annotations

import streamlit as st


st.markdown(
    """
    <div class="enterprise-header">
        <div>
            <h1 class="enterprise-header-title">
                Administration
            </h1>
            <div class="enterprise-header-subtitle">
                Configure system access, data connections,
                API settings, user roles, and monitoring.
            </div>
        </div>
        <div class="enterprise-header-badge">
            Administrator Access
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.warning(
    "This page is visible only when the Administrator "
    "role is selected."
)

settings_column, monitoring_column = st.columns(
    2,
    gap="large",
)

with settings_column:
    with st.container(border=True):
        st.subheader("System Configuration")

        st.text_input(
            "Application Name",
            value="Gaming Machine Intelligence",
        )

        st.selectbox(
            "Default Dashboard Role",
            options=[
                "Executive",
                "Data Analyst",
                "Operations Manager",
                "Maintenance Manager",
            ],
        )

        st.toggle(
            "Enable API Caching",
            value=True,
        )

        st.toggle(
            "Enable Audit Logging",
            value=True,
        )

with monitoring_column:
    with st.container(border=True):
        st.subheader("Platform Monitoring")

        st.metric(
            "Application Status",
            "Operational",
            "All systems available",
        )

        st.metric(
            "API Response Time",
            "128 ms",
            "-12 ms",
        )

        st.metric(
            "Active Sessions",
            "4",
            "+1",
        )
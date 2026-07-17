import streamlit as st

from src.dashboard.styles import (
    render_page_header,
)


render_page_header(
    "System Health",
    (
        "API status, database connectivity, "
        "data freshness, and platform operations."
    ),
)

st.info(
    "System health components "
    "will be added next."
)
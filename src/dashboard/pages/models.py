import streamlit as st

from src.dashboard.styles import (
    render_page_header,
)


render_page_header(
    "Model Monitoring",
    (
        "Model performance, validation metrics, "
        "feature importance, and governance."
    ),
)

st.info(
    "Model monitoring components "
    "will be added next."
)
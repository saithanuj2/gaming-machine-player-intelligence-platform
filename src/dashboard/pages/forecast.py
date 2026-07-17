import streamlit as st

from src.dashboard.styles import (
    render_page_header,
)


render_page_header(
    "Revenue Forecasting",
    (
        "Daily and weekly revenue forecasts, "
        "accuracy, and location trends."
    ),
)

st.info(
    "Revenue forecasting components "
    "will be added next."
)
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st


# =========================================================
# PROJECT PATH CONFIGURATION
# =========================================================

CURRENT_FILE = Path(__file__).resolve()
DASHBOARD_DIR = CURRENT_FILE.parent
PROJECT_ROOT = CURRENT_FILE.parents[2]
PAGES_DIR = DASHBOARD_DIR / "pages"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# =========================================================
# PROJECT IMPORTS
# =========================================================

from src.dashboard.api_client import (
    api_health,
    clear_api_cache,
)
from src.dashboard.styles import apply_dashboard_styles


# =========================================================
# STREAMLIT PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Gaming Machine Intelligence Platform",
    page_icon="🎰",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# SESSION STATE DEFAULTS
# =========================================================

DEFAULT_SESSION_STATE = {
    "dashboard_theme": "Light",
    "user_role": "Executive",
    "api_url": os.getenv(
        "API_BASE_URL",
        "http://127.0.0.1:8000",
    ),
    "last_refresh": datetime.now(),
}

for key, default_value in DEFAULT_SESSION_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = default_value


# =========================================================
# APPLY DASHBOARD STYLES
# =========================================================

apply_dashboard_styles(
    theme=st.session_state.dashboard_theme,
)


# =========================================================
# ROLE CONFIGURATION
# =========================================================

AVAILABLE_ROLES = [
    "Executive",
    "Data Analyst",
    "Operations Manager",
    "Maintenance Manager",
    "Administrator",
]


# =========================================================
# SIDEBAR CONFIGURATION
# =========================================================

with st.sidebar:
    st.markdown(
        """
        <div style="
            padding: 14px 4px 18px 4px;
        ">
            <div style="
                font-size: 26px;
                font-weight: 750;
                line-height: 1.2;
            ">
                🎰 Gaming Intelligence
            </div>

            <div style="
                margin-top: 6px;
                color: #64748b;
                font-size: 13px;
            ">
                Enterprise Analytics Platform
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    selected_role = st.selectbox(
        label="User role",
        options=AVAILABLE_ROLES,
        index=AVAILABLE_ROLES.index(
            st.session_state.user_role
        ),
        key="sidebar_role_selector",
    )

    if selected_role != st.session_state.user_role:
        st.session_state.user_role = selected_role
        st.rerun()

    selected_theme = st.selectbox(
        label="Dashboard theme",
        options=[
            "Light",
            "Dark",
        ],
        index=[
            "Light",
            "Dark",
        ].index(
            st.session_state.dashboard_theme
        ),
        key="sidebar_theme_selector",
    )

    if selected_theme != st.session_state.dashboard_theme:
        st.session_state.dashboard_theme = selected_theme
        st.rerun()

    entered_api_url = st.text_input(
        label="FastAPI URL",
        value=st.session_state.api_url,
        key="sidebar_api_url",
    )

    entered_api_url = entered_api_url.strip()

    if entered_api_url:
        st.session_state.api_url = entered_api_url
    else:
        st.session_state.api_url = (
            "http://127.0.0.1:8000"
        )

    backend_connected = api_health(
        base_url=st.session_state.api_url,
    )

    if backend_connected:
        st.success(
            "API Connected",
            icon="✅",
        )
    else:
        st.warning(
            "Demo Data Mode",
            icon="⚠️",
        )

        st.caption(
            "Start FastAPI on port 8000 to enable "
            "live backend connectivity."
        )

    if st.button(
        label="Refresh dashboard",
        type="primary",
        use_container_width=True,
        key="refresh_dashboard_button",
    ):
        clear_api_cache()
        st.cache_data.clear()

        st.session_state.last_refresh = (
            datetime.now()
        )

        st.rerun()

    st.caption(
        "Last refresh: "
        f"{st.session_state.last_refresh:%Y-%m-%d %H:%M:%S}"
    )


# =========================================================
# VERIFY REQUIRED PAGE FILES
# =========================================================

REQUIRED_PAGE_FILES = {
    "executive": PAGES_DIR / "executive.py",
    "revenue": PAGES_DIR / "revenue.py",
    "players": PAGES_DIR / "players.py",
    "machines": PAGES_DIR / "machines.py",
    "operations": PAGES_DIR / "operations.py",
    "predictions": PAGES_DIR / "predictions.py",
    "administration": PAGES_DIR / "administration.py",
}

missing_page_files = [
    str(page_path)
    for page_path in REQUIRED_PAGE_FILES.values()
    if not page_path.exists()
]

if missing_page_files:
    st.error(
        "One or more dashboard page files are missing."
    )

    st.code(
        "\n".join(missing_page_files)
    )

    st.stop()


# =========================================================
# STREAMLIT PAGE DEFINITIONS
#
# IMPORTANT:
# These pages are loaded using file paths.
# They do not need a render() function.
# =========================================================

executive_page = st.Page(
    page=str(
        REQUIRED_PAGE_FILES["executive"]
    ),
    title="Executive Overview",
    icon=":material/dashboard:",
    default=True,
)

revenue_page = st.Page(
    page=str(
        REQUIRED_PAGE_FILES["revenue"]
    ),
    title="Revenue Analytics",
    icon=":material/monitoring:",
)

players_page = st.Page(
    page=str(
        REQUIRED_PAGE_FILES["players"]
    ),
    title="Player Intelligence",
    icon=":material/groups:",
)

machines_page = st.Page(
    page=str(
        REQUIRED_PAGE_FILES["machines"]
    ),
    title="Machine Analytics",
    icon=":material/precision_manufacturing:",
)

operations_page = st.Page(
    page=str(
        REQUIRED_PAGE_FILES["operations"]
    ),
    title="Operations Center",
    icon=":material/warning:",
)

predictions_page = st.Page(
    page=str(
        REQUIRED_PAGE_FILES["predictions"]
    ),
    title="AI Predictions",
    icon=":material/psychology:",
)

administration_page = st.Page(
    page=str(
        REQUIRED_PAGE_FILES["administration"]
    ),
    title="Administration",
    icon=":material/admin_panel_settings:",
)


# =========================================================
# ROLE-BASED NAVIGATION
# =========================================================

ROLE_NAVIGATION = {
    "Executive": {
        "Enterprise Intelligence": [
            executive_page,
            revenue_page,
            players_page,
            machines_page,
            operations_page,
            predictions_page,
        ],
    },

    "Data Analyst": {
        "Analytics": [
            executive_page,
            revenue_page,
            players_page,
            machines_page,
            predictions_page,
        ],
    },

    "Operations Manager": {
        "Operations": [
            executive_page,
            machines_page,
            operations_page,
            predictions_page,
        ],
    },

    "Maintenance Manager": {
        "Maintenance": [
            executive_page,
            machines_page,
            operations_page,
        ],
    },

    "Administrator": {
        "Enterprise Intelligence": [
            executive_page,
            revenue_page,
            players_page,
            machines_page,
            operations_page,
            predictions_page,
        ],

        "System Management": [
            administration_page,
        ],
    },
}


# =========================================================
# START APPLICATION NAVIGATION
# =========================================================

selected_navigation = ROLE_NAVIGATION.get(
    st.session_state.user_role,
    ROLE_NAVIGATION["Executive"],
)

navigation = st.navigation(
    pages=selected_navigation,
    position="sidebar",
    expanded=True,
)

navigation.run()
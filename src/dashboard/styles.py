from __future__ import annotations

import streamlit as st


def apply_dashboard_styles(theme: str = "Light") -> None:
    """Apply global enterprise dashboard styling."""

    is_dark = theme.lower() == "dark"

    if is_dark:
        colors = {
            "app_background": "#0B1120",
            "surface": "#111827",
            "surface_secondary": "#182235",
            "surface_hover": "#1F2A3D",
            "text_primary": "#F8FAFC",
            "text_secondary": "#CBD5E1",
            "text_muted": "#94A3B8",
            "border": "#293548",
            "border_soft": "#202C3D",
            "primary": "#60A5FA",
            "primary_dark": "#3B82F6",
            "primary_soft": "#172554",
            "success": "#34D399",
            "success_soft": "#064E3B",
            "warning": "#FBBF24",
            "warning_soft": "#451A03",
            "danger": "#FB7185",
            "danger_soft": "#4C0519",
            "header_background": "#111C33",
            "shadow": "rgba(0, 0, 0, 0.30)",
        }
    else:
        colors = {
            "app_background": "#F4F7FB",
            "surface": "#FFFFFF",
            "surface_secondary": "#F8FAFC",
            "surface_hover": "#F1F5F9",
            "text_primary": "#0F172A",
            "text_secondary": "#334155",
            "text_muted": "#64748B",
            "border": "#DCE3EC",
            "border_soft": "#E8EDF3",
            "primary": "#2563EB",
            "primary_dark": "#1D4ED8",
            "primary_soft": "#EFF6FF",
            "success": "#059669",
            "success_soft": "#ECFDF5",
            "warning": "#D97706",
            "warning_soft": "#FFFBEB",
            "danger": "#DC2626",
            "danger_soft": "#FEF2F2",
            "header_background": "#13294B",
            "shadow": "rgba(15, 23, 42, 0.08)",
        }

    css = f"""
    <style>
    /* =====================================================
       APPLICATION VARIABLES
       ===================================================== */

    :root {{
        --app-background: {colors["app_background"]};
        --surface: {colors["surface"]};
        --surface-secondary: {colors["surface_secondary"]};
        --surface-hover: {colors["surface_hover"]};
        --text-primary: {colors["text_primary"]};
        --text-secondary: {colors["text_secondary"]};
        --text-muted: {colors["text_muted"]};
        --border: {colors["border"]};
        --border-soft: {colors["border_soft"]};
        --primary: {colors["primary"]};
        --primary-dark: {colors["primary_dark"]};
        --primary-soft: {colors["primary_soft"]};
        --success: {colors["success"]};
        --success-soft: {colors["success_soft"]};
        --warning: {colors["warning"]};
        --warning-soft: {colors["warning_soft"]};
        --danger: {colors["danger"]};
        --danger-soft: {colors["danger_soft"]};
        --header-background: {colors["header_background"]};
        --dashboard-shadow: {colors["shadow"]};
    }}

    /* =====================================================
       GLOBAL APPLICATION
       ===================================================== */

    html,
    body,
    [class*="css"] {{
        font-family:
            Inter,
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            Roboto,
            Helvetica,
            Arial,
            sans-serif;
    }}

    html {{
        font-size: 15px;
    }}

    body {{
        color: var(--text-primary);
    }}

    [data-testid="stAppViewContainer"] {{
        background: var(--app-background);
        color: var(--text-primary);
    }}

    [data-testid="stMain"] {{
        width: 100%;
        background: var(--app-background);
    }}

    [data-testid="stMainBlockContainer"],
    .main .block-container {{
        width: 100%;
        max-width: 1540px;
        margin: 0 auto;
        padding-top: 1.5rem;
        padding-right: 2.25rem;
        padding-bottom: 2.5rem;
        padding-left: 2.25rem;
    }}

    h1,
    h2,
    h3,
    h4,
    h5,
    h6,
    p,
    label,
    span {{
        color: var(--text-primary);
    }}

    [data-testid="stCaptionContainer"],
    .stCaption {{
        color: var(--text-muted);
    }}

    hr {{
        border-color: var(--border-soft);
    }}

    /* =====================================================
       SIDEBAR
       ===================================================== */

    [data-testid="stSidebar"] {{
        background: var(--surface);
        border-right: 1px solid var(--border);
    }}

    [data-testid="stSidebarContent"] {{
        padding-top: 0.75rem;
    }}

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{
        color: var(--text-secondary);
    }}

    .sidebar-brand {{
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin: 0 0 1.35rem 0;
        padding: 0.85rem;
        border: 1px solid var(--border);
        border-radius: 14px;
        background: var(--surface-secondary);
    }}

    .sidebar-brand-icon {{
        display: flex;
        width: 42px;
        height: 42px;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        border-radius: 11px;
        background: var(--primary);
        color: #FFFFFF;
        font-size: 0.85rem;
        font-weight: 800;
        letter-spacing: 0.03em;
    }}

    .sidebar-brand-title {{
        color: var(--text-primary);
        font-size: 0.92rem;
        font-weight: 700;
        line-height: 1.25;
    }}

    .sidebar-brand-subtitle {{
        margin-top: 0.2rem;
        color: var(--text-muted);
        font-size: 0.68rem;
        line-height: 1.25;
    }}

    .sidebar-section-label {{
        margin-top: 1.25rem;
        margin-bottom: 0.45rem;
        color: var(--text-muted);
        font-size: 0.65rem;
        font-weight: 700;
        letter-spacing: 0.09em;
    }}

    [data-testid="stSidebarNav"] {{
        margin-top: 0.5rem;
    }}

    [data-testid="stSidebarNav"] a {{
        margin-bottom: 0.22rem;
        border-radius: 9px;
        color: var(--text-secondary);
    }}

    [data-testid="stSidebarNav"] a:hover {{
        background: var(--surface-hover);
        color: var(--text-primary);
    }}

    [data-testid="stSidebarNav"] a[aria-current="page"] {{
        background: var(--primary-soft);
        color: var(--primary);
        font-weight: 650;
    }}

    .connection-status {{
        display: flex;
        align-items: center;
        gap: 0.65rem;
        margin-top: 0.45rem;
        padding: 0.75rem 0.8rem;
        border: 1px solid var(--border);
        border-radius: 10px;
    }}

    .connection-status strong {{
        display: block;
        color: var(--text-primary);
        font-size: 0.78rem;
        font-weight: 700;
    }}

    .connection-status span:not(.connection-dot) {{
        display: block;
        margin-top: 0.1rem;
        color: var(--text-muted);
        font-size: 0.67rem;
    }}

    .connection-dot {{
        display: block;
        width: 9px;
        height: 9px;
        flex-shrink: 0;
        border-radius: 50%;
    }}

    .connection-online {{
        background: var(--success-soft);
    }}

    .connection-online .connection-dot {{
        background: var(--success);
        box-shadow: 0 0 0 4px rgba(5, 150, 105, 0.12);
    }}

    .connection-offline {{
        background: var(--warning-soft);
    }}

    .connection-offline .connection-dot {{
        background: var(--warning);
        box-shadow: 0 0 0 4px rgba(217, 119, 6, 0.12);
    }}

    .sidebar-footer {{
        margin-top: 2rem;
        padding-top: 1rem;
        padding-bottom: 0.5rem;
        border-top: 1px solid var(--border-soft);
        text-align: center;
    }}

    .sidebar-footer-title {{
        color: var(--text-primary);
        font-size: 0.71rem;
        font-weight: 650;
    }}

    .sidebar-footer-text {{
        margin-top: 0.18rem;
        color: var(--text-muted);
        font-size: 0.62rem;
    }}

    .sidebar-footer-version {{
        margin-top: 0.3rem;
        color: var(--text-muted);
        font-size: 0.58rem;
    }}

    /* =====================================================
       PAGE HEADER
       ===================================================== */

    .enterprise-header {{
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 1rem;
        margin-bottom: 1rem;
        padding: 1.25rem 1.4rem;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        background: var(--header-background);
        box-shadow: 0 8px 24px var(--dashboard-shadow);
    }}

    .enterprise-header-title {{
        margin: 0;
        color: #FFFFFF !important;
        font-size: 1.48rem;
        font-weight: 750;
        letter-spacing: -0.025em;
    }}

    .enterprise-header-subtitle {{
        max-width: 800px;
        margin-top: 0.35rem;
        color: #CBD5E1 !important;
        font-size: 0.78rem;
        line-height: 1.5;
    }}

    .enterprise-header-badge {{
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        flex-shrink: 0;
        padding: 0.38rem 0.65rem;
        border: 1px solid rgba(52, 211, 153, 0.30);
        border-radius: 999px;
        background: rgba(16, 185, 129, 0.14);
        color: #A7F3D0 !important;
        font-size: 0.66rem;
        font-weight: 700;
    }}

    /* =====================================================
       METRICS
       ===================================================== */

    [data-testid="stMetric"] {{
        min-height: 115px;
        padding: 1rem 1rem 0.85rem 1rem;
        border: 1px solid var(--border);
        border-radius: 12px;
        background: var(--surface);
        box-shadow: 0 3px 12px var(--dashboard-shadow);
    }}

    [data-testid="stMetric"]:hover {{
        border-color: var(--primary);
        box-shadow: 0 8px 22px var(--dashboard-shadow);
        transition: all 0.18s ease;
    }}

    [data-testid="stMetricLabel"] {{
        color: var(--text-muted);
        font-size: 0.72rem;
        font-weight: 650;
    }}

    [data-testid="stMetricLabel"] p {{
        color: var(--text-muted) !important;
    }}

    [data-testid="stMetricValue"] {{
        color: var(--text-primary);
        font-size: 1.36rem;
        font-weight: 750;
        letter-spacing: -0.025em;
    }}

    [data-testid="stMetricValue"] div {{
        color: var(--text-primary) !important;
    }}

    [data-testid="stMetricDelta"] {{
        font-size: 0.68rem;
        font-weight: 650;
    }}

    /* =====================================================
       CONTAINERS AND PANELS
       ===================================================== */

    [data-testid="stVerticalBlockBorderWrapper"] {{
        border-color: var(--border) !important;
        border-radius: 12px;
        background: var(--surface);
        box-shadow: 0 3px 12px var(--dashboard-shadow);
    }}

    .section-header {{
        margin-top: 1.5rem;
        margin-bottom: 0.7rem;
    }}

    .section-header-title {{
        color: var(--text-primary);
        font-size: 1rem;
        font-weight: 750;
        letter-spacing: -0.012em;
    }}

    .section-header-description {{
        margin-top: 0.18rem;
        color: var(--text-muted);
        font-size: 0.72rem;
        line-height: 1.45;
    }}

    /* =====================================================
       INPUTS
       ===================================================== */

    [data-baseweb="select"] > div,
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stDateInput"] input {{
        border-color: var(--border) !important;
        background: var(--surface-secondary) !important;
        color: var(--text-primary) !important;
    }}

    [data-baseweb="select"] span {{
        color: var(--text-primary);
    }}

    [data-testid="stTextInput"] label,
    [data-testid="stSelectbox"] label,
    [data-testid="stNumberInput"] label,
    [data-testid="stDateInput"] label {{
        color: var(--text-secondary) !important;
        font-size: 0.71rem;
        font-weight: 650;
    }}

    /* =====================================================
       BUTTONS
       ===================================================== */

    [data-testid="stButton"] button,
    [data-testid="stDownloadButton"] button {{
        min-height: 38px;
        border: 1px solid var(--border);
        border-radius: 9px;
        background: var(--surface);
        color: var(--text-primary);
        font-size: 0.72rem;
        font-weight: 650;
    }}

    [data-testid="stButton"] button:hover,
    [data-testid="stDownloadButton"] button:hover {{
        border-color: var(--primary);
        color: var(--primary);
    }}

    [data-testid="stButton"] button[kind="primary"] {{
        border-color: var(--primary);
        background: var(--primary);
        color: #FFFFFF;
    }}

    [data-testid="stButton"] button[kind="primary"]:hover {{
        border-color: var(--primary-dark);
        background: var(--primary-dark);
        color: #FFFFFF;
    }}

    /* =====================================================
       DATAFRAMES
       ===================================================== */

    [data-testid="stDataFrame"] {{
        border: 1px solid var(--border);
        border-radius: 10px;
        background: var(--surface);
        overflow: hidden;
    }}

    /* =====================================================
       ALERTS
       ===================================================== */

    [data-testid="stAlert"] {{
        border-radius: 10px;
        font-size: 0.73rem;
    }}

    /* =====================================================
       TABS
       ===================================================== */

    [data-baseweb="tab-list"] {{
        gap: 0.35rem;
        border-bottom: 1px solid var(--border);
    }}

    [data-baseweb="tab"] {{
        border-radius: 8px 8px 0 0;
        color: var(--text-muted);
        font-size: 0.73rem;
        font-weight: 650;
    }}

    [aria-selected="true"][data-baseweb="tab"] {{
        background: var(--primary-soft);
        color: var(--primary);
    }}

    /* =====================================================
       PLOTLY
       ===================================================== */

    .js-plotly-plot,
    .plot-container {{
        border-radius: 10px;
    }}

    /* =====================================================
       FOOTER
       ===================================================== */

    .dashboard-footer {{
        margin-top: 1.8rem;
        padding-top: 0.9rem;
        border-top: 1px solid var(--border-soft);
        color: var(--text-muted);
        text-align: center;
        font-size: 0.63rem;
        line-height: 1.6;
    }}

    /* =====================================================
       RESPONSIVE DESIGN
       ===================================================== */

    @media (max-width: 1100px) {{
        [data-testid="stMainBlockContainer"],
        .main .block-container {{
            padding-right: 1.25rem;
            padding-left: 1.25rem;
        }}

        .enterprise-header {{
            padding: 1rem;
        }}
    }}

    @media (max-width: 700px) {{
        [data-testid="stMainBlockContainer"],
        .main .block-container {{
            padding-top: 1rem;
            padding-right: 0.75rem;
            padding-left: 0.75rem;
        }}

        .enterprise-header {{
            flex-direction: column;
        }}

        .enterprise-header-title {{
            font-size: 1.22rem;
        }}
    }}
    </style>
    """

    st.markdown(
        css,
        unsafe_allow_html=True,
    )
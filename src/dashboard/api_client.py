from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st
from dotenv import load_dotenv


# =========================================================
# ENVIRONMENT CONFIGURATION
# =========================================================

load_dotenv()

API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "http://127.0.0.1:8000",
).rstrip("/")


# =========================================================
# CUSTOM EXCEPTION
# =========================================================

class APIClientError(RuntimeError):
    """Raised when the FastAPI backend cannot fulfill a request."""


# =========================================================
# GENERIC API REQUEST
# =========================================================

@st.cache_data(
    ttl=60,
    show_spinner=False,
)
def get_api_data(
    endpoint: str,
    params: dict[str, Any] | None = None,
    base_url: str | None = None,
) -> dict[str, Any]:
    """
    Fetch JSON data from the FastAPI backend.

    Parameters
    ----------
    endpoint:
        API endpoint such as /health or /api/v1/dashboard/kpis.
    params:
        Optional query parameters.
    base_url:
        Optional API base URL override.
    """

    api_url = (
        base_url.rstrip("/")
        if base_url
        else API_BASE_URL
    )

    url = f"{api_url}/{endpoint.lstrip('/')}"

    try:
        response = requests.get(
            url,
            params=params,
            timeout=30,
        )

        response.raise_for_status()

        payload = response.json()

        if not isinstance(payload, dict):
            return {
                "data": payload,
            }

        return payload

    except requests.exceptions.ConnectionError as error:
        raise APIClientError(
            "The FastAPI backend is not reachable. "
            "Start the API on port 8000."
        ) from error

    except requests.exceptions.Timeout as error:
        raise APIClientError(
            "The API request timed out."
        ) from error

    except requests.exceptions.HTTPError as error:
        detail: Any = None

        try:
            payload = response.json()

            if isinstance(payload, dict):
                detail = payload.get(
                    "detail",
                    payload,
                )
            else:
                detail = payload

        except ValueError:
            detail = response.text

        raise APIClientError(
            f"API request failed with status "
            f"{response.status_code}: {detail}"
        ) from error

    except requests.exceptions.RequestException as error:
        raise APIClientError(
            f"API request failed: {error}"
        ) from error


# =========================================================
# CACHE MANAGEMENT
# =========================================================

def clear_api_cache() -> None:
    """Clear all cached API responses."""

    get_api_data.clear()


# =========================================================
# API HEALTH CHECK
# =========================================================

def api_health(
    base_url: str | None = None,
) -> bool:
    """
    Return True when the FastAPI backend is reachable.

    Supports both:
    - /health
    - /api/v1/health
    """

    api_url = (
        base_url.rstrip("/")
        if base_url
        else API_BASE_URL
    )

    health_endpoints = [
        "/health",
        "/api/v1/health",
    ]

    for endpoint in health_endpoints:
        try:
            response = requests.get(
                f"{api_url}{endpoint}",
                timeout=3,
            )

            if response.status_code == 200:
                return True

        except requests.exceptions.RequestException:
            continue

    return False


def get_api_health(
    base_url: str | None = None,
) -> dict[str, Any]:
    """
    Return backend health information.

    Attempts the current /health endpoint first,
    followed by /api/v1/health.
    """

    api_url = (
        base_url.rstrip("/")
        if base_url
        else API_BASE_URL
    )

    health_endpoints = [
        "/health",
        "/api/v1/health",
    ]

    last_error: Exception | None = None

    for endpoint in health_endpoints:
        try:
            return get_api_data(
                endpoint=endpoint,
                base_url=api_url,
            )

        except APIClientError as error:
            last_error = error

    raise APIClientError(
        "The backend health endpoint is unavailable."
    ) from last_error


# =========================================================
# EXECUTIVE DASHBOARD ENDPOINTS
# =========================================================

def get_executive_kpis() -> dict[str, Any]:
    """Return executive KPI information."""

    return get_api_data(
        "/api/v1/dashboard/kpis"
    )


def get_revenue_trend(
    days: int = 30,
) -> dict[str, Any]:
    """Return recent revenue-trend data."""

    return get_api_data(
        "/api/v1/dashboard/revenue-trend",
        params={
            "days": days,
        },
    )


# =========================================================
# PLAYER INTELLIGENCE ENDPOINTS
# =========================================================

def get_player_summary() -> dict[str, Any]:
    """Return player-intelligence summary data."""

    return get_api_data(
        "/api/v1/players/summary"
    )


def get_churn_players(
    page: int = 1,
    page_size: int = 100,
    risk_level: str | None = None,
    minimum_probability: float = 0.0,
    search: str | None = None,
) -> dict[str, Any]:
    """Return churn-risk player records."""

    parameters: dict[str, Any] = {
        "page": page,
        "page_size": page_size,
        "minimum_probability": minimum_probability,
    }

    if risk_level:
        parameters["risk_level"] = risk_level

    if search:
        parameters["search"] = search

    return get_api_data(
        "/api/v1/players/churn-risk",
        params=parameters,
    )


def get_player_segments(
    page: int = 1,
    page_size: int = 100,
    segment: str | None = None,
    search: str | None = None,
) -> dict[str, Any]:
    """Return player-segmentation records."""

    parameters: dict[str, Any] = {
        "page": page,
        "page_size": page_size,
    }

    if segment:
        parameters["segment"] = segment

    if search:
        parameters["search"] = search

    return get_api_data(
        "/api/v1/players/segments",
        params=parameters,
    )


# =========================================================
# MACHINE INTELLIGENCE ENDPOINTS
# =========================================================

def get_machine_summary() -> dict[str, Any]:
    """Return machine-intelligence summary data."""

    return get_api_data(
        "/api/v1/machines/summary"
    )


def get_failure_risk(
    page: int = 1,
    page_size: int = 100,
    risk_level: str | None = None,
    minimum_probability: float = 0.0,
) -> dict[str, Any]:
    """Return machine-failure prediction records."""

    parameters: dict[str, Any] = {
        "page": page,
        "page_size": page_size,
        "minimum_probability": minimum_probability,
    }

    if risk_level:
        parameters["risk_level"] = risk_level

    return get_api_data(
        "/api/v1/machines/failure-risk",
        params=parameters,
    )


def get_machine_anomalies(
    page: int = 1,
    page_size: int = 100,
    risk_level: str | None = None,
) -> dict[str, Any]:
    """Return machine-anomaly alert records."""

    parameters: dict[str, Any] = {
        "page": page,
        "page_size": page_size,
        "anomaly_only": True,
    }

    if risk_level:
        parameters["risk_level"] = risk_level

    return get_api_data(
        "/api/v1/machines/anomalies",
        params=parameters,
    )


# =========================================================
# FORECAST ENDPOINTS
# =========================================================

def get_forecast_summary() -> dict[str, Any]:
    """Return daily and weekly forecast summaries."""

    return get_api_data(
        "/api/v1/forecast/summary"
    )


def get_daily_forecast(
    page: int = 1,
    page_size: int = 500,
    location_id: str | None = None,
) -> dict[str, Any]:
    """Return daily forecast records."""

    parameters: dict[str, Any] = {
        "page": page,
        "page_size": page_size,
    }

    if location_id:
        parameters["location_id"] = location_id

    return get_api_data(
        "/api/v1/forecast/daily",
        params=parameters,
    )


def get_weekly_forecast(
    page: int = 1,
    page_size: int = 500,
    location_id: str | None = None,
) -> dict[str, Any]:
    """Return weekly forecast records."""

    parameters: dict[str, Any] = {
        "page": page,
        "page_size": page_size,
    }

    if location_id:
        parameters["location_id"] = location_id

    return get_api_data(
        "/api/v1/forecast/weekly",
        params=parameters,
    )


def get_model_comparison() -> dict[str, Any]:
    """Return forecast model-comparison results."""

    return get_api_data(
        "/api/v1/forecast/model-comparison"
    )
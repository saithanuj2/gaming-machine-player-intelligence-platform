from typing import Any

import pandas as pd


def format_currency(
    value: Any,
    decimals: int = 0,
) -> str:
    """Format a numeric value as US currency."""

    try:
        numeric_value = float(value or 0)
    except (TypeError, ValueError):
        numeric_value = 0.0

    return f"${numeric_value:,.{decimals}f}"


def format_number(
    value: Any,
    decimals: int = 0,
) -> str:
    """Format a numeric value with commas."""

    try:
        numeric_value = float(value or 0)
    except (TypeError, ValueError):
        numeric_value = 0.0

    return f"{numeric_value:,.{decimals}f}"


def format_percentage(
    value: Any,
    decimals: int = 1,
    already_percentage: bool = False,
) -> str:
    """Format a decimal or percentage value."""

    try:
        numeric_value = float(value or 0)
    except (TypeError, ValueError):
        numeric_value = 0.0

    if not already_percentage:
        numeric_value *= 100

    return f"{numeric_value:,.{decimals}f}%"


def records_to_dataframe(
    records: list[dict[str, Any]] | None,
) -> pd.DataFrame:
    """Convert API records into a DataFrame."""

    if not records:
        return pd.DataFrame()

    return pd.DataFrame(records)


def dataframe_to_csv_bytes(
    dataframe: pd.DataFrame,
) -> bytes:
    """Convert a DataFrame into downloadable CSV bytes."""

    return dataframe.to_csv(
        index=False,
    ).encode("utf-8")


def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    """Convert a value safely to float."""

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(
    value: Any,
    default: int = 0,
) -> int:
    """Convert a value safely to integer."""

    try:
        return int(value)
    except (TypeError, ValueError):
        return default
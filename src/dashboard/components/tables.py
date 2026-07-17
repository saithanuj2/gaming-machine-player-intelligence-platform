from typing import Any

import pandas as pd
import streamlit as st

from src.dashboard.utils import (
    dataframe_to_csv_bytes,
)


def render_data_table(
    dataframe: pd.DataFrame,
    column_config: dict[str, Any] | None = None,
    height: int = 420,
    hide_index: bool = True,
    selection_mode: str | None = None,
    key: str | None = None,
) -> Any:
    """Render a professional interactive table."""

    if dataframe.empty:
        st.info(
            "No records are available for "
            "the selected filters."
        )
        return None

    table_arguments: dict[str, Any] = {
        "data": dataframe,
        "use_container_width": True,
        "hide_index": hide_index,
        "height": height,
        "column_config": column_config,
        "key": key,
    }

    if selection_mode:
        table_arguments[
            "on_select"
        ] = "rerun"

        table_arguments[
            "selection_mode"
        ] = selection_mode

    return st.dataframe(
        **table_arguments
    )


def render_download_button(
    dataframe: pd.DataFrame,
    label: str,
    file_name: str,
    key: str,
) -> None:
    """Render a CSV export button."""

    if dataframe.empty:
        return

    st.download_button(
        label=label,
        data=dataframe_to_csv_bytes(
            dataframe
        ),
        file_name=file_name,
        mime="text/csv",
        key=key,
        use_container_width=True,
    )


def apply_risk_sorting(
    dataframe: pd.DataFrame,
    risk_column: str,
) -> pd.DataFrame:
    """Sort records by business-risk severity."""

    if (
        dataframe.empty
        or risk_column
        not in dataframe.columns
    ):
        return dataframe

    risk_order = {
        "Critical": 4,
        "High": 3,
        "Medium": 2,
        "Low": 1,
    }

    output = dataframe.copy()

    output[
        "_risk_sort"
    ] = output[
        risk_column
    ].map(
        risk_order
    ).fillna(0)

    output = output.sort_values(
        "_risk_sort",
        ascending=False,
    ).drop(
        columns=[
            "_risk_sort"
        ]
    )

    return output.reset_index(
        drop=True
    )


def format_risk_column(
    risk_column: str,
) -> dict[str, Any]:
    """Return Streamlit config for a risk field."""

    return {
        risk_column: st.column_config.TextColumn(
            risk_column.replace(
                "_",
                " ",
            ).title(),
            help="Business risk classification",
        )
    }


def render_table_toolbar(
    dataframe: pd.DataFrame,
    download_name: str,
    download_key: str,
) -> None:
    """Render record count and CSV export controls."""

    left_column, right_column = st.columns(
        [
            3,
            1,
        ]
    )

    with left_column:
        st.caption(
            f"{len(dataframe):,} records displayed"
        )

    with right_column:
        render_download_button(
            dataframe=dataframe,
            label="Download CSV",
            file_name=download_name,
            key=download_key,
        )
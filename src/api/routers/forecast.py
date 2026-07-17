import math
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DAILY_PREDICTIONS_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "ml"
    / "revenue_forecast_predictions.csv"
)

WEEKLY_PREDICTIONS_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "ml"
    / "weekly_revenue_forecast_predictions.csv"
)

DAILY_METRICS_PATH = (
    PROJECT_ROOT
    / "reports"
    / "model_metrics"
    / "revenue_forecast_model_metrics.csv"
)

WEEKLY_METRICS_PATH = (
    PROJECT_ROOT
    / "reports"
    / "model_metrics"
    / "weekly_revenue_forecast_model_metrics.csv"
)

WEEKLY_LOCATION_SUMMARY_PATH = (
    PROJECT_ROOT
    / "reports"
    / "model_metrics"
    / "weekly_revenue_forecast_location_summary.csv"
)

WEEKLY_SELECTION_PATH = (
    PROJECT_ROOT
    / "reports"
    / "model_metrics"
    / "weekly_revenue_forecast_selection.txt"
)


router = APIRouter(
    prefix="/api/v1/forecast",
    tags=["Revenue Forecasting"],
)


def load_csv(
    file_path: Path,
    dataset_name: str,
) -> pd.DataFrame:
    """Load a required forecasting CSV file."""

    if not file_path.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                f"{dataset_name} was not found: "
                f"{file_path.name}. Run the related "
                "forecasting pipeline first."
            ),
        )

    try:
        dataframe = pd.read_csv(file_path)

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Unable to read {file_path.name}: "
                f"{error}"
            ),
        ) from error

    if dataframe.empty:
        raise HTTPException(
            status_code=503,
            detail=(
                f"{dataset_name} contains no records."
            ),
        )

    return dataframe


def validate_columns(
    dataframe: pd.DataFrame,
    required_columns: set[str],
    dataset_name: str,
) -> None:
    """Confirm that a dataset contains required columns."""

    missing_columns = (
        required_columns
        - set(dataframe.columns)
    )

    if missing_columns:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Missing columns in {dataset_name}: "
                + ", ".join(
                    sorted(missing_columns)
                )
            ),
        )


def serialize_value(value: Any) -> Any:
    """Convert Pandas and NumPy values into JSON-safe values."""

    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if isinstance(value, pd.Timestamp):
        return value.isoformat()

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, np.integer):
        return int(value)

    if isinstance(value, np.floating):
        numeric_value = float(value)

        if math.isnan(numeric_value):
            return None

        if math.isinf(numeric_value):
            return None

        return numeric_value

    if isinstance(value, np.bool_):
        return bool(value)

    return value


def dataframe_to_records(
    dataframe: pd.DataFrame,
) -> list[dict[str, Any]]:
    """Convert a DataFrame into JSON-safe records."""

    records = dataframe.to_dict(
        orient="records"
    )

    return [
        {
            key: serialize_value(value)
            for key, value in record.items()
        }
        for record in records
    ]


def paginate_dataframe(
    dataframe: pd.DataFrame,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    """Return a paginated response."""

    total_records = len(dataframe)

    total_pages = (
        math.ceil(
            total_records / page_size
        )
        if total_records
        else 0
    )

    start_index = (
        page - 1
    ) * page_size

    end_index = (
        start_index
        + page_size
    )

    page_data = dataframe.iloc[
        start_index:end_index
    ]

    return {
        "page": page,
        "page_size": page_size,
        "total_records": total_records,
        "total_pages": total_pages,
        "data": dataframe_to_records(
            page_data
        ),
    }


def parse_optional_date(
    value: str | None,
    parameter_name: str,
) -> pd.Timestamp | None:
    """Parse an optional API date parameter."""

    if value is None:
        return None

    parsed_value = pd.to_datetime(
        value,
        errors="coerce",
    )

    if pd.isna(parsed_value):
        raise HTTPException(
            status_code=422,
            detail=(
                f"{parameter_name} must be a "
                "valid date in YYYY-MM-DD format."
            ),
        )

    return pd.Timestamp(parsed_value)


def calculate_forecast_summary(
    dataframe: pd.DataFrame,
    actual_column: str,
    predicted_column: str,
) -> dict[str, Any]:
    """Calculate forecast metrics from saved predictions."""

    validate_columns(
        dataframe,
        {
            actual_column,
            predicted_column,
        },
        "forecast prediction output",
    )

    actual = pd.to_numeric(
        dataframe[actual_column],
        errors="coerce",
    )

    predicted = pd.to_numeric(
        dataframe[predicted_column],
        errors="coerce",
    )

    valid_mask = (
        actual.notna()
        & predicted.notna()
    )

    actual = actual.loc[
        valid_mask
    ]

    predicted = predicted.loc[
        valid_mask
    ]

    if actual.empty:
        return {
            "record_count": 0,
            "actual_revenue": 0.0,
            "predicted_revenue": 0.0,
            "average_absolute_error": 0.0,
            "root_mean_squared_error": 0.0,
            "weighted_absolute_percentage_error": 0.0,
        }

    errors = (
        actual
        - predicted
    )

    absolute_errors = (
        errors.abs()
    )

    squared_errors = (
        errors ** 2
    )

    denominator = float(
        actual.abs().sum()
    )

    wape = (
        float(
            absolute_errors.sum()
            / denominator
            * 100
        )
        if denominator != 0
        else 0.0
    )

    rmse = float(
        np.sqrt(
            squared_errors.mean()
        )
    )

    return {
        "record_count": int(
            len(actual)
        ),
        "actual_revenue": round(
            float(actual.sum()),
            2,
        ),
        "predicted_revenue": round(
            float(predicted.sum()),
            2,
        ),
        "average_absolute_error": round(
            float(
                absolute_errors.mean()
            ),
            2,
        ),
        "root_mean_squared_error": round(
            rmse,
            2,
        ),
        "weighted_absolute_percentage_error": round(
            wape,
            2,
        ),
    }


def get_best_metric_row(
    dataframe: pd.DataFrame,
) -> dict[str, Any]:
    """Return the row with the lowest RMSE."""

    validate_columns(
        dataframe,
        {
            "model",
            "mae",
            "rmse",
            "r2_score",
        },
        "forecast model metrics",
    )

    output = dataframe.copy()

    output["rmse"] = pd.to_numeric(
        output["rmse"],
        errors="coerce",
    )

    output = output.dropna(
        subset=["rmse"]
    )

    if output.empty:
        raise HTTPException(
            status_code=500,
            detail=(
                "Forecast model metrics contain "
                "no valid RMSE values."
            ),
        )

    best_row = output.sort_values(
        "rmse"
    ).iloc[0]

    return {
        key: serialize_value(value)
        for key, value in best_row.to_dict().items()
    }


@router.get("/summary")
def get_forecast_summary() -> dict[str, Any]:
    """Return daily and weekly forecasting KPIs."""

    daily_data = load_csv(
        DAILY_PREDICTIONS_PATH,
        "Daily forecast predictions",
    )

    weekly_data = load_csv(
        WEEKLY_PREDICTIONS_PATH,
        "Weekly forecast predictions",
    )

    daily_metrics = load_csv(
        DAILY_METRICS_PATH,
        "Daily forecast model metrics",
    )

    weekly_metrics = load_csv(
        WEEKLY_METRICS_PATH,
        "Weekly forecast model metrics",
    )

    validate_columns(
        daily_data,
        {
            "net_gaming_revenue",
            "predicted_revenue",
        },
        "daily forecast predictions",
    )

    validate_columns(
        weekly_data,
        {
            "net_gaming_revenue",
            "selected_predicted_revenue",
            "selected_forecasting_method",
        },
        "weekly forecast predictions",
    )

    daily_summary = (
        calculate_forecast_summary(
            dataframe=daily_data,
            actual_column=(
                "net_gaming_revenue"
            ),
            predicted_column=(
                "predicted_revenue"
            ),
        )
    )

    weekly_summary = (
        calculate_forecast_summary(
            dataframe=weekly_data,
            actual_column=(
                "net_gaming_revenue"
            ),
            predicted_column=(
                "selected_predicted_revenue"
            ),
        )
    )

    daily_best_metric = (
        get_best_metric_row(
            daily_metrics
        )
    )

    weekly_best_metric = (
        get_best_metric_row(
            weekly_metrics
        )
    )

    weekly_method = str(
        weekly_data[
            "selected_forecasting_method"
        ].iloc[0]
    )

    return {
        "daily_forecast": {
            **daily_summary,
            "best_evaluated_model": (
                daily_best_metric.get(
                    "model"
                )
            ),
            "saved_mae": (
                daily_best_metric.get(
                    "mae"
                )
            ),
            "saved_rmse": (
                daily_best_metric.get(
                    "rmse"
                )
            ),
            "saved_mape_pct": (
                daily_best_metric.get(
                    "mape_pct"
                )
            ),
            "saved_wape_pct": (
                daily_best_metric.get(
                    "wape_pct"
                )
            ),
            "saved_r2_score": (
                daily_best_metric.get(
                    "r2_score"
                )
            ),
        },
        "weekly_forecast": {
            **weekly_summary,
            "selected_forecasting_method": (
                weekly_method
            ),
            "best_evaluated_method": (
                weekly_best_metric.get(
                    "model"
                )
            ),
            "saved_mae": (
                weekly_best_metric.get(
                    "mae"
                )
            ),
            "saved_rmse": (
                weekly_best_metric.get(
                    "rmse"
                )
            ),
            "saved_mape_pct": (
                weekly_best_metric.get(
                    "mape_pct"
                )
            ),
            "saved_wape_pct": (
                weekly_best_metric.get(
                    "wape_pct"
                )
            ),
            "saved_r2_score": (
                weekly_best_metric.get(
                    "r2_score"
                )
            ),
        },
    }


@router.get("/daily")
def get_daily_forecast(
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=50,
        ge=1,
        le=500,
    ),
    location_id: str | None = Query(
        default=None,
    ),
    region: str | None = Query(
        default=None,
    ),
    forecast_status: str | None = Query(
        default=None,
    ),
    start_date: str | None = Query(
        default=None,
        description="YYYY-MM-DD",
    ),
    end_date: str | None = Query(
        default=None,
        description="YYYY-MM-DD",
    ),
) -> dict[str, Any]:
    """Return filtered daily forecast records."""

    dataframe = load_csv(
        DAILY_PREDICTIONS_PATH,
        "Daily forecast predictions",
    )

    validate_columns(
        dataframe,
        {
            "activity_date",
            "location_id",
            "net_gaming_revenue",
            "predicted_revenue",
        },
        "daily forecast predictions",
    )

    filtered = dataframe.copy()

    filtered["activity_date"] = (
        pd.to_datetime(
            filtered["activity_date"],
            errors="coerce",
        )
    )

    filtered = filtered.dropna(
        subset=["activity_date"]
    )

    start_timestamp = (
        parse_optional_date(
            start_date,
            "start_date",
        )
    )

    end_timestamp = (
        parse_optional_date(
            end_date,
            "end_date",
        )
    )

    if (
        start_timestamp is not None
        and end_timestamp is not None
        and start_timestamp > end_timestamp
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "start_date cannot be later "
                "than end_date."
            ),
        )

    if location_id:
        filtered = filtered.loc[
            filtered[
                "location_id"
            ].astype(str).str.upper()
            == location_id.upper()
        ]

    if (
        region
        and "region"
        in filtered.columns
    ):
        filtered = filtered.loc[
            filtered[
                "region"
            ].astype(str).str.lower()
            == region.lower()
        ]

    if (
        forecast_status
        and "forecast_status"
        in filtered.columns
    ):
        filtered = filtered.loc[
            filtered[
                "forecast_status"
            ].astype(str).str.lower()
            == forecast_status.lower()
        ]

    if start_timestamp is not None:
        filtered = filtered.loc[
            filtered[
                "activity_date"
            ] >= start_timestamp
        ]

    if end_timestamp is not None:
        filtered = filtered.loc[
            filtered[
                "activity_date"
            ] <= end_timestamp
        ]

    filtered = filtered.sort_values(
        [
            "activity_date",
            "location_id",
        ],
        ascending=[
            False,
            True,
        ],
    ).reset_index(drop=True)

    filtered["activity_date"] = (
        filtered["activity_date"]
        .dt.strftime("%Y-%m-%d")
    )

    response = paginate_dataframe(
        dataframe=filtered,
        page=page,
        page_size=page_size,
    )

    response["filters"] = {
        "location_id": location_id,
        "region": region,
        "forecast_status": forecast_status,
        "start_date": start_date,
        "end_date": end_date,
    }

    return response


@router.get("/weekly")
def get_weekly_forecast(
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=50,
        ge=1,
        le=500,
    ),
    location_id: str | None = Query(
        default=None,
    ),
    region: str | None = Query(
        default=None,
    ),
    forecast_status: str | None = Query(
        default=None,
    ),
    start_date: str | None = Query(
        default=None,
        description="YYYY-MM-DD",
    ),
    end_date: str | None = Query(
        default=None,
        description="YYYY-MM-DD",
    ),
) -> dict[str, Any]:
    """Return filtered weekly forecast records."""

    dataframe = load_csv(
        WEEKLY_PREDICTIONS_PATH,
        "Weekly forecast predictions",
    )

    validate_columns(
        dataframe,
        {
            "week_start_date",
            "location_id",
            "net_gaming_revenue",
            "selected_predicted_revenue",
            "selected_forecasting_method",
        },
        "weekly forecast predictions",
    )

    filtered = dataframe.copy()

    filtered["week_start_date"] = (
        pd.to_datetime(
            filtered["week_start_date"],
            errors="coerce",
        )
    )

    filtered = filtered.dropna(
        subset=["week_start_date"]
    )

    start_timestamp = (
        parse_optional_date(
            start_date,
            "start_date",
        )
    )

    end_timestamp = (
        parse_optional_date(
            end_date,
            "end_date",
        )
    )

    if (
        start_timestamp is not None
        and end_timestamp is not None
        and start_timestamp > end_timestamp
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "start_date cannot be later "
                "than end_date."
            ),
        )

    if location_id:
        filtered = filtered.loc[
            filtered[
                "location_id"
            ].astype(str).str.upper()
            == location_id.upper()
        ]

    if (
        region
        and "region"
        in filtered.columns
    ):
        filtered = filtered.loc[
            filtered[
                "region"
            ].astype(str).str.lower()
            == region.lower()
        ]

    if (
        forecast_status
        and "forecast_status"
        in filtered.columns
    ):
        filtered = filtered.loc[
            filtered[
                "forecast_status"
            ].astype(str).str.lower()
            == forecast_status.lower()
        ]

    if start_timestamp is not None:
        filtered = filtered.loc[
            filtered[
                "week_start_date"
            ] >= start_timestamp
        ]

    if end_timestamp is not None:
        filtered = filtered.loc[
            filtered[
                "week_start_date"
            ] <= end_timestamp
        ]

    filtered = filtered.sort_values(
        [
            "week_start_date",
            "location_id",
        ],
        ascending=[
            False,
            True,
        ],
    ).reset_index(drop=True)

    selected_method = (
        str(
            filtered[
                "selected_forecasting_method"
            ].iloc[0]
        )
        if not filtered.empty
        else None
    )

    filtered["week_start_date"] = (
        filtered["week_start_date"]
        .dt.strftime("%Y-%m-%d")
    )

    response = paginate_dataframe(
        dataframe=filtered,
        page=page,
        page_size=page_size,
    )

    response[
        "selected_forecasting_method"
    ] = selected_method

    response["filters"] = {
        "location_id": location_id,
        "region": region,
        "forecast_status": forecast_status,
        "start_date": start_date,
        "end_date": end_date,
    }

    return response


@router.get("/model-comparison")
def get_forecast_model_comparison() -> dict[str, Any]:
    """Return forecasting metrics and governance decisions."""

    daily_metrics = load_csv(
        DAILY_METRICS_PATH,
        "Daily forecast model metrics",
    )

    weekly_metrics = load_csv(
        WEEKLY_METRICS_PATH,
        "Weekly forecast model metrics",
    )

    location_summary = load_csv(
        WEEKLY_LOCATION_SUMMARY_PATH,
        "Weekly location forecast summary",
    )

    for dataframe in [
        daily_metrics,
        weekly_metrics,
    ]:
        if "rmse" in dataframe.columns:
            dataframe["rmse"] = (
                pd.to_numeric(
                    dataframe["rmse"],
                    errors="coerce",
                )
            )

    daily_metrics = (
        daily_metrics.sort_values(
            "rmse",
            na_position="last",
        )
        .reset_index(drop=True)
    )

    weekly_metrics = (
        weekly_metrics.sort_values(
            "rmse",
            na_position="last",
        )
        .reset_index(drop=True)
    )

    if (
        "average_selected_absolute_error"
        in location_summary.columns
    ):
        location_summary[
            "average_selected_absolute_error"
        ] = pd.to_numeric(
            location_summary[
                "average_selected_absolute_error"
            ],
            errors="coerce",
        )

        location_summary = (
            location_summary.sort_values(
                "average_selected_absolute_error",
                na_position="last",
            )
            .reset_index(drop=True)
        )

    selection_metadata = None

    if WEEKLY_SELECTION_PATH.exists():
        try:
            selection_metadata = (
                WEEKLY_SELECTION_PATH.read_text(
                    encoding="utf-8"
                )
            )
        except OSError as error:
            selection_metadata = (
                "Unable to read weekly "
                f"selection metadata: {error}"
            )

    return {
        "daily_model_comparison": (
            dataframe_to_records(
                daily_metrics
            )
        ),
        "weekly_model_comparison": (
            dataframe_to_records(
                weekly_metrics
            )
        ),
        "weekly_location_summary": (
            dataframe_to_records(
                location_summary
            )
        ),
        "weekly_governance_metadata": (
            selection_metadata
        ),
    }


@router.get("/location/{location_id}")
def get_location_forecast(
    location_id: str,
) -> dict[str, Any]:
    """Return daily and weekly forecasts for one location."""

    daily_data = load_csv(
        DAILY_PREDICTIONS_PATH,
        "Daily forecast predictions",
    )

    weekly_data = load_csv(
        WEEKLY_PREDICTIONS_PATH,
        "Weekly forecast predictions",
    )

    validate_columns(
        daily_data,
        {
            "location_id",
            "activity_date",
            "net_gaming_revenue",
            "predicted_revenue",
        },
        "daily forecast predictions",
    )

    validate_columns(
        weekly_data,
        {
            "location_id",
            "week_start_date",
            "net_gaming_revenue",
            "selected_predicted_revenue",
        },
        "weekly forecast predictions",
    )

    normalized_location_id = (
        location_id.upper()
    )

    daily_match = daily_data.loc[
        daily_data[
            "location_id"
        ].astype(str).str.upper()
        == normalized_location_id
    ].copy()

    weekly_match = weekly_data.loc[
        weekly_data[
            "location_id"
        ].astype(str).str.upper()
        == normalized_location_id
    ].copy()

    if (
        daily_match.empty
        and weekly_match.empty
    ):
        raise HTTPException(
            status_code=404,
            detail=(
                f"Location "
                f"{normalized_location_id} "
                "was not found."
            ),
        )

    location_name = None

    for candidate in [
        daily_match,
        weekly_match,
    ]:
        if (
            not candidate.empty
            and "location_name"
            in candidate.columns
        ):
            location_name = str(
                candidate[
                    "location_name"
                ].iloc[0]
            )
            break

    if not daily_match.empty:
        daily_match["activity_date"] = (
            pd.to_datetime(
                daily_match[
                    "activity_date"
                ],
                errors="coerce",
            )
        )

        daily_match = (
            daily_match.sort_values(
                "activity_date",
                ascending=False,
            )
        )

        daily_match["activity_date"] = (
            daily_match[
                "activity_date"
            ].dt.strftime(
                "%Y-%m-%d"
            )
        )

    if not weekly_match.empty:
        weekly_match[
            "week_start_date"
        ] = pd.to_datetime(
            weekly_match[
                "week_start_date"
            ],
            errors="coerce",
        )

        weekly_match = (
            weekly_match.sort_values(
                "week_start_date",
                ascending=False,
            )
        )

        weekly_match[
            "week_start_date"
        ] = weekly_match[
            "week_start_date"
        ].dt.strftime(
            "%Y-%m-%d"
        )

    daily_summary = (
        calculate_forecast_summary(
            dataframe=daily_match,
            actual_column=(
                "net_gaming_revenue"
            ),
            predicted_column=(
                "predicted_revenue"
            ),
        )
        if not daily_match.empty
        else None
    )

    weekly_summary = (
        calculate_forecast_summary(
            dataframe=weekly_match,
            actual_column=(
                "net_gaming_revenue"
            ),
            predicted_column=(
                "selected_predicted_revenue"
            ),
        )
        if not weekly_match.empty
        else None
    )

    return {
        "location_id": (
            normalized_location_id
        ),
        "location_name": location_name,
        "daily_summary": daily_summary,
        "weekly_summary": weekly_summary,
        "recent_daily_forecasts": (
            dataframe_to_records(
                daily_match.head(30)
            )
        ),
        "recent_weekly_forecasts": (
            dataframe_to_records(
                weekly_match.head(12)
            )
        ),
    }
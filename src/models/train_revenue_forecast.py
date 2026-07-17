import os
import sys
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import pyodbc
from dotenv import load_dotenv
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    GradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import (
    OneHotEncoder,
    StandardScaler,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


MODELS_DIR = PROJECT_ROOT / "models"

ML_DATA_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "ml"
)

METRICS_DIR = (
    PROJECT_ROOT
    / "reports"
    / "model_metrics"
)

TARGET_COLUMN = "net_gaming_revenue"
DATE_COLUMN = "activity_date"
RANDOM_SEED = 42


# These categorical values are known before the forecast date.
CATEGORICAL_COLUMNS = [
    "location_id",
    "region",
    "location_type",
    "day_of_week_name",
]


# Only calendar and historical lag features are used.
# Same-day wager, payout, session, transaction, and event data
# are excluded to prevent target leakage.
NUMERIC_COLUMNS = [
    "activity_year",
    "activity_month",
    "activity_quarter",
    "day_of_week_number",
    "is_weekend",
    "revenue_lag_1_day",
    "revenue_lag_7_days",
    "revenue_lag_14_days",
    "previous_7_day_average_revenue",
    "previous_30_day_average_revenue",
    "previous_7_day_average_sessions",
]


FEATURE_COLUMNS = (
    CATEGORICAL_COLUMNS
    + NUMERIC_COLUMNS
)


def create_directories() -> None:
    """Create model and reporting directories."""

    MODELS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    ML_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    METRICS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


def build_connection_string() -> str:
    """Build SQL Server connection string from the .env file."""

    load_dotenv(
        PROJECT_ROOT / ".env"
    )

    required_variables = [
        "SQL_SERVER",
        "SQL_DATABASE",
        "SQL_USERNAME",
        "SQL_PASSWORD",
        "SQL_DRIVER",
    ]

    missing_variables = [
        variable
        for variable in required_variables
        if not os.getenv(variable)
    ]

    if missing_variables:
        raise ValueError(
            "Missing required environment variables: "
            + ", ".join(missing_variables)
        )

    return (
        f"DRIVER={{{os.getenv('SQL_DRIVER')}}};"
        f"SERVER={os.getenv('SQL_SERVER')};"
        f"DATABASE={os.getenv('SQL_DATABASE')};"
        f"UID={os.getenv('SQL_USERNAME')};"
        f"PWD={os.getenv('SQL_PASSWORD')};"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
    )


def load_forecasting_dataset() -> pd.DataFrame:
    """Load the revenue forecasting view from SQL Server."""

    query = """
        SELECT *
        FROM dbo.vw_ml_revenue_forecast
        ORDER BY
            activity_date,
            location_id;
    """

    connection = None

    try:
        connection = pyodbc.connect(
            build_connection_string(),
            timeout=15,
        )

        dataframe = pd.read_sql(
            query,
            connection,
        )

    finally:
        if connection is not None:
            connection.close()

    if dataframe.empty:
        raise ValueError(
            "Revenue forecast view returned zero rows."
        )

    return dataframe


def validate_dataset(
    dataframe: pd.DataFrame,
) -> None:
    """Validate required columns and target values."""

    required_columns = {
        DATE_COLUMN,
        TARGET_COLUMN,
        *FEATURE_COLUMNS,
    }

    missing_columns = required_columns.difference(
        dataframe.columns
    )

    if missing_columns:
        raise ValueError(
            "Required columns are missing: "
            + ", ".join(
                sorted(missing_columns)
            )
        )

    if dataframe[
        DATE_COLUMN
    ].isna().any():
        raise ValueError(
            "Null activity dates were found."
        )

    if dataframe[
        TARGET_COLUMN
    ].isna().any():
        raise ValueError(
            "Null revenue targets were found."
        )


def prepare_dataset(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Clean the dataset and remove records without sufficient
    historical lag information.
    """

    output = dataframe.copy()

    output[
        DATE_COLUMN
    ] = pd.to_datetime(
        output[DATE_COLUMN],
        errors="coerce",
    )

    for column in (
        NUMERIC_COLUMNS
        + [TARGET_COLUMN]
    ):
        output[column] = pd.to_numeric(
            output[column],
            errors="coerce",
        )

    if output[
        DATE_COLUMN
    ].isna().any():
        raise ValueError(
            "Some activity dates could not be parsed."
        )

    required_lag_columns = [
        "revenue_lag_1_day",
        "revenue_lag_7_days",
        "revenue_lag_14_days",
        "previous_7_day_average_revenue",
        "previous_30_day_average_revenue",
        "previous_7_day_average_sessions",
    ]

    output = output.dropna(
        subset=required_lag_columns
    ).copy()

    output = output.dropna(
        subset=[TARGET_COLUMN]
    ).copy()

    output = output.sort_values(
        [
            DATE_COLUMN,
            "location_id",
        ]
    ).reset_index(drop=True)

    if len(output) < 100:
        raise ValueError(
            "Too few usable forecasting rows remain "
            "after removing incomplete lag records."
        )

    return output


def chronological_split(
    dataframe: pd.DataFrame,
    test_fraction: float = 0.20,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split data chronologically so future dates never appear
    in the training dataset.
    """

    unique_dates = np.sort(
        dataframe[
            DATE_COLUMN
        ].dt.normalize().unique()
    )

    if len(unique_dates) < 2:
        raise ValueError(
            "At least two unique dates are required."
        )

    split_index = int(
        len(unique_dates)
        * (1 - test_fraction)
    )

    split_index = max(
        1,
        min(
            split_index,
            len(unique_dates) - 1,
        ),
    )

    cutoff_date = pd.Timestamp(
        unique_dates[split_index]
    )

    train_data = dataframe.loc[
        dataframe[DATE_COLUMN]
        < cutoff_date
    ].copy()

    test_data = dataframe.loc[
        dataframe[DATE_COLUMN]
        >= cutoff_date
    ].copy()

    if train_data.empty:
        raise ValueError(
            "Chronological split produced an "
            "empty training dataset."
        )

    if test_data.empty:
        raise ValueError(
            "Chronological split produced an "
            "empty testing dataset."
        )

    print(
        "Training through:",
        train_data[
            DATE_COLUMN
        ].max().date(),
    )

    print(
        "Testing from:",
        test_data[
            DATE_COLUMN
        ].min().date(),
    )

    return train_data, test_data


def build_preprocessor() -> ColumnTransformer:
    """Build numeric and categorical preprocessing pipelines."""

    numeric_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="median",
                ),
            ),
            (
                "scaler",
                StandardScaler(),
            ),
        ]
    )

    categorical_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="most_frequent",
                ),
            ),
            (
                "encoder",
                OneHotEncoder(
                    handle_unknown="ignore",
                ),
            ),
        ]
    )

    return ColumnTransformer(
        transformers=[
            (
                "numeric",
                numeric_pipeline,
                NUMERIC_COLUMNS,
            ),
            (
                "categorical",
                categorical_pipeline,
                CATEGORICAL_COLUMNS,
            ),
        ]
    )


def build_models() -> dict[str, Pipeline]:
    """Create leakage-free forecasting models."""

    random_forest = Pipeline(
        steps=[
            (
                "preprocessor",
                build_preprocessor(),
            ),
            (
                "model",
                RandomForestRegressor(
                    n_estimators=500,
                    max_depth=14,
                    min_samples_split=8,
                    min_samples_leaf=3,
                    max_features="sqrt",
                    n_jobs=-1,
                    random_state=RANDOM_SEED,
                ),
            ),
        ]
    )

    gradient_boosting = Pipeline(
        steps=[
            (
                "preprocessor",
                build_preprocessor(),
            ),
            (
                "model",
                GradientBoostingRegressor(
                    n_estimators=300,
                    learning_rate=0.03,
                    max_depth=3,
                    min_samples_split=8,
                    min_samples_leaf=4,
                    loss="huber",
                    random_state=RANDOM_SEED,
                ),
            ),
        ]
    )

    return {
        "Random Forest Regressor": (
            random_forest
        ),
        "Gradient Boosting Regressor": (
            gradient_boosting
        ),
    }


def calculate_mape(
    actual: pd.Series,
    predicted: np.ndarray,
) -> float:
    """
    Calculate MAPE while excluding actual values close to zero.

    MAPE is included for reference, but it can be unstable
    because daily gaming revenue may be small or negative.
    """

    actual_array = np.asarray(
        actual,
        dtype=float,
    )

    predicted_array = np.asarray(
        predicted,
        dtype=float,
    )

    nonzero_mask = (
        np.abs(actual_array) > 1.0
    )

    if not nonzero_mask.any():
        return float("nan")

    absolute_percentage_errors = np.abs(
        (
            actual_array[nonzero_mask]
            - predicted_array[nonzero_mask]
        )
        / actual_array[nonzero_mask]
    )

    return float(
        absolute_percentage_errors.mean()
        * 100
    )


def calculate_wape(
    actual: pd.Series,
    predicted: np.ndarray,
) -> float:
    """
    Calculate weighted absolute percentage error.

    WAPE is more stable than MAPE when actual values are
    near zero or negative.
    """

    actual_array = np.asarray(
        actual,
        dtype=float,
    )

    predicted_array = np.asarray(
        predicted,
        dtype=float,
    )

    denominator = np.sum(
        np.abs(actual_array)
    )

    if denominator == 0:
        return float("nan")

    numerator = np.sum(
        np.abs(
            actual_array
            - predicted_array
        )
    )

    return float(
        numerator
        / denominator
        * 100
    )


def evaluate_model(
    model_name: str,
    model: Pipeline,
    x_train: pd.DataFrame,
    x_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series,
) -> tuple[
    dict[str, Any],
    np.ndarray,
]:
    """Train and evaluate one forecasting model."""

    print(
        f"\nTraining {model_name}..."
    )

    model.fit(
        x_train,
        y_train,
    )

    predictions = model.predict(
        x_test
    )

    mae = mean_absolute_error(
        y_test,
        predictions,
    )

    rmse = np.sqrt(
        mean_squared_error(
            y_test,
            predictions,
        )
    )

    r2 = r2_score(
        y_test,
        predictions,
    )

    mape = calculate_mape(
        y_test,
        predictions,
    )

    wape = calculate_wape(
        y_test,
        predictions,
    )

    metrics = {
        "model": model_name,
        "mae": mae,
        "rmse": rmse,
        "mape_pct": mape,
        "wape_pct": wape,
        "r2_score": r2,
    }

    print(
        f"MAE: ${mae:,.2f}"
    )

    print(
        f"RMSE: ${rmse:,.2f}"
    )

    print(
        f"MAPE: {mape:,.2f}%"
    )

    print(
        f"WAPE: {wape:,.2f}%"
    )

    print(
        f"R²: {r2:.4f}"
    )

    return metrics, predictions


def create_naive_baseline(
    test_data: pd.DataFrame,
) -> tuple[
    dict[str, Any],
    np.ndarray,
]:
    """Use the previous available daily revenue as baseline."""

    predictions = test_data[
        "revenue_lag_1_day"
    ].to_numpy(
        dtype=float
    )

    actual = test_data[
        TARGET_COLUMN
    ]

    mae = mean_absolute_error(
        actual,
        predictions,
    )

    rmse = np.sqrt(
        mean_squared_error(
            actual,
            predictions,
        )
    )

    mape = calculate_mape(
        actual,
        predictions,
    )

    wape = calculate_wape(
        actual,
        predictions,
    )

    r2 = r2_score(
        actual,
        predictions,
    )

    metrics = {
        "model": (
            "Naive Previous-Day Baseline"
        ),
        "mae": mae,
        "rmse": rmse,
        "mape_pct": mape,
        "wape_pct": wape,
        "r2_score": r2,
    }

    return metrics, predictions


def extract_feature_importance(
    model: Pipeline,
) -> pd.DataFrame:
    """Extract feature importance from the selected model."""

    preprocessor = model.named_steps[
        "preprocessor"
    ]

    estimator = model.named_steps[
        "model"
    ]

    feature_names = (
        preprocessor
        .get_feature_names_out()
    )

    cleaned_names = [
        name.replace(
            "numeric__",
            "",
        ).replace(
            "categorical__",
            "",
        )
        for name in feature_names
    ]

    if not hasattr(
        estimator,
        "feature_importances_",
    ):
        raise ValueError(
            "Selected model does not expose "
            "feature importances."
        )

    importance_values = (
        estimator.feature_importances_
    )

    output = pd.DataFrame(
        {
            "feature": cleaned_names,
            "feature_importance": (
                importance_values
            ),
        }
    )

    return output.sort_values(
        "feature_importance",
        ascending=False,
    ).reset_index(drop=True)


def create_forecast_output(
    test_data: pd.DataFrame,
    predictions: np.ndarray,
    baseline_predictions: np.ndarray,
) -> pd.DataFrame:
    """Create Power BI-ready forecasting results."""

    reporting_columns = [
        DATE_COLUMN,
        "location_id",
        "location_name",
        "region",
        "location_type",
        "session_count",
        "unique_player_count",
        "active_machine_count",
        "total_wager",
        "event_count",
        "downtime_minutes",
        "critical_event_count",
        TARGET_COLUMN,
    ]

    available_columns = [
        column
        for column in reporting_columns
        if column in test_data.columns
    ]

    output = test_data[
        available_columns
    ].copy()

    output[
        "predicted_revenue"
    ] = predictions

    output[
        "baseline_predicted_revenue"
    ] = baseline_predictions

    output[
        "forecast_error"
    ] = (
        output[TARGET_COLUMN]
        - output[
            "predicted_revenue"
        ]
    )

    output[
        "absolute_error"
    ] = output[
        "forecast_error"
    ].abs()

    output[
        "absolute_percentage_error"
    ] = np.where(
        output[
            TARGET_COLUMN
        ].abs() > 1.0,
        (
            output[
                "absolute_error"
            ]
            / output[
                TARGET_COLUMN
            ].abs()
        )
        * 100,
        np.nan,
    )

    output[
        "forecast_status"
    ] = np.select(
        [
            output[
                "absolute_percentage_error"
            ] <= 10,

            output[
                "absolute_percentage_error"
            ] <= 25,
        ],
        [
            "High Accuracy",
            "Acceptable",
        ],
        default="Review",
    )

    return output.sort_values(
        [
            DATE_COLUMN,
            "location_id",
        ]
    ).reset_index(drop=True)


def save_outputs(
    best_model_name: str,
    best_model: Pipeline,
    metrics_dataframe: pd.DataFrame,
    forecast_output: pd.DataFrame,
    feature_importance: pd.DataFrame,
) -> None:
    """Save model, metrics, predictions, and metadata."""

    model_path = (
        MODELS_DIR
        / "revenue_forecast_best_model.joblib"
    )

    metrics_path = (
        METRICS_DIR
        / "revenue_forecast_model_metrics.csv"
    )

    predictions_path = (
        ML_DATA_DIR
        / "revenue_forecast_predictions.csv"
    )

    importance_path = (
        METRICS_DIR
        / "revenue_forecast_feature_importance.csv"
    )

    metadata_path = (
        METRICS_DIR
        / "revenue_forecast_best_model.txt"
    )

    joblib.dump(
        best_model,
        model_path,
    )

    metrics_dataframe.to_csv(
        metrics_path,
        index=False,
    )

    forecast_output.to_csv(
        predictions_path,
        index=False,
    )

    feature_importance.to_csv(
        importance_path,
        index=False,
    )

    metadata_path.write_text(
        (
            f"Best model: {best_model_name}\n"
            "Selection metric: RMSE\n"
            "Validation method: "
            "Chronological holdout\n"
            "Leakage controls: Same-day wager, "
            "payout, session, transaction and event "
            "fields excluded from model features\n"
            "Dataset type: Synthetic daily gaming "
            "revenue dataset\n"
        ),
        encoding="utf-8",
    )

    print("\nSaved outputs:")
    print(
        f"Model: {model_path}"
    )
    print(
        f"Metrics: {metrics_path}"
    )
    print(
        f"Predictions: {predictions_path}"
    )
    print(
        f"Feature importance: "
        f"{importance_path}"
    )
    print(
        f"Metadata: {metadata_path}"
    )


def main() -> None:
    """Run the complete forecasting pipeline."""

    create_directories()

    print(
        "Loading revenue forecast dataset "
        "from SQL Server..."
    )

    dataframe = (
        load_forecasting_dataset()
    )

    validate_dataset(
        dataframe
    )

    prepared_data = prepare_dataset(
        dataframe
    )

    dataset_path = (
        ML_DATA_DIR
        / "revenue_forecast_dataset.csv"
    )

    prepared_data.to_csv(
        dataset_path,
        index=False,
    )

    print(
        f"Raw rows: {len(dataframe):,}"
    )

    print(
        f"Usable rows: "
        f"{len(prepared_data):,}"
    )

    print(
        "Date range:",
        prepared_data[
            DATE_COLUMN
        ].min().date(),
        "to",
        prepared_data[
            DATE_COLUMN
        ].max().date(),
    )

    train_data, test_data = (
        chronological_split(
            prepared_data,
            test_fraction=0.20,
        )
    )

    x_train = train_data[
        FEATURE_COLUMNS
    ].copy()

    y_train = train_data[
        TARGET_COLUMN
    ].copy()

    x_test = test_data[
        FEATURE_COLUMNS
    ].copy()

    y_test = test_data[
        TARGET_COLUMN
    ].copy()

    print(
        f"Training rows: "
        f"{len(train_data):,}"
    )

    print(
        f"Testing rows: "
        f"{len(test_data):,}"
    )

    (
        baseline_metrics,
        baseline_predictions,
    ) = create_naive_baseline(
        test_data
    )

    print(
        "\nNaive Previous-Day Baseline:"
    )

    print(
        f"MAE: "
        f"${baseline_metrics['mae']:,.2f}"
    )

    print(
        f"RMSE: "
        f"${baseline_metrics['rmse']:,.2f}"
    )

    print(
        f"MAPE: "
        f"{baseline_metrics['mape_pct']:,.2f}%"
    )

    print(
        f"WAPE: "
        f"{baseline_metrics['wape_pct']:,.2f}%"
    )

    print(
        f"R²: "
        f"{baseline_metrics['r2_score']:.4f}"
    )

    metrics_records = [
        baseline_metrics
    ]

    model_results: dict[
        str,
        dict[str, Any],
    ] = {}

    models = build_models()

    for model_name, model in models.items():
        metrics, predictions = (
            evaluate_model(
                model_name=model_name,
                model=model,
                x_train=x_train,
                x_test=x_test,
                y_train=y_train,
                y_test=y_test,
            )
        )

        metrics_records.append(
            metrics
        )

        model_results[
            model_name
        ] = {
            "model": model,
            "predictions": predictions,
        }

    metrics_dataframe = pd.DataFrame(
        metrics_records
    ).sort_values(
        "rmse",
        ascending=True,
    ).reset_index(drop=True)

    eligible_models = (
        metrics_dataframe.loc[
            metrics_dataframe[
                "model"
            ]
            != "Naive Previous-Day Baseline"
        ]
    )

    if eligible_models.empty:
        raise ValueError(
            "No trainable forecasting models "
            "were evaluated."
        )

    best_model_name = str(
        eligible_models.iloc[0][
            "model"
        ]
    )

    best_model = model_results[
        best_model_name
    ]["model"]

    best_predictions = model_results[
        best_model_name
    ]["predictions"]

    feature_importance = (
        extract_feature_importance(
            best_model
        )
    )

    forecast_output = (
        create_forecast_output(
            test_data=test_data,
            predictions=best_predictions,
            baseline_predictions=(
                baseline_predictions
            ),
        )
    )

    baseline_rmse = float(
        baseline_metrics["rmse"]
    )

    best_rmse = float(
        eligible_models.iloc[0]["rmse"]
    )

    rmse_improvement_pct = (
        (
            baseline_rmse
            - best_rmse
        )
        / baseline_rmse
        * 100
        if baseline_rmse != 0
        else float("nan")
    )

    print("\nModel comparison:")

    print(
        metrics_dataframe.to_string(
            index=False
        )
    )

    print(
        f"\nSelected best model: "
        f"{best_model_name}"
    )

    print(
        "RMSE improvement over baseline: "
        f"{rmse_improvement_pct:.2f}%"
    )

    print(
        "\nTop 10 forecasting features:"
    )

    print(
        feature_importance.head(
            10
        ).to_string(
            index=False
        )
    )

    save_outputs(
        best_model_name=(
            best_model_name
        ),
        best_model=best_model,
        metrics_dataframe=(
            metrics_dataframe
        ),
        forecast_output=(
            forecast_output
        ),
        feature_importance=(
            feature_importance
        ),
    )


if __name__ == "__main__":
    main()
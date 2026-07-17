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
from sklearn.preprocessing import OneHotEncoder, StandardScaler


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
DATE_COLUMN = "week_start_date"
RANDOM_SEED = 42

BASELINE_MODEL_NAME = (
    "Naive Previous-Week Baseline"
)


CATEGORICAL_COLUMNS = [
    "location_id",
    "region",
    "location_type",
]


NUMERIC_COLUMNS = [
    "activity_year",
    "activity_quarter",
    "activity_month",
    "iso_week_number",
    "revenue_lag_1_week",
    "revenue_lag_2_weeks",
    "revenue_lag_4_weeks",
    "previous_4_week_average_revenue",
    "previous_8_week_average_revenue",
    "previous_4_week_average_sessions",
]


FEATURE_COLUMNS = (
    CATEGORICAL_COLUMNS
    + NUMERIC_COLUMNS
)


def create_directories() -> None:
    """Create model, metrics, and processed-data directories."""

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
    """Build SQL Server connection string from .env."""

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


def load_weekly_dataset() -> pd.DataFrame:
    """Load weekly revenue forecasting data from SQL Server."""

    query = """
        SELECT *
        FROM dbo.vw_ml_weekly_revenue_forecast
        ORDER BY
            week_start_date,
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
            "The weekly revenue forecasting view "
            "returned zero rows."
        )

    return dataframe


def validate_dataset(
    dataframe: pd.DataFrame,
) -> None:
    """Validate required fields and target quality."""

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
            "Null weekly dates were found."
        )

    if dataframe[
        TARGET_COLUMN
    ].isna().any():
        raise ValueError(
            "Null weekly revenue targets were found."
        )


def prepare_dataset(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Clean the dataset and remove weeks without sufficient
    historical lag features.
    """

    output = dataframe.copy()

    output[
        DATE_COLUMN
    ] = pd.to_datetime(
        output[DATE_COLUMN],
        errors="coerce",
    )

    if output[
        DATE_COLUMN
    ].isna().any():
        raise ValueError(
            "Some week_start_date values could not be parsed."
        )

    for column in (
        NUMERIC_COLUMNS
        + [TARGET_COLUMN]
    ):
        output[column] = pd.to_numeric(
            output[column],
            errors="coerce",
        )

    required_lag_columns = [
        "revenue_lag_1_week",
        "revenue_lag_2_weeks",
        "revenue_lag_4_weeks",
        "previous_4_week_average_revenue",
        "previous_8_week_average_revenue",
        "previous_4_week_average_sessions",
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
            "Too few weekly records remain after "
            "removing incomplete lag rows."
        )

    if output[
        DATE_COLUMN
    ].nunique() < 10:
        raise ValueError(
            "At least 10 distinct weeks are required "
            "for chronological validation."
        )

    return output


def chronological_split(
    dataframe: pd.DataFrame,
    test_fraction: float = 0.20,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split the data chronologically using complete weeks."""

    unique_dates = np.sort(
        dataframe[
            DATE_COLUMN
        ].dt.normalize().unique()
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
            "The chronological split produced "
            "an empty training dataset."
        )

    if test_data.empty:
        raise ValueError(
            "The chronological split produced "
            "an empty testing dataset."
        )

    if (
        train_data[DATE_COLUMN].max()
        >= test_data[DATE_COLUMN].min()
    ):
        raise ValueError(
            "Training and testing date ranges overlap."
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

    print(
        "Training weeks:",
        f"{train_data[DATE_COLUMN].nunique():,}",
    )

    print(
        "Testing weeks:",
        f"{test_data[DATE_COLUMN].nunique():,}",
    )

    return train_data, test_data


def build_preprocessor() -> ColumnTransformer:
    """Create numeric and categorical preprocessing."""

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
    """Create weekly revenue forecasting models."""

    random_forest = Pipeline(
        steps=[
            (
                "preprocessor",
                build_preprocessor(),
            ),
            (
                "model",
                RandomForestRegressor(
                    n_estimators=600,
                    max_depth=12,
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
                    learning_rate=0.025,
                    max_depth=2,
                    min_samples_split=8,
                    min_samples_leaf=4,
                    loss="huber",
                    random_state=RANDOM_SEED,
                ),
            ),
        ]
    )

    return {
        "Random Forest Regressor": random_forest,
        "Gradient Boosting Regressor": gradient_boosting,
    }


def calculate_mape(
    actual: pd.Series,
    predicted: np.ndarray,
) -> float:
    """Calculate MAPE while excluding values close to zero."""

    actual_array = np.asarray(
        actual,
        dtype=float,
    )

    predicted_array = np.asarray(
        predicted,
        dtype=float,
    )

    usable_mask = (
        np.abs(actual_array) > 1.0
    )

    if not usable_mask.any():
        return float("nan")

    return float(
        np.mean(
            np.abs(
                (
                    actual_array[usable_mask]
                    - predicted_array[usable_mask]
                )
                / actual_array[usable_mask]
            )
        )
        * 100
    )


def calculate_wape(
    actual: pd.Series,
    predicted: np.ndarray,
) -> float:
    """Calculate weighted absolute percentage error."""

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


def calculate_metrics(
    model_name: str,
    actual: pd.Series,
    predicted: np.ndarray,
) -> dict[str, Any]:
    """Calculate forecasting metrics."""

    mae = mean_absolute_error(
        actual,
        predicted,
    )

    rmse = np.sqrt(
        mean_squared_error(
            actual,
            predicted,
        )
    )

    mape = calculate_mape(
        actual,
        predicted,
    )

    wape = calculate_wape(
        actual,
        predicted,
    )

    r2 = r2_score(
        actual,
        predicted,
    )

    return {
        "model": model_name,
        "mae": mae,
        "rmse": rmse,
        "mape_pct": mape,
        "wape_pct": wape,
        "r2_score": r2,
    }


def print_metrics(
    metrics: dict[str, Any],
) -> None:
    """Print formatted forecasting metrics."""

    print(
        f"MAE: ${metrics['mae']:,.2f}"
    )

    print(
        f"RMSE: ${metrics['rmse']:,.2f}"
    )

    print(
        f"MAPE: {metrics['mape_pct']:,.2f}%"
    )

    print(
        f"WAPE: {metrics['wape_pct']:,.2f}%"
    )

    print(
        f"R²: {metrics['r2_score']:.4f}"
    )


def create_naive_baseline(
    test_data: pd.DataFrame,
) -> tuple[dict[str, Any], np.ndarray]:
    """Use previous-week revenue as the naive baseline."""

    predictions = test_data[
        "revenue_lag_1_week"
    ].to_numpy(
        dtype=float
    )

    metrics = calculate_metrics(
        model_name=BASELINE_MODEL_NAME,
        actual=test_data[
            TARGET_COLUMN
        ],
        predicted=predictions,
    )

    return metrics, predictions


def evaluate_model(
    model_name: str,
    model: Pipeline,
    x_train: pd.DataFrame,
    x_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series,
) -> tuple[dict[str, Any], np.ndarray]:
    """Train and evaluate a machine-learning model."""

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

    metrics = calculate_metrics(
        model_name=model_name,
        actual=y_test,
        predicted=predictions,
    )

    print_metrics(
        metrics
    )

    return metrics, predictions


def extract_feature_importance(
    model: Pipeline,
) -> pd.DataFrame:
    """Extract feature importance from the fitted ML model."""

    preprocessor = model.named_steps[
        "preprocessor"
    ]

    estimator = model.named_steps[
        "model"
    ]

    if not hasattr(
        estimator,
        "feature_importances_",
    ):
        raise ValueError(
            "The selected model does not expose "
            "feature importances."
        )

    feature_names = (
        preprocessor
        .get_feature_names_out()
    )

    cleaned_feature_names = [
        name.replace(
            "numeric__",
            "",
        ).replace(
            "categorical__",
            "",
        )
        for name in feature_names
    ]

    importance_values = (
        estimator.feature_importances_
    )

    if (
        len(cleaned_feature_names)
        != len(importance_values)
    ):
        raise ValueError(
            "Feature names and importance values "
            "do not have matching lengths."
        )

    output = pd.DataFrame(
        {
            "feature": cleaned_feature_names,
            "feature_importance": importance_values,
        }
    )

    return output.sort_values(
        "feature_importance",
        ascending=False,
    ).reset_index(drop=True)


def create_forecast_output(
    test_data: pd.DataFrame,
    selected_predictions: np.ndarray,
    best_ml_predictions: np.ndarray,
    baseline_predictions: np.ndarray,
    selected_method: str,
) -> pd.DataFrame:
    """Create Power BI-ready weekly forecasting results."""

    reporting_columns = [
        DATE_COLUMN,
        "location_id",
        "location_name",
        "region",
        "location_type",
        "transaction_count",
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
        "selected_forecasting_method"
    ] = selected_method

    output[
        "selected_predicted_revenue"
    ] = selected_predictions

    output[
        "best_ml_predicted_revenue"
    ] = best_ml_predictions

    output[
        "baseline_predicted_revenue"
    ] = baseline_predictions

    output[
        "selected_forecast_error"
    ] = (
        output[TARGET_COLUMN]
        - output[
            "selected_predicted_revenue"
        ]
    )

    output[
        "selected_absolute_error"
    ] = output[
        "selected_forecast_error"
    ].abs()

    output[
        "ml_absolute_error"
    ] = (
        output[TARGET_COLUMN]
        - output[
            "best_ml_predicted_revenue"
        ]
    ).abs()

    output[
        "baseline_absolute_error"
    ] = (
        output[TARGET_COLUMN]
        - output[
            "baseline_predicted_revenue"
        ]
    ).abs()

    output[
        "ml_beats_baseline_flag"
    ] = (
        output[
            "ml_absolute_error"
        ]
        < output[
            "baseline_absolute_error"
        ]
    ).astype(int)

    output[
        "selected_absolute_percentage_error"
    ] = np.where(
        output[
            TARGET_COLUMN
        ].abs() > 1.0,
        (
            output[
                "selected_absolute_error"
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
                "selected_absolute_percentage_error"
            ] <= 10,

            output[
                "selected_absolute_percentage_error"
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


def build_location_summary(
    forecast_output: pd.DataFrame,
) -> pd.DataFrame:
    """Summarize selected forecast accuracy by location."""

    summary = (
        forecast_output
        .groupby(
            [
                "location_id",
                "location_name",
            ],
            as_index=False,
        )
        .agg(
            test_week_count=(
                DATE_COLUMN,
                "count",
            ),
            actual_revenue=(
                TARGET_COLUMN,
                "sum",
            ),
            selected_predicted_revenue=(
                "selected_predicted_revenue",
                "sum",
            ),
            average_selected_absolute_error=(
                "selected_absolute_error",
                "mean",
            ),
            median_selected_absolute_error=(
                "selected_absolute_error",
                "median",
            ),
            ml_beats_baseline_rate=(
                "ml_beats_baseline_flag",
                "mean",
            ),
        )
    )

    summary[
        "selected_total_forecast_error"
    ] = (
        summary[
            "actual_revenue"
        ]
        - summary[
            "selected_predicted_revenue"
        ]
    )

    return summary.sort_values(
        "average_selected_absolute_error"
    ).reset_index(drop=True)


def save_outputs(
    selected_forecasting_method: str,
    best_ml_model_name: str,
    best_ml_model: Pipeline,
    metrics_dataframe: pd.DataFrame,
    forecast_output: pd.DataFrame,
    location_summary: pd.DataFrame,
    feature_importance: pd.DataFrame,
    ml_rmse_improvement_pct: float,
    baseline_wins: bool,
) -> None:
    """Save model, forecasts, metrics, and governance metadata."""

    model_path = (
        MODELS_DIR
        / "weekly_revenue_forecast_best_ml_model.joblib"
    )

    metrics_path = (
        METRICS_DIR
        / "weekly_revenue_forecast_model_metrics.csv"
    )

    predictions_path = (
        ML_DATA_DIR
        / "weekly_revenue_forecast_predictions.csv"
    )

    location_summary_path = (
        METRICS_DIR
        / "weekly_revenue_forecast_location_summary.csv"
    )

    feature_importance_path = (
        METRICS_DIR
        / "weekly_revenue_forecast_feature_importance.csv"
    )

    metadata_path = (
        METRICS_DIR
        / "weekly_revenue_forecast_selection.txt"
    )

    joblib.dump(
        best_ml_model,
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

    location_summary.to_csv(
        location_summary_path,
        index=False,
    )

    feature_importance.to_csv(
        feature_importance_path,
        index=False,
    )

    metadata_text = (
        f"Selected forecasting method: "
        f"{selected_forecasting_method}\n"
        f"Best machine-learning model: "
        f"{best_ml_model_name}\n"
        "Selection metric: RMSE\n"
        "Validation method: Chronological weekly holdout\n"
        "Baseline: Previous-week revenue\n"
        f"Baseline selected: {baseline_wins}\n"
        f"Best ML RMSE improvement over baseline: "
        f"{ml_rmse_improvement_pct:.2f}%\n"
        "Leakage controls: Same-week wager, payout, "
        "sessions, transactions, and event values excluded "
        "from model features\n"
        "Dataset type: Synthetic weekly gaming revenue\n"
        "\nGovernance decision:\n"
    )

    if baseline_wins:
        metadata_text += (
            "The naive previous-week baseline outperformed "
            "all trained machine-learning models. The baseline "
            "was selected as the recommended forecasting method. "
            "The saved joblib file contains the best ML model "
            "for experimentation only.\n"
        )
    else:
        metadata_text += (
            "The best machine-learning model outperformed "
            "the naive baseline and was selected as the "
            "recommended forecasting method.\n"
        )

    metadata_path.write_text(
        metadata_text,
        encoding="utf-8",
    )

    print("\nSaved outputs:")
    print(
        f"Best ML model: {model_path}"
    )
    print(
        f"Metrics: {metrics_path}"
    )
    print(
        f"Predictions: {predictions_path}"
    )
    print(
        f"Location summary: "
        f"{location_summary_path}"
    )
    print(
        f"Feature importance: "
        f"{feature_importance_path}"
    )
    print(
        f"Selection metadata: "
        f"{metadata_path}"
    )


def main() -> None:
    """Run the complete weekly forecasting workflow."""

    create_directories()

    print(
        "Loading weekly revenue forecast dataset "
        "from SQL Server..."
    )

    dataframe = load_weekly_dataset()

    validate_dataset(
        dataframe
    )

    prepared_data = prepare_dataset(
        dataframe
    )

    dataset_path = (
        ML_DATA_DIR
        / "weekly_revenue_forecast_dataset.csv"
    )

    prepared_data.to_csv(
        dataset_path,
        index=False,
    )

    print(
        f"Raw rows: {len(dataframe):,}"
    )

    print(
        f"Usable rows: {len(prepared_data):,}"
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
        f"Training rows: {len(train_data):,}"
    )

    print(
        f"Testing rows: {len(test_data):,}"
    )

    (
        baseline_metrics,
        baseline_predictions,
    ) = create_naive_baseline(
        test_data
    )

    print(
        "\nNaive Previous-Week Baseline:"
    )

    print_metrics(
        baseline_metrics
    )

    metrics_records = [
        baseline_metrics
    ]

    model_results: dict[
        str,
        dict[str, Any],
    ] = {}

    for model_name, model in (
        build_models().items()
    ):
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
        "rmse"
    ).reset_index(drop=True)

    best_overall_row = (
        metrics_dataframe.iloc[0]
    )

    best_overall_name = str(
        best_overall_row["model"]
    )

    trainable_metrics = (
        metrics_dataframe.loc[
            metrics_dataframe[
                "model"
            ] != BASELINE_MODEL_NAME
        ]
        .sort_values("rmse")
        .reset_index(drop=True)
    )

    if trainable_metrics.empty:
        raise ValueError(
            "No machine-learning forecasting "
            "models were evaluated."
        )

    best_ml_row = (
        trainable_metrics.iloc[0]
    )

    best_ml_model_name = str(
        best_ml_row["model"]
    )

    best_ml_model = model_results[
        best_ml_model_name
    ]["model"]

    best_ml_predictions = model_results[
        best_ml_model_name
    ]["predictions"]

    baseline_rmse = float(
        baseline_metrics["rmse"]
    )

    best_ml_rmse = float(
        best_ml_row["rmse"]
    )

    if baseline_rmse == 0:
        ml_rmse_improvement_pct = float(
            "nan"
        )
    else:
        ml_rmse_improvement_pct = (
            (
                baseline_rmse
                - best_ml_rmse
            )
            / baseline_rmse
            * 100
        )

    baseline_wins = (
        best_overall_name
        == BASELINE_MODEL_NAME
    )

    if baseline_wins:
        selected_forecasting_method = (
            BASELINE_MODEL_NAME
        )

        selected_predictions = (
            baseline_predictions
        )
    else:
        selected_forecasting_method = (
            best_ml_model_name
        )

        selected_predictions = (
            best_ml_predictions
        )

    feature_importance = (
        extract_feature_importance(
            best_ml_model
        )
    )

    forecast_output = (
        create_forecast_output(
            test_data=test_data,
            selected_predictions=(
                selected_predictions
            ),
            best_ml_predictions=(
                best_ml_predictions
            ),
            baseline_predictions=(
                baseline_predictions
            ),
            selected_method=(
                selected_forecasting_method
            ),
        )
    )

    location_summary = (
        build_location_summary(
            forecast_output
        )
    )

    print("\nModel comparison:")

    print(
        metrics_dataframe.to_string(
            index=False
        )
    )

    print(
        "\nSelected forecasting method: "
        f"{selected_forecasting_method}"
    )

    print(
        "Best machine-learning model: "
        f"{best_ml_model_name}"
    )

    print(
        "Best ML RMSE improvement over baseline: "
        f"{ml_rmse_improvement_pct:.2f}%"
    )

    if baseline_wins:
        print(
            "Governance decision: the baseline "
            "outperformed the ML models and was selected."
        )
    else:
        print(
            "Governance decision: the ML model "
            "outperformed the baseline and was selected."
        )

    print(
        "\nTop 10 features from the best "
        "machine-learning model:"
    )

    print(
        feature_importance.head(
            10
        ).to_string(
            index=False
        )
    )

    print(
        "\nLocation-level forecast summary:"
    )

    print(
        location_summary[
            [
                "location_id",
                "location_name",
                "average_selected_absolute_error",
                "ml_beats_baseline_rate",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )

    save_outputs(
        selected_forecasting_method=(
            selected_forecasting_method
        ),
        best_ml_model_name=(
            best_ml_model_name
        ),
        best_ml_model=(
            best_ml_model
        ),
        metrics_dataframe=(
            metrics_dataframe
        ),
        forecast_output=(
            forecast_output
        ),
        location_summary=(
            location_summary
        ),
        feature_importance=(
            feature_importance
        ),
        ml_rmse_improvement_pct=(
            ml_rmse_improvement_pct
        ),
        baseline_wins=(
            baseline_wins
        ),
    )


if __name__ == "__main__":
    main()
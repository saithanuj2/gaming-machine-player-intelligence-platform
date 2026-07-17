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
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

MODELS_DIR = PROJECT_ROOT / "models"
ML_DATA_DIR = PROJECT_ROOT / "data" / "processed" / "ml"
METRICS_DIR = PROJECT_ROOT / "reports" / "model_metrics"

RANDOM_SEED = 42
TARGET_COLUMN = "churn_flag"


def create_directories() -> None:
    """Create output directories if they do not exist."""

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    ML_DATA_DIR.mkdir(parents=True, exist_ok=True)
    METRICS_DIR.mkdir(parents=True, exist_ok=True)


def build_connection_string() -> str:
    """Build the SQL Server connection string from environment variables."""

    load_dotenv(PROJECT_ROOT / ".env")

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


def load_churn_dataset() -> pd.DataFrame:
    """Load the churn dataset from the SQL Server predictive view."""

    query = """
        SELECT *
        FROM dbo.vw_ml_player_churn;
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
            "The churn dataset returned zero rows."
        )

    return dataframe


def validate_dataset(dataframe: pd.DataFrame) -> None:
    """Validate target, duplicate records, and class distribution."""

    required_columns = {
        "player_id",
        TARGET_COLUMN,
        "loyalty_tier",
        "age_band",
        "home_region",
        "total_historical_sessions",
        "days_since_last_session",
    }

    missing_columns = required_columns.difference(
        dataframe.columns
    )

    if missing_columns:
        raise ValueError(
            "Required columns are missing: "
            + ", ".join(sorted(missing_columns))
        )

    if dataframe["player_id"].duplicated().any():
        raise ValueError(
            "Duplicate player IDs were found."
        )

    if dataframe[TARGET_COLUMN].isna().any():
        raise ValueError(
            "Null values were found in churn_flag."
        )

    valid_target_values = {0, 1}

    if not set(
        dataframe[TARGET_COLUMN].unique()
    ).issubset(valid_target_values):
        raise ValueError(
            "churn_flag contains values other than 0 and 1."
        )

    class_counts = dataframe[
        TARGET_COLUMN
    ].value_counts()

    if len(class_counts) < 2:
        raise ValueError(
            "The target contains only one class."
        )


def prepare_features(
    dataframe: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series]:
    """Select defensible model features and remove leakage columns."""

    feature_columns = [
        "loyalty_tier",
        "age_band",
        "home_region",
        "marketing_opt_in",
        "registered_active_flag",
        "days_since_last_session",
        "observed_player_lifetime_days",
        "total_historical_sessions",
        "sessions_last_30_days",
        "sessions_last_90_days",
        "locations_visited",
        "machines_played",
        "total_session_minutes",
        "average_session_minutes",
        "total_rounds",
        "total_wager",
        "total_payout",
        "player_net_revenue",
        "average_wager_per_session",
        "wager_last_30_days",
        "wager_last_90_days",
        "revenue_last_30_days",
        "revenue_last_90_days",
        "sessions_per_observed_day",
    ]

    missing_features = [
        column
        for column in feature_columns
        if column not in dataframe.columns
    ]

    if missing_features:
        raise ValueError(
            "Model features are missing: "
            + ", ".join(missing_features)
        )

    features = dataframe[
        feature_columns
    ].copy()

    target = dataframe[
        TARGET_COLUMN
    ].astype(int)

    categorical_columns = [
        "loyalty_tier",
        "age_band",
        "home_region",
    ]

    numeric_columns = [
        column
        for column in feature_columns
        if column not in categorical_columns
    ]

    for column in numeric_columns:
        features[column] = pd.to_numeric(
            features[column],
            errors="coerce",
        )

    return features, target


def build_preprocessor(
    categorical_columns: list[str],
    numeric_columns: list[str],
) -> ColumnTransformer:
    """Create preprocessing steps for categorical and numerical features."""

    numeric_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(strategy="median"),
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
                SimpleImputer(strategy="most_frequent"),
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
                numeric_columns,
            ),
            (
                "categorical",
                categorical_pipeline,
                categorical_columns,
            ),
        ]
    )


def build_models(
    categorical_columns: list[str],
    numeric_columns: list[str],
) -> dict[str, Pipeline]:
    """Create baseline classification pipelines."""

    logistic_pipeline = Pipeline(
        steps=[
            (
                "preprocessor",
                build_preprocessor(
                    categorical_columns,
                    numeric_columns,
                ),
            ),
            (
                "model",
                LogisticRegression(
                    max_iter=2_000,
                    class_weight="balanced",
                    random_state=RANDOM_SEED,
                ),
            ),
        ]
    )

    random_forest_pipeline = Pipeline(
        steps=[
            (
                "preprocessor",
                build_preprocessor(
                    categorical_columns,
                    numeric_columns,
                ),
            ),
            (
                "model",
                RandomForestClassifier(
                    n_estimators=400,
                    max_depth=12,
                    min_samples_split=10,
                    min_samples_leaf=4,
                    class_weight="balanced",
                    n_jobs=-1,
                    random_state=RANDOM_SEED,
                ),
            ),
        ]
    )

    return {
        "Logistic Regression": logistic_pipeline,
        "Random Forest": random_forest_pipeline,
    }


def evaluate_model(
    model_name: str,
    model: Pipeline,
    x_train: pd.DataFrame,
    x_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series,
) -> tuple[dict[str, Any], np.ndarray, np.ndarray]:
    """Train and evaluate one classification model."""

    print(f"\nTraining {model_name}...")

    model.fit(
        x_train,
        y_train,
    )

    predictions = model.predict(
        x_test
    )

    probabilities = model.predict_proba(
        x_test
    )[:, 1]

    metrics = {
        "model": model_name,
        "accuracy": accuracy_score(
            y_test,
            predictions,
        ),
        "precision": precision_score(
            y_test,
            predictions,
            zero_division=0,
        ),
        "recall": recall_score(
            y_test,
            predictions,
            zero_division=0,
        ),
        "f1_score": f1_score(
            y_test,
            predictions,
            zero_division=0,
        ),
        "roc_auc": roc_auc_score(
            y_test,
            probabilities,
        ),
    }

    print(f"\n{model_name} metrics:")

    for metric_name, metric_value in metrics.items():
        if metric_name != "model":
            print(
                f"{metric_name}: "
                f"{metric_value:.4f}"
            )

    print("\nConfusion matrix:")
    print(
        confusion_matrix(
            y_test,
            predictions,
        )
    )

    print("\nClassification report:")
    print(
        classification_report(
            y_test,
            predictions,
            digits=4,
            zero_division=0,
        )
    )

    return metrics, predictions, probabilities


def save_results(
    metrics_dataframe: pd.DataFrame,
    test_results: pd.DataFrame,
    best_model_name: str,
    best_model: Pipeline,
) -> None:
    """Save model, evaluation metrics, and test predictions."""

    model_path = (
        MODELS_DIR
        / "player_churn_best_model.joblib"
    )

    metrics_path = (
        METRICS_DIR
        / "player_churn_model_metrics.csv"
    )

    predictions_path = (
        ML_DATA_DIR
        / "player_churn_test_predictions.csv"
    )

    metadata_path = (
        METRICS_DIR
        / "player_churn_best_model.txt"
    )

    joblib.dump(
        best_model,
        model_path,
    )

    metrics_dataframe.to_csv(
        metrics_path,
        index=False,
    )

    test_results.to_csv(
        predictions_path,
        index=False,
    )

    metadata_path.write_text(
        f"Best model: {best_model_name}\n"
        f"Selection metric: ROC-AUC\n",
        encoding="utf-8",
    )

    print("\nSaved outputs:")
    print(f"Model: {model_path}")
    print(f"Metrics: {metrics_path}")
    print(f"Predictions: {predictions_path}")
    print(f"Metadata: {metadata_path}")


def main() -> None:
    create_directories()

    print("Loading churn dataset from SQL Server...")

    dataframe = load_churn_dataset()

    validate_dataset(dataframe)

    dataset_path = (
        ML_DATA_DIR
        / "player_churn_dataset.csv"
    )

    dataframe.to_csv(
        dataset_path,
        index=False,
    )

    print(
        f"Rows loaded: {len(dataframe):,}"
    )
    print(
        f"Columns loaded: {len(dataframe.columns):,}"
    )

    print("\nTarget distribution:")
    print(
        dataframe[
            TARGET_COLUMN
        ].value_counts()
        .sort_index()
    )

    features, target = prepare_features(
        dataframe
    )

    categorical_columns = [
        "loyalty_tier",
        "age_band",
        "home_region",
    ]

    numeric_columns = [
        column
        for column in features.columns
        if column not in categorical_columns
    ]

    (
        x_train,
        x_test,
        y_train,
        y_test,
    ) = train_test_split(
        features,
        target,
        test_size=0.20,
        stratify=target,
        random_state=RANDOM_SEED,
    )

    print(
        f"\nTraining rows: {len(x_train):,}"
    )
    print(
        f"Testing rows: {len(x_test):,}"
    )

    models = build_models(
        categorical_columns,
        numeric_columns,
    )

    metrics_records = []
    model_results = {}

    for model_name, model in models.items():
        (
            metrics,
            predictions,
            probabilities,
        ) = evaluate_model(
            model_name=model_name,
            model=model,
            x_train=x_train,
            x_test=x_test,
            y_train=y_train,
            y_test=y_test,
        )

        metrics_records.append(
            metrics
        )

        model_results[model_name] = {
            "model": model,
            "predictions": predictions,
            "probabilities": probabilities,
        }

    metrics_dataframe = pd.DataFrame(
        metrics_records
    ).sort_values(
        "roc_auc",
        ascending=False,
    )

    best_model_name = metrics_dataframe.iloc[
        0
    ]["model"]

    best_result = model_results[
        best_model_name
    ]

    test_results = x_test.copy()
    test_results["actual_churn_flag"] = (
        y_test.to_numpy()
    )
    test_results["predicted_churn_flag"] = (
        best_result["predictions"]
    )
    test_results["churn_probability"] = (
        best_result["probabilities"]
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

    save_results(
        metrics_dataframe=metrics_dataframe,
        test_results=test_results,
        best_model_name=best_model_name,
        best_model=best_result["model"],
    )


if __name__ == "__main__":
    main()
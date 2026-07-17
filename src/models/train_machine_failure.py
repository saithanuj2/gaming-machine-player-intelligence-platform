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
from sklearn.model_selection import (
    StratifiedKFold,
    cross_validate,
    train_test_split,
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

TARGET_COLUMN = "failure_target_flag"
RANDOM_SEED = 42


CATEGORICAL_COLUMNS = [
    "manufacturer",
    "cabinet_type",
    "game_category",
    "software_version",
    "machine_status",
]


NUMERIC_COLUMNS = [
    "theoretical_hold_pct",
    "machine_age_days",
    "total_historical_events",
    "unplanned_event_count",
    "critical_event_count",
    "high_severity_event_count",
    "total_downtime_minutes",
    "average_downtime_minutes",
    "days_since_last_event",
    "events_last_30_days",
    "downtime_last_30_days",
    "events_last_90_days",
    "downtime_last_90_days",
    "historical_session_count",
    "historical_unique_players",
    "historical_total_wager",
    "historical_net_revenue",
    "revenue_last_30_days",
    "sessions_last_30_days",
]


FEATURE_COLUMNS = (
    CATEGORICAL_COLUMNS
    + NUMERIC_COLUMNS
)


def create_directories() -> None:
    """Create output directories."""

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
    """Create SQL Server connection string from .env."""

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


def load_machine_failure_dataset() -> pd.DataFrame:
    """Load machine-failure features from SQL Server."""

    query = """
        SELECT *
        FROM dbo.vw_ml_machine_failure;
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
            "Machine failure dataset returned zero rows."
        )

    return dataframe


def validate_dataset(
    dataframe: pd.DataFrame,
) -> None:
    """Validate identifiers, features, and target."""

    required_columns = {
        "machine_id",
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
        "machine_id"
    ].duplicated().any():
        raise ValueError(
            "Duplicate machine IDs were found."
        )

    if dataframe[
        TARGET_COLUMN
    ].isna().any():
        raise ValueError(
            "Null values were found in "
            "failure_target_flag."
        )

    target_values = set(
        dataframe[
            TARGET_COLUMN
        ].unique()
    )

    if not target_values.issubset(
        {0, 1}
    ):
        raise ValueError(
            "failure_target_flag must contain "
            "only 0 and 1."
        )

    if len(target_values) < 2:
        raise ValueError(
            "The target contains only one class."
        )


def prepare_features(
    dataframe: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series]:
    """Prepare model features and target."""

    features = dataframe[
        FEATURE_COLUMNS
    ].copy()

    for column in NUMERIC_COLUMNS:
        features[column] = pd.to_numeric(
            features[column],
            errors="coerce",
        )

    target = dataframe[
        TARGET_COLUMN
    ].astype(int)

    return features, target


def build_preprocessor() -> ColumnTransformer:
    """Create numeric and categorical preprocessing."""

    numeric_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="median"
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
                    strategy="most_frequent"
                ),
            ),
            (
                "encoder",
                OneHotEncoder(
                    handle_unknown="ignore"
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
    """Create machine-failure classification models."""

    logistic_regression = Pipeline(
        steps=[
            (
                "preprocessor",
                build_preprocessor(),
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

    random_forest = Pipeline(
        steps=[
            (
                "preprocessor",
                build_preprocessor(),
            ),
            (
                "model",
                RandomForestClassifier(
                    n_estimators=500,
                    max_depth=8,
                    min_samples_split=4,
                    min_samples_leaf=2,
                    max_features="sqrt",
                    class_weight="balanced",
                    n_jobs=-1,
                    random_state=RANDOM_SEED,
                ),
            ),
        ]
    )

    return {
        "Logistic Regression": logistic_regression,
        "Random Forest": random_forest,
    }


def run_cross_validation(
    model: Pipeline,
    features: pd.DataFrame,
    target: pd.Series,
) -> dict[str, float]:
    """Run stratified five-fold cross-validation."""

    cross_validator = StratifiedKFold(
        n_splits=5,
        shuffle=True,
        random_state=RANDOM_SEED,
    )

    scoring = {
        "accuracy": "accuracy",
        "precision": "precision",
        "recall": "recall",
        "f1": "f1",
        "roc_auc": "roc_auc",
    }

    results = cross_validate(
        estimator=model,
        X=features,
        y=target,
        cv=cross_validator,
        scoring=scoring,
        n_jobs=-1,
        return_train_score=False,
    )

    return {
        "cv_accuracy_mean": (
            results["test_accuracy"].mean()
        ),
        "cv_accuracy_std": (
            results["test_accuracy"].std()
        ),
        "cv_precision_mean": (
            results["test_precision"].mean()
        ),
        "cv_recall_mean": (
            results["test_recall"].mean()
        ),
        "cv_f1_mean": (
            results["test_f1"].mean()
        ),
        "cv_roc_auc_mean": (
            results["test_roc_auc"].mean()
        ),
        "cv_roc_auc_std": (
            results["test_roc_auc"].std()
        ),
    }


def evaluate_holdout(
    model_name: str,
    model: Pipeline,
    x_train: pd.DataFrame,
    x_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series,
) -> tuple[
    dict[str, Any],
    np.ndarray,
    np.ndarray,
]:
    """Train and evaluate one model on holdout data."""

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

    print(
        f"\n{model_name} holdout metrics:"
    )

    for metric_name, metric_value in (
        metrics.items()
    ):
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

    return (
        metrics,
        predictions,
        probabilities,
    )


def extract_feature_importance(
    model: Pipeline,
) -> pd.DataFrame:
    """Extract coefficients or feature importance."""

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

    if hasattr(estimator, "coef_"):
        importance_values = (
            estimator.coef_[0]
        )

        importance_column = (
            "coefficient"
        )

    elif hasattr(
        estimator,
        "feature_importances_",
    ):
        importance_values = (
            estimator
            .feature_importances_
        )

        importance_column = (
            "feature_importance"
        )

    else:
        raise ValueError(
            "The selected model does not expose "
            "feature importance."
        )

    importance_dataframe = pd.DataFrame(
        {
            "feature": cleaned_names,
            importance_column: (
                importance_values
            ),
        }
    )

    importance_dataframe[
        "absolute_importance"
    ] = np.abs(
        importance_values
    )

    return importance_dataframe.sort_values(
        "absolute_importance",
        ascending=False,
    ).reset_index(drop=True)


def generate_all_machine_predictions(
    model: Pipeline,
    dataframe: pd.DataFrame,
    features: pd.DataFrame,
) -> pd.DataFrame:
    """Score all machines and create risk labels."""

    probabilities = model.predict_proba(
        features
    )[:, 1]

    predictions = (
        probabilities >= 0.50
    ).astype(int)

    output_columns = [
        "machine_id",
        "location_id",
        "manufacturer",
        "cabinet_type",
        "game_title",
        "game_category",
        "software_version",
        "machine_status",
        "machine_age_days",
        "total_historical_events",
        "unplanned_event_count",
        "critical_event_count",
        "high_severity_event_count",
        "total_downtime_minutes",
        "average_downtime_minutes",
        "events_last_30_days",
        "downtime_last_30_days",
        "events_last_90_days",
        "downtime_last_90_days",
        "historical_net_revenue",
        "revenue_last_30_days",
        TARGET_COLUMN,
    ]

    output = dataframe[
        output_columns
    ].copy()

    output[
        "failure_probability"
    ] = probabilities

    output[
        "predicted_failure_flag"
    ] = predictions

    output[
        "failure_risk_level"
    ] = pd.cut(
        output[
            "failure_probability"
        ],
        bins=[
            -np.inf,
            0.30,
            0.60,
            0.80,
            np.inf,
        ],
        labels=[
            "Low",
            "Medium",
            "High",
            "Critical",
        ],
    )

    output[
        "recommended_action"
    ] = np.select(
        [
            output[
                "failure_probability"
            ] >= 0.80,

            output[
                "failure_probability"
            ] >= 0.60,

            output[
                "failure_probability"
            ] >= 0.30,
        ],
        [
            "Immediate maintenance inspection",
            "Schedule preventive maintenance",
            "Increase monitoring frequency",
        ],
        default="Routine monitoring",
    )

    output[
        "revenue_at_risk"
    ] = (
        output[
            "historical_net_revenue"
        ].clip(lower=0)
        * output[
            "failure_probability"
        ]
    ).round(2)

    return output.sort_values(
        [
            "failure_probability",
            "revenue_at_risk",
        ],
        ascending=False,
    ).reset_index(drop=True)


def save_outputs(
    best_model_name: str,
    best_model: Pipeline,
    metrics_dataframe: pd.DataFrame,
    holdout_predictions: pd.DataFrame,
    all_machine_predictions: pd.DataFrame,
    feature_importance: pd.DataFrame,
) -> None:
    """Save model and reporting artifacts."""

    model_path = (
        MODELS_DIR
        / "machine_failure_best_model.joblib"
    )

    metrics_path = (
        METRICS_DIR
        / "machine_failure_model_metrics.csv"
    )

    holdout_path = (
        ML_DATA_DIR
        / "machine_failure_test_predictions.csv"
    )

    all_predictions_path = (
        ML_DATA_DIR
        / "machine_failure_all_predictions.csv"
    )

    feature_importance_path = (
        METRICS_DIR
        / "machine_failure_feature_importance.csv"
    )

    metadata_path = (
        METRICS_DIR
        / "machine_failure_best_model.txt"
    )

    joblib.dump(
        best_model,
        model_path,
    )

    metrics_dataframe.to_csv(
        metrics_path,
        index=False,
    )

    holdout_predictions.to_csv(
        holdout_path,
        index=False,
    )

    all_machine_predictions.to_csv(
        all_predictions_path,
        index=False,
    )

    feature_importance.to_csv(
        feature_importance_path,
        index=False,
    )

    metadata_path.write_text(
        (
            f"Best model: {best_model_name}\n"
            "Selection metric: "
            "Cross-validation ROC-AUC\n"
            "Dataset type: Synthetic machine "
            "health dataset\n"
        ),
        encoding="utf-8",
    )

    print("\nSaved outputs:")
    print(f"Model: {model_path}")
    print(f"Metrics: {metrics_path}")
    print(
        f"Holdout predictions: {holdout_path}"
    )
    print(
        "All machine predictions: "
        f"{all_predictions_path}"
    )
    print(
        "Feature importance: "
        f"{feature_importance_path}"
    )
    print(f"Metadata: {metadata_path}")


def main() -> None:
    create_directories()

    print(
        "Loading machine failure dataset "
        "from SQL Server..."
    )

    dataframe = (
        load_machine_failure_dataset()
    )

    validate_dataset(
        dataframe
    )

    dataset_path = (
        ML_DATA_DIR
        / "machine_failure_dataset.csv"
    )

    dataframe.to_csv(
        dataset_path,
        index=False,
    )

    print(
        f"Rows loaded: {len(dataframe):,}"
    )

    print(
        f"Columns loaded: "
        f"{len(dataframe.columns):,}"
    )

    print("\nTarget distribution:")
    print(
        dataframe[
            TARGET_COLUMN
        ]
        .value_counts()
        .sort_index()
    )

    features, target = prepare_features(
        dataframe
    )

    (
        x_train,
        x_test,
        y_train,
        y_test,
    ) = train_test_split(
        features,
        target,
        test_size=0.25,
        stratify=target,
        random_state=RANDOM_SEED,
    )

    print(
        f"\nTraining rows: "
        f"{len(x_train):,}"
    )

    print(
        f"Testing rows: "
        f"{len(x_test):,}"
    )

    models = build_models()

    metrics_records = []
    model_results = {}

    for model_name, model in (
        models.items()
    ):
        cross_validation_metrics = (
            run_cross_validation(
                model=model,
                features=features,
                target=target,
            )
        )

        (
            holdout_metrics,
            predictions,
            probabilities,
        ) = evaluate_holdout(
            model_name=model_name,
            model=model,
            x_train=x_train,
            x_test=x_test,
            y_train=y_train,
            y_test=y_test,
        )

        combined_metrics = {
            **holdout_metrics,
            **cross_validation_metrics,
        }

        metrics_records.append(
            combined_metrics
        )

        model_results[model_name] = {
            "model": model,
            "predictions": predictions,
            "probabilities": probabilities,
        }

    metrics_dataframe = pd.DataFrame(
        metrics_records
    ).sort_values(
        [
            "cv_roc_auc_mean",
            "cv_f1_mean",
        ],
        ascending=False,
    )

    best_model_name = (
        metrics_dataframe.iloc[0][
            "model"
        ]
    )

    best_model = model_results[
        best_model_name
    ]["model"]

    best_model.fit(
        features,
        target,
    )

    test_indexes = x_test.index

    holdout_predictions = dataframe.loc[
        test_indexes,
        [
            "machine_id",
            "manufacturer",
            "game_category",
            "software_version",
            TARGET_COLUMN,
        ],
    ].copy()

    holdout_predictions[
        "predicted_failure_flag"
    ] = model_results[
        best_model_name
    ]["predictions"]

    holdout_predictions[
        "failure_probability"
    ] = model_results[
        best_model_name
    ]["probabilities"]

    holdout_predictions = (
        holdout_predictions.sort_values(
            "failure_probability",
            ascending=False,
        )
    )

    all_machine_predictions = (
        generate_all_machine_predictions(
            model=best_model,
            dataframe=dataframe,
            features=features,
        )
    )

    feature_importance = (
        extract_feature_importance(
            best_model
        )
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
        "\nTop 10 influential features:"
    )

    print(
        feature_importance.head(
            10
        ).to_string(
            index=False
        )
    )

    print(
        "\nTop 10 machines by predicted "
        "failure risk:"
    )

    print(
        all_machine_predictions[
            [
                "machine_id",
                "manufacturer",
                "software_version",
                "failure_probability",
                "failure_risk_level",
                "recommended_action",
                "revenue_at_risk",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )

    save_outputs(
        best_model_name=best_model_name,
        best_model=best_model,
        metrics_dataframe=(
            metrics_dataframe
        ),
        holdout_predictions=(
            holdout_predictions
        ),
        all_machine_predictions=(
            all_machine_predictions
        ),
        feature_importance=(
            feature_importance
        ),
    )


if __name__ == "__main__":
    main()
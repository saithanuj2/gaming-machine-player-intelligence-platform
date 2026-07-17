import os
import sys
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import pyodbc
from dotenv import load_dotenv
from sklearn.base import clone
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_validate


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


MODEL_PATH = (
    PROJECT_ROOT
    / "models"
    / "player_churn_best_model.joblib"
)

VALIDATION_DIR = (
    PROJECT_ROOT
    / "reports"
    / "model_validation"
)

ML_DATA_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "ml"
)

TARGET_COLUMN = "churn_flag"
RANDOM_SEED = 42

CATEGORICAL_COLUMNS = [
    "loyalty_tier",
    "age_band",
    "home_region",
]

FEATURE_COLUMNS = [
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


def create_output_directories() -> None:
    """Create validation output directories."""

    VALIDATION_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    ML_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


def build_connection_string() -> str:
    """Build SQL Server connection string from environment variables."""

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
            "Missing environment variables: "
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


def load_dataset() -> pd.DataFrame:
    """Load the full churn dataset from SQL Server."""

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
            "The churn predictive view returned no rows."
        )

    return dataframe


def validate_dataset(
    dataframe: pd.DataFrame,
) -> None:
    """Validate required columns and target quality."""

    required_columns = {
        "player_id",
        TARGET_COLUMN,
        *FEATURE_COLUMNS,
    }

    missing_columns = (
        required_columns
        - set(dataframe.columns)
    )

    if missing_columns:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(
                sorted(missing_columns)
            )
        )

    if dataframe[
        "player_id"
    ].duplicated().any():
        raise ValueError(
            "Duplicate player IDs were found."
        )

    if dataframe[
        TARGET_COLUMN
    ].isna().any():
        raise ValueError(
            "Null values were found in churn_flag."
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
            "churn_flag must contain only 0 and 1."
        )


def prepare_features(
    dataframe: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series]:
    """Create the model feature matrix and target vector."""

    features = dataframe[
        FEATURE_COLUMNS
    ].copy()

    numeric_columns = [
        column
        for column in FEATURE_COLUMNS
        if column not in CATEGORICAL_COLUMNS
    ]

    for column in numeric_columns:
        features[column] = pd.to_numeric(
            features[column],
            errors="coerce",
        )

    target = dataframe[
        TARGET_COLUMN
    ].astype(int)

    return features, target


def run_cross_validation(
    model: Any,
    features: pd.DataFrame,
    target: pd.Series,
) -> pd.DataFrame:
    """Run five-fold stratified cross-validation."""

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
        estimator=clone(model),
        X=features,
        y=target,
        cv=cross_validator,
        scoring=scoring,
        return_train_score=True,
        n_jobs=-1,
    )

    fold_records = []

    for fold_number in range(5):
        fold_records.append(
            {
                "fold": fold_number + 1,
                "train_accuracy": (
                    results[
                        "train_accuracy"
                    ][fold_number]
                ),
                "validation_accuracy": (
                    results[
                        "test_accuracy"
                    ][fold_number]
                ),
                "validation_precision": (
                    results[
                        "test_precision"
                    ][fold_number]
                ),
                "validation_recall": (
                    results[
                        "test_recall"
                    ][fold_number]
                ),
                "validation_f1": (
                    results[
                        "test_f1"
                    ][fold_number]
                ),
                "validation_roc_auc": (
                    results[
                        "test_roc_auc"
                    ][fold_number]
                ),
            }
        )

    return pd.DataFrame(
        fold_records
    )


def build_cross_validation_summary(
    cross_validation_results: pd.DataFrame,
) -> pd.DataFrame:
    """Summarize mean and standard deviation across folds."""

    metrics = [
        "train_accuracy",
        "validation_accuracy",
        "validation_precision",
        "validation_recall",
        "validation_f1",
        "validation_roc_auc",
    ]

    summary_records = []

    for metric in metrics:
        summary_records.append(
            {
                "metric": metric,
                "mean": cross_validation_results[
                    metric
                ].mean(),
                "standard_deviation": (
                    cross_validation_results[
                        metric
                    ].std()
                ),
                "minimum": cross_validation_results[
                    metric
                ].min(),
                "maximum": cross_validation_results[
                    metric
                ].max(),
            }
        )

    return pd.DataFrame(
        summary_records
    )


def generate_full_predictions(
    model: Any,
    features: pd.DataFrame,
    target: pd.Series,
) -> tuple[np.ndarray, np.ndarray]:
    """Fit the model on all rows and generate predictions."""

    model.fit(
        features,
        target,
    )

    probabilities = model.predict_proba(
        features
    )[:, 1]

    predictions = (
        probabilities >= 0.50
    ).astype(int)

    return predictions, probabilities


def analyze_thresholds(
    target: pd.Series,
    probabilities: np.ndarray,
) -> pd.DataFrame:
    """Evaluate classification metrics across probability thresholds."""

    thresholds = np.arange(
        0.20,
        0.81,
        0.05,
    )

    records = []

    for threshold in thresholds:
        predictions = (
            probabilities >= threshold
        ).astype(int)

        records.append(
            {
                "threshold": round(
                    float(threshold),
                    2,
                ),
                "accuracy": accuracy_score(
                    target,
                    predictions,
                ),
                "precision": precision_score(
                    target,
                    predictions,
                    zero_division=0,
                ),
                "recall": recall_score(
                    target,
                    predictions,
                    zero_division=0,
                ),
                "f1_score": f1_score(
                    target,
                    predictions,
                    zero_division=0,
                ),
            }
        )

    return pd.DataFrame(
        records
    )


def select_best_threshold(
    threshold_results: pd.DataFrame,
) -> float:
    """Select the threshold producing the highest F1 score."""

    best_row = threshold_results.sort_values(
        [
            "f1_score",
            "recall",
            "precision",
        ],
        ascending=False,
    ).iloc[0]

    return float(
        best_row["threshold"]
    )


def extract_feature_importance(
    model: Any,
) -> pd.DataFrame:
    """
    Extract feature coefficients or feature importances from
    the trained pipeline.
    """

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

    if hasattr(
        estimator,
        "coef_",
    ):
        values = estimator.coef_[0]
        importance_type = "coefficient"

    elif hasattr(
        estimator,
        "feature_importances_",
    ):
        values = (
            estimator
            .feature_importances_
        )
        importance_type = "feature_importance"

    else:
        raise ValueError(
            "The saved model does not expose "
            "coefficients or feature importances."
        )

    importance_dataframe = pd.DataFrame(
        {
            "feature": cleaned_feature_names,
            importance_type: values,
        }
    )

    importance_dataframe[
        "absolute_importance"
    ] = np.abs(values)

    importance_dataframe[
        "effect_direction"
    ] = np.where(
        values > 0,
        "Higher churn risk",
        np.where(
            values < 0,
            "Lower churn risk",
            "Neutral",
        ),
    )

    return importance_dataframe.sort_values(
        "absolute_importance",
        ascending=False,
    ).reset_index(drop=True)


def create_prediction_dataset(
    dataframe: pd.DataFrame,
    probabilities: np.ndarray,
    threshold: float,
) -> pd.DataFrame:
    """Create an actionable prediction dataset for all players."""

    prediction_dataframe = dataframe[
        [
            "player_id",
            "loyalty_tier",
            "age_band",
            "home_region",
            "marketing_opt_in",
            "days_since_last_session",
            "total_historical_sessions",
            "sessions_last_30_days",
            "sessions_last_90_days",
            "total_wager",
            "player_net_revenue",
            TARGET_COLUMN,
        ]
    ].copy()

    prediction_dataframe[
        "churn_probability"
    ] = probabilities

    prediction_dataframe[
        "predicted_churn_flag"
    ] = (
        prediction_dataframe[
            "churn_probability"
        ] >= threshold
    ).astype(int)

    prediction_dataframe[
        "risk_level"
    ] = pd.cut(
        prediction_dataframe[
            "churn_probability"
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

    prediction_dataframe[
        "recommended_action"
    ] = np.select(
        [
            prediction_dataframe[
                "churn_probability"
            ] >= 0.80,

            prediction_dataframe[
                "churn_probability"
            ] >= 0.60,

            prediction_dataframe[
                "churn_probability"
            ] >= 0.30,
        ],
        [
            "Immediate retention outreach",
            "Targeted loyalty offer",
            "Monitor engagement",
        ],
        default="No immediate action",
    )

    return prediction_dataframe.sort_values(
        "churn_probability",
        ascending=False,
    ).reset_index(drop=True)


def save_confusion_matrix(
    target: pd.Series,
    predictions: np.ndarray,
) -> pd.DataFrame:
    """Create a labeled confusion-matrix table."""

    matrix = confusion_matrix(
        target,
        predictions,
    )

    return pd.DataFrame(
        matrix,
        index=[
            "Actual No Churn",
            "Actual Churn",
        ],
        columns=[
            "Predicted No Churn",
            "Predicted Churn",
        ],
    )


def write_executive_summary(
    cross_validation_summary: pd.DataFrame,
    threshold_results: pd.DataFrame,
    best_threshold: float,
    target: pd.Series,
    probabilities: np.ndarray,
    predictions: np.ndarray,
    high_risk_players: pd.DataFrame,
    feature_importance: pd.DataFrame,
) -> None:
    """Write an executive-friendly model validation summary."""

    roc_auc = roc_auc_score(
        target,
        probabilities,
    )

    accuracy = accuracy_score(
        target,
        predictions,
    )

    precision = precision_score(
        target,
        predictions,
        zero_division=0,
    )

    recall = recall_score(
        target,
        predictions,
        zero_division=0,
    )

    f1 = f1_score(
        target,
        predictions,
        zero_division=0,
    )

    validation_auc_row = (
        cross_validation_summary.loc[
            cross_validation_summary[
                "metric"
            ] == "validation_roc_auc"
        ].iloc[0]
    )

    validation_f1_row = (
        cross_validation_summary.loc[
            cross_validation_summary[
                "metric"
            ] == "validation_f1"
        ].iloc[0]
    )

    best_threshold_row = (
        threshold_results.loc[
            threshold_results[
                "threshold"
            ] == best_threshold
        ].iloc[0]
    )

    top_features = feature_importance.head(
        5
    )

    feature_lines = "\n".join(
        f"- {row.feature}: "
        f"{row.effect_direction}"
        for row in top_features.itertuples()
    )

    summary = f"""
PLAYER CHURN MODEL VALIDATION SUMMARY
=====================================

Model
-----
Saved best classification pipeline

Dataset
-------
Total players: {len(target):,}
Churn players: {int(target.sum()):,}
Non-churn players: {int((target == 0).sum()):,}
Data type: Synthetic behavioral gaming dataset

Five-Fold Cross-Validation
--------------------------
Mean ROC-AUC: {validation_auc_row['mean']:.4f}
ROC-AUC standard deviation: {validation_auc_row['standard_deviation']:.4f}
Mean F1 score: {validation_f1_row['mean']:.4f}
F1 standard deviation: {validation_f1_row['standard_deviation']:.4f}

Full-Dataset Evaluation
-----------------------
Accuracy: {accuracy:.4f}
Precision: {precision:.4f}
Recall: {recall:.4f}
F1 score: {f1:.4f}
ROC-AUC: {roc_auc:.4f}

Threshold Analysis
------------------
Selected threshold: {best_threshold:.2f}
Threshold accuracy: {best_threshold_row['accuracy']:.4f}
Threshold precision: {best_threshold_row['precision']:.4f}
Threshold recall: {best_threshold_row['recall']:.4f}
Threshold F1 score: {best_threshold_row['f1_score']:.4f}

High-Risk Population
--------------------
Players with probability >= 0.80: {len(high_risk_players):,}

Most Influential Features
-------------------------
{feature_lines}

Business Recommendation
-----------------------
Prioritize immediate retention outreach for players classified
as Critical risk. Use targeted loyalty offers for High-risk
players and monitor Medium-risk players for further engagement
decline.

Interpretation Note
-------------------
Performance was measured on a synthetic behavioral dataset.
The generator intentionally links historical engagement,
recency, loyalty and wagering behavior with future churn.
Results should not be presented as real-world casino model
performance without external validation.
""".strip()

    summary_path = (
        VALIDATION_DIR
        / "player_churn_executive_summary.txt"
    )

    summary_path.write_text(
        summary,
        encoding="utf-8",
    )


def main() -> None:
    create_output_directories()

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Saved model not found: {MODEL_PATH}"
        )

    print(
        "Loading player churn dataset..."
    )

    dataframe = load_dataset()

    validate_dataset(
        dataframe
    )

    features, target = prepare_features(
        dataframe
    )

    print(
        f"Rows loaded: {len(dataframe):,}"
    )

    print(
        "\nLoading saved best model..."
    )

    model = joblib.load(
        MODEL_PATH
    )

    print(
        "\nRunning five-fold cross-validation..."
    )

    cross_validation_results = (
        run_cross_validation(
            model=model,
            features=features,
            target=target,
        )
    )

    cross_validation_summary = (
        build_cross_validation_summary(
            cross_validation_results
        )
    )

    print(
        "\nTraining model on the full dataset..."
    )

    predictions_at_default, probabilities = (
        generate_full_predictions(
            model=model,
            features=features,
            target=target,
        )
    )

    print(
        "\nEvaluating probability thresholds..."
    )

    threshold_results = analyze_thresholds(
        target=target,
        probabilities=probabilities,
    )

    best_threshold = select_best_threshold(
        threshold_results
    )

    optimized_predictions = (
        probabilities >= best_threshold
    ).astype(int)

    print(
        "\nExtracting feature importance..."
    )

    feature_importance = (
        extract_feature_importance(
            model
        )
    )

    prediction_dataset = (
        create_prediction_dataset(
            dataframe=dataframe,
            probabilities=probabilities,
            threshold=best_threshold,
        )
    )

    high_risk_players = (
        prediction_dataset.loc[
            prediction_dataset[
                "churn_probability"
            ] >= 0.80
        ].copy()
    )

    default_confusion_matrix = (
        save_confusion_matrix(
            target=target,
            predictions=predictions_at_default,
        )
    )

    optimized_confusion_matrix = (
        save_confusion_matrix(
            target=target,
            predictions=optimized_predictions,
        )
    )

    report = classification_report(
        target,
        optimized_predictions,
        digits=4,
        zero_division=0,
    )

    cross_validation_results.to_csv(
        VALIDATION_DIR
        / "player_churn_cross_validation_folds.csv",
        index=False,
    )

    cross_validation_summary.to_csv(
        VALIDATION_DIR
        / "player_churn_cross_validation_summary.csv",
        index=False,
    )

    threshold_results.to_csv(
        VALIDATION_DIR
        / "player_churn_threshold_analysis.csv",
        index=False,
    )

    feature_importance.to_csv(
        VALIDATION_DIR
        / "player_churn_feature_importance.csv",
        index=False,
    )

    default_confusion_matrix.to_csv(
        VALIDATION_DIR
        / "player_churn_confusion_matrix_default.csv",
    )

    optimized_confusion_matrix.to_csv(
        VALIDATION_DIR
        / "player_churn_confusion_matrix_optimized.csv",
    )

    prediction_dataset.to_csv(
        ML_DATA_DIR
        / "player_churn_all_predictions.csv",
        index=False,
    )

    high_risk_players.to_csv(
        VALIDATION_DIR
        / "player_churn_high_risk_players.csv",
        index=False,
    )

    (
        VALIDATION_DIR
        / "player_churn_classification_report.txt"
    ).write_text(
        report,
        encoding="utf-8",
    )

    write_executive_summary(
        cross_validation_summary=(
            cross_validation_summary
        ),
        threshold_results=threshold_results,
        best_threshold=best_threshold,
        target=target,
        probabilities=probabilities,
        predictions=optimized_predictions,
        high_risk_players=high_risk_players,
        feature_importance=feature_importance,
    )

    validated_model_path = (
        PROJECT_ROOT
        / "models"
        / "player_churn_validated_model.joblib"
    )

    joblib.dump(
        model,
        validated_model_path,
    )

    print("\nValidation completed successfully.")

    print(
        f"Best threshold: {best_threshold:.2f}"
    )

    print(
        "Cross-validation summary:"
    )

    print(
        cross_validation_summary.to_string(
            index=False
        )
    )

    print(
        "\nTop ten influential features:"
    )

    print(
        feature_importance.head(
            10
        ).to_string(
            index=False
        )
    )

    print(
        "\nHigh-risk players:",
        f"{len(high_risk_players):,}",
    )

    print(
        "\nSaved validation reports to:"
    )

    print(
        VALIDATION_DIR
    )

    print(
        "Validated model:",
        validated_model_path,
    )


if __name__ == "__main__":
    main()
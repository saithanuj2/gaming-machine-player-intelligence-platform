import sys
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
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

MODEL_PATH = (
    PROJECT_ROOT
    / "models"
    / "machine_failure_best_model.joblib"
)

DATASET_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "ml"
    / "machine_failure_dataset.csv"
)

PREDICTIONS_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "ml"
    / "machine_failure_all_predictions.csv"
)

VALIDATION_DIR = (
    PROJECT_ROOT
    / "reports"
    / "machine_failure_validation"
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

FEATURE_COLUMNS = CATEGORICAL_COLUMNS + NUMERIC_COLUMNS


def create_output_directory() -> None:
    """Create validation output directory."""

    VALIDATION_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


def load_inputs() -> tuple[Any, pd.DataFrame, pd.DataFrame]:
    """Load the trained model, ML dataset, and saved predictions."""

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found: {MODEL_PATH}"
        )

    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATASET_PATH}"
        )

    if not PREDICTIONS_PATH.exists():
        raise FileNotFoundError(
            f"Predictions not found: {PREDICTIONS_PATH}"
        )

    model = joblib.load(
        MODEL_PATH
    )

    dataset = pd.read_csv(
        DATASET_PATH
    )

    predictions = pd.read_csv(
        PREDICTIONS_PATH
    )

    return model, dataset, predictions


def validate_dataset(
    dataframe: pd.DataFrame,
) -> None:
    """Validate identifiers, required columns, and target."""

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
            "Missing required columns: "
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
            "Null values were found in the target."
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
            "failure_target_flag must contain only 0 and 1."
        )

    if len(target_values) < 2:
        raise ValueError(
            "The target contains only one class."
        )


def prepare_features(
    dataframe: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series]:
    """Create feature matrix and target vector."""

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


def run_cross_validation(
    model: Any,
    features: pd.DataFrame,
    target: pd.Series,
) -> pd.DataFrame:
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
        estimator=clone(model),
        X=features,
        y=target,
        cv=cross_validator,
        scoring=scoring,
        return_train_score=True,
        n_jobs=-1,
    )

    records = []

    for fold_index in range(5):
        records.append(
            {
                "fold": fold_index + 1,
                "train_accuracy": results[
                    "train_accuracy"
                ][fold_index],
                "validation_accuracy": results[
                    "test_accuracy"
                ][fold_index],
                "validation_precision": results[
                    "test_precision"
                ][fold_index],
                "validation_recall": results[
                    "test_recall"
                ][fold_index],
                "validation_f1": results[
                    "test_f1"
                ][fold_index],
                "validation_roc_auc": results[
                    "test_roc_auc"
                ][fold_index],
            }
        )

    return pd.DataFrame(
        records
    )


def summarize_cross_validation(
    fold_results: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate summary statistics across folds."""

    metric_columns = [
        "train_accuracy",
        "validation_accuracy",
        "validation_precision",
        "validation_recall",
        "validation_f1",
        "validation_roc_auc",
    ]

    records = []

    for metric in metric_columns:
        records.append(
            {
                "metric": metric,
                "mean": fold_results[
                    metric
                ].mean(),
                "standard_deviation": fold_results[
                    metric
                ].std(),
                "minimum": fold_results[
                    metric
                ].min(),
                "maximum": fold_results[
                    metric
                ].max(),
            }
        )

    return pd.DataFrame(
        records
    )


def fit_full_model(
    model: Any,
    features: pd.DataFrame,
    target: pd.Series,
) -> tuple[Any, np.ndarray]:
    """Fit the model on all records and return probabilities."""

    model.fit(
        features,
        target,
    )

    probabilities = model.predict_proba(
        features
    )[:, 1]

    return model, probabilities


def analyze_thresholds(
    target: pd.Series,
    probabilities: np.ndarray,
) -> pd.DataFrame:
    """Evaluate model performance across probability thresholds."""

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
    """Select threshold using F1, then recall, then precision."""

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
    """Extract feature importance from the fitted pipeline."""

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

    if hasattr(
        estimator,
        "feature_importances_",
    ):
        importance_values = (
            estimator.feature_importances_
        )

        importance_column = (
            "feature_importance"
        )

    elif hasattr(
        estimator,
        "coef_",
    ):
        importance_values = (
            estimator.coef_[0]
        )

        importance_column = "coefficient"

    else:
        raise ValueError(
            "The model does not expose feature importance."
        )

    output = pd.DataFrame(
        {
            "feature": cleaned_names,
            importance_column: importance_values,
        }
    )

    output[
        "absolute_importance"
    ] = np.abs(
        importance_values
    )

    return output.sort_values(
        "absolute_importance",
        ascending=False,
    ).reset_index(drop=True)


def build_confusion_matrix_table(
    target: pd.Series,
    predictions: np.ndarray,
) -> pd.DataFrame:
    """Create a labeled confusion matrix table."""

    matrix = confusion_matrix(
        target,
        predictions,
    )

    return pd.DataFrame(
        matrix,
        index=[
            "Actual Healthy",
            "Actual Failure",
        ],
        columns=[
            "Predicted Healthy",
            "Predicted Failure",
        ],
    )


def create_maintenance_priority(
    predictions: pd.DataFrame,
) -> pd.DataFrame:
    """Create maintenance ranking using risk and revenue exposure."""

    required_columns = {
        "machine_id",
        "manufacturer",
        "software_version",
        "failure_probability",
        "failure_risk_level",
        "recommended_action",
        "revenue_at_risk",
        "total_downtime_minutes",
        "critical_event_count",
        "unplanned_event_count",
    }

    missing_columns = required_columns.difference(
        predictions.columns
    )

    if missing_columns:
        raise ValueError(
            "Missing prediction columns: "
            + ", ".join(
                sorted(missing_columns)
            )
        )

    output = predictions.copy()

    output[
        "maintenance_priority_score"
    ] = (
        output[
            "failure_probability"
        ]
        * 100
        + output[
            "revenue_at_risk"
        ].fillna(0)
        / 100
        + output[
            "total_downtime_minutes"
        ].fillna(0)
        / 100
        + output[
            "critical_event_count"
        ].fillna(0)
        * 2
    ).round(2)

    output[
        "maintenance_priority_rank"
    ] = output[
        "maintenance_priority_score"
    ].rank(
        method="dense",
        ascending=False,
    ).astype(int)

    return output.sort_values(
        [
            "maintenance_priority_score",
            "failure_probability",
        ],
        ascending=False,
    ).reset_index(drop=True)


def create_risk_summary(
    prioritized_machines: pd.DataFrame,
) -> pd.DataFrame:
    """Create Power BI-ready summary by failure risk level."""

    summary = (
        prioritized_machines
        .groupby(
            "failure_risk_level",
            observed=False,
        )
        .agg(
            machine_count=(
                "machine_id",
                "count",
            ),
            average_failure_probability=(
                "failure_probability",
                "mean",
            ),
            total_revenue_at_risk=(
                "revenue_at_risk",
                "sum",
            ),
            total_downtime_minutes=(
                "total_downtime_minutes",
                "sum",
            ),
            total_critical_events=(
                "critical_event_count",
                "sum",
            ),
            total_unplanned_events=(
                "unplanned_event_count",
                "sum",
            ),
        )
        .reset_index()
    )

    return summary.sort_values(
        "total_revenue_at_risk",
        ascending=False,
    )


def write_executive_summary(
    cross_validation_summary: pd.DataFrame,
    threshold_results: pd.DataFrame,
    best_threshold: float,
    target: pd.Series,
    probabilities: np.ndarray,
    optimized_predictions: np.ndarray,
    feature_importance: pd.DataFrame,
    prioritized_machines: pd.DataFrame,
) -> None:
    """Write an executive maintenance summary."""

    accuracy = accuracy_score(
        target,
        optimized_predictions,
    )

    precision = precision_score(
        target,
        optimized_predictions,
        zero_division=0,
    )

    recall = recall_score(
        target,
        optimized_predictions,
        zero_division=0,
    )

    f1 = f1_score(
        target,
        optimized_predictions,
        zero_division=0,
    )

    roc_auc = roc_auc_score(
        target,
        probabilities,
    )

    cv_auc = cross_validation_summary.loc[
        cross_validation_summary[
            "metric"
        ] == "validation_roc_auc"
    ].iloc[0]

    cv_f1 = cross_validation_summary.loc[
        cross_validation_summary[
            "metric"
        ] == "validation_f1"
    ].iloc[0]

    threshold_row = threshold_results.loc[
        threshold_results[
            "threshold"
        ] == best_threshold
    ].iloc[0]

    top_features = feature_importance.head(
        5
    )

    feature_lines = "\n".join(
        f"- {row.feature}"
        for row in top_features.itertuples()
    )

    critical_machine_count = int(
        (
            prioritized_machines[
                "failure_risk_level"
            ] == "Critical"
        ).sum()
    )

    high_machine_count = int(
        (
            prioritized_machines[
                "failure_risk_level"
            ] == "High"
        ).sum()
    )

    summary = f"""
MACHINE FAILURE MODEL VALIDATION SUMMARY
========================================

Dataset
-------
Total machines: {len(target):,}
Failure machines: {int(target.sum()):,}
Healthy machines: {int((target == 0).sum()):,}
Data type: Synthetic machine-health dataset

Five-Fold Cross-Validation
--------------------------
Mean ROC-AUC: {cv_auc['mean']:.4f}
ROC-AUC standard deviation: {cv_auc['standard_deviation']:.4f}
Mean F1 score: {cv_f1['mean']:.4f}
F1 standard deviation: {cv_f1['standard_deviation']:.4f}

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
Threshold accuracy: {threshold_row['accuracy']:.4f}
Threshold precision: {threshold_row['precision']:.4f}
Threshold recall: {threshold_row['recall']:.4f}
Threshold F1 score: {threshold_row['f1_score']:.4f}

Maintenance Risk Population
---------------------------
Critical-risk machines: {critical_machine_count:,}
High-risk machines: {high_machine_count:,}

Most Influential Features
-------------------------
{feature_lines}

Business Recommendation
-----------------------
Prioritize immediate inspection for Critical-risk machines.
Schedule preventive maintenance for High-risk machines with
high revenue exposure. Increase monitoring for Medium-risk
machines showing rising downtime and repeated unplanned events.

Interpretation Note
-------------------
Results are based on synthetic machine-health data. Model
performance and maintenance recommendations require external
validation before production deployment.
""".strip()

    summary_path = (
        VALIDATION_DIR
        / "machine_failure_executive_summary.txt"
    )

    summary_path.write_text(
        summary,
        encoding="utf-8",
    )


def main() -> None:
    create_output_directory()

    model, dataset, saved_predictions = (
        load_inputs()
    )

    validate_dataset(
        dataset
    )

    features, target = prepare_features(
        dataset
    )

    print(
        f"Machines loaded: {len(dataset):,}"
    )

    print(
        "\nRunning five-fold cross-validation..."
    )

    fold_results = run_cross_validation(
        model=model,
        features=features,
        target=target,
    )

    cross_validation_summary = (
        summarize_cross_validation(
            fold_results
        )
    )

    print(
        "\nTraining model on full dataset..."
    )

    model, probabilities = fit_full_model(
        model=model,
        features=features,
        target=target,
    )

    print(
        "\nRunning threshold analysis..."
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

    default_predictions = (
        probabilities >= 0.50
    ).astype(int)

    feature_importance = (
        extract_feature_importance(
            model
        )
    )

    default_confusion_matrix = (
        build_confusion_matrix_table(
            target=target,
            predictions=default_predictions,
        )
    )

    optimized_confusion_matrix = (
        build_confusion_matrix_table(
            target=target,
            predictions=optimized_predictions,
        )
    )

    prioritized_machines = (
        create_maintenance_priority(
            saved_predictions
        )
    )

    risk_summary = create_risk_summary(
        prioritized_machines
    )

    classification_report_text = (
        classification_report(
            target,
            optimized_predictions,
            digits=4,
            zero_division=0,
        )
    )

    fold_results.to_csv(
        VALIDATION_DIR
        / "machine_failure_cross_validation_folds.csv",
        index=False,
    )

    cross_validation_summary.to_csv(
        VALIDATION_DIR
        / "machine_failure_cross_validation_summary.csv",
        index=False,
    )

    threshold_results.to_csv(
        VALIDATION_DIR
        / "machine_failure_threshold_analysis.csv",
        index=False,
    )

    feature_importance.to_csv(
        VALIDATION_DIR
        / "machine_failure_feature_importance.csv",
        index=False,
    )

    default_confusion_matrix.to_csv(
        VALIDATION_DIR
        / "machine_failure_confusion_matrix_default.csv",
    )

    optimized_confusion_matrix.to_csv(
        VALIDATION_DIR
        / "machine_failure_confusion_matrix_optimized.csv",
    )

    prioritized_machines.to_csv(
        VALIDATION_DIR
        / "machine_failure_maintenance_priority.csv",
        index=False,
    )

    risk_summary.to_csv(
        VALIDATION_DIR
        / "machine_failure_risk_summary.csv",
        index=False,
    )

    (
        VALIDATION_DIR
        / "machine_failure_classification_report.txt"
    ).write_text(
        classification_report_text,
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
        optimized_predictions=(
            optimized_predictions
        ),
        feature_importance=(
            feature_importance
        ),
        prioritized_machines=(
            prioritized_machines
        ),
    )

    validated_model_path = (
        PROJECT_ROOT
        / "models"
        / "machine_failure_validated_model.joblib"
    )

    joblib.dump(
        model,
        validated_model_path,
    )

    print(
        "\nMachine failure validation completed."
    )

    print(
        f"Best threshold: {best_threshold:.2f}"
    )

    print(
        "\nCross-validation summary:"
    )

    print(
        cross_validation_summary.to_string(
            index=False
        )
    )

    print(
        "\nTop 10 features:"
    )

    print(
        feature_importance.head(
            10
        ).to_string(
            index=False
        )
    )

    print(
        "\nTop 10 maintenance priorities:"
    )

    print(
        prioritized_machines[
            [
                "machine_id",
                "manufacturer",
                "failure_probability",
                "failure_risk_level",
                "revenue_at_risk",
                "maintenance_priority_score",
                "recommended_action",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )

    print(
        "\nReports saved to:"
    )

    print(
        VALIDATION_DIR
    )

    print(
        "Validated model:"
    )

    print(
        validated_model_path
    )


if __name__ == "__main__":
    main()
import os
import sys
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import pyodbc
from dotenv import load_dotenv
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score,
)
from sklearn.preprocessing import StandardScaler


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

TARGET_COLUMN = "rule_based_anomaly_flag"
RANDOM_SEED = 42


FEATURE_COLUMNS = [
    "transaction_count",
    "session_count",
    "unique_player_count",
    "total_wager",
    "total_payout",
    "jackpot_amount",
    "net_gaming_revenue",
    "actual_hold_pct",
    "event_count",
    "downtime_minutes",
    "critical_event_count",
    "investigation_count",
    "active_minutes",
    "availability_pct",
    "revenue_per_active_hour",
    "revenue_z_score",
    "wager_z_score",
    "downtime_z_score",
]


def create_directories() -> None:
    """Create required output folders."""

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
    """Build SQL Server connection string using .env values."""

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


def load_anomaly_dataset() -> pd.DataFrame:
    """Load machine anomaly data from SQL Server."""

    query = """
        SELECT *
        FROM dbo.vw_ml_machine_anomaly
        ORDER BY
            activity_date,
            machine_id;
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
            "The machine anomaly dataset returned zero rows."
        )

    return dataframe


def validate_dataset(
    dataframe: pd.DataFrame,
) -> None:
    """Validate required columns and target values."""

    required_columns = {
        "activity_date",
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

    target_values = set(
        dataframe[
            TARGET_COLUMN
        ].dropna().unique()
    )

    if not target_values.issubset(
        {0, 1}
    ):
        raise ValueError(
            "rule_based_anomaly_flag must contain only 0 and 1."
        )


def prepare_features(
    dataframe: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series]:
    """Prepare numerical features and rule-based labels."""

    features = dataframe[
        FEATURE_COLUMNS
    ].copy()

    for column in FEATURE_COLUMNS:
        features[column] = pd.to_numeric(
            features[column],
            errors="coerce",
        )

    features = features.replace(
        [np.inf, -np.inf],
        np.nan,
    )

    features = features.fillna(
        features.median(
            numeric_only=True
        )
    )

    if features.isna().any().any():
        remaining_nulls = features.columns[
            features.isna().any()
        ].tolist()

        raise ValueError(
            "Null values remain in features: "
            + ", ".join(remaining_nulls)
        )

    target = dataframe[
        TARGET_COLUMN
    ].astype(int)

    return features, target


def fit_isolation_forest(
    features: pd.DataFrame,
    contamination: float,
) -> tuple[
    IsolationForest,
    StandardScaler,
    np.ndarray,
    np.ndarray,
]:
    """Fit Isolation Forest and return predictions and scores."""

    scaler = StandardScaler()

    scaled_features = scaler.fit_transform(
        features
    )

    model = IsolationForest(
        n_estimators=500,
        contamination=contamination,
        max_samples="auto",
        random_state=RANDOM_SEED,
        n_jobs=-1,
    )

    raw_predictions = model.fit_predict(
        scaled_features
    )

    anomaly_scores = (
        -model.score_samples(
            scaled_features
        )
    )

    anomaly_predictions = np.where(
        raw_predictions == -1,
        1,
        0,
    )

    return (
        model,
        scaler,
        anomaly_predictions,
        anomaly_scores,
    )


def evaluate_against_rule_based_labels(
    target: pd.Series,
    predictions: np.ndarray,
) -> dict[str, Any]:
    """
    Compare Isolation Forest flags with the existing rule-based
    anomaly labels.

    The rule-based label is not ground truth, but it provides a
    useful benchmark for overlap and review.
    """

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

    matrix = confusion_matrix(
        target,
        predictions,
    )

    return {
        "precision_vs_rule_label": precision,
        "recall_vs_rule_label": recall,
        "f1_vs_rule_label": f1,
        "true_negative": int(matrix[0, 0]),
        "false_positive": int(matrix[0, 1]),
        "false_negative": int(matrix[1, 0]),
        "true_positive": int(matrix[1, 1]),
    }


def create_anomaly_output(
    dataframe: pd.DataFrame,
    predictions: np.ndarray,
    anomaly_scores: np.ndarray,
) -> pd.DataFrame:
    """Create dashboard-ready anomaly predictions."""

    output_columns = [
        "activity_date",
        "machine_id",
        "location_id",
        "manufacturer",
        "game_title",
        "game_category",
        "software_version",
        "transaction_count",
        "session_count",
        "unique_player_count",
        "total_wager",
        "total_payout",
        "jackpot_amount",
        "net_gaming_revenue",
        "actual_hold_pct",
        "event_count",
        "downtime_minutes",
        "critical_event_count",
        "investigation_count",
        "availability_pct",
        "revenue_per_active_hour",
        "revenue_z_score",
        "wager_z_score",
        "downtime_z_score",
        TARGET_COLUMN,
    ]

    output = dataframe[
        output_columns
    ].copy()

    output[
        "isolation_forest_anomaly_flag"
    ] = predictions

    output[
        "anomaly_score"
    ] = anomaly_scores

    score_percentile = output[
        "anomaly_score"
    ].rank(
        method="average",
        pct=True,
    )

    output[
        "anomaly_percentile"
    ] = score_percentile

    output[
        "anomaly_risk_level"
    ] = pd.cut(
        score_percentile,
        bins=[
            -np.inf,
            0.80,
            0.95,
            0.99,
            np.inf,
        ],
        labels=[
            "Low",
            "Medium",
            "High",
            "Critical",
        ],
        include_lowest=True,
    )

    output[
        "anomaly_reason"
    ] = np.select(
        [
            output[
                "critical_event_count"
            ] > 0,

            output[
                "downtime_z_score"
            ] >= 3,

            output[
                "revenue_z_score"
            ].abs() >= 3,

            output[
                "wager_z_score"
            ].abs() >= 3,
        ],
        [
            "Critical machine event",
            "Unusually high downtime",
            "Unusual revenue behavior",
            "Unusual wagering behavior",
        ],
        default="Multivariate behavior anomaly",
    )

    output[
        "recommended_action"
    ] = np.select(
        [
            output[
                "anomaly_risk_level"
            ].astype(str)
            == "Critical",

            output[
                "anomaly_risk_level"
            ].astype(str)
            == "High",

            output[
                "anomaly_risk_level"
            ].astype(str)
            == "Medium",
        ],
        [
            "Immediate operational investigation",
            "Review machine and event history",
            "Increase monitoring frequency",
        ],
        default="Routine monitoring",
    )

    output[
        "revenue_exposure"
    ] = (
        output[
            "net_gaming_revenue"
        ].abs()
        * output[
            "anomaly_percentile"
        ]
    ).round(2)

    return output.sort_values(
        [
            "anomaly_score",
            "revenue_exposure",
        ],
        ascending=False,
    ).reset_index(drop=True)


def create_machine_summary(
    anomaly_output: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate anomaly behavior by machine."""

    summary = (
        anomaly_output
        .groupby(
            [
                "machine_id",
                "location_id",
                "manufacturer",
                "game_title",
                "software_version",
            ],
            as_index=False,
        )
        .agg(
            machine_day_count=(
                "activity_date",
                "count",
            ),
            anomaly_day_count=(
                "isolation_forest_anomaly_flag",
                "sum",
            ),
            rule_based_anomaly_day_count=(
                TARGET_COLUMN,
                "sum",
            ),
            average_anomaly_score=(
                "anomaly_score",
                "mean",
            ),
            maximum_anomaly_score=(
                "anomaly_score",
                "max",
            ),
            total_downtime_minutes=(
                "downtime_minutes",
                "sum",
            ),
            total_critical_events=(
                "critical_event_count",
                "sum",
            ),
            total_revenue_exposure=(
                "revenue_exposure",
                "sum",
            ),
        )
    )

    summary[
        "anomaly_rate"
    ] = (
        summary[
            "anomaly_day_count"
        ]
        / summary[
            "machine_day_count"
        ]
    )

    summary[
        "operational_priority_score"
    ] = (
        summary[
            "anomaly_rate"
        ]
        * 100
        + summary[
            "maximum_anomaly_score"
        ]
        * 20
        + summary[
            "total_critical_events"
        ]
        * 2
        + summary[
            "total_revenue_exposure"
        ]
        / 100
    ).round(2)

    summary[
        "priority_rank"
    ] = summary[
        "operational_priority_score"
    ].rank(
        method="dense",
        ascending=False,
    ).astype(int)

    return summary.sort_values(
        [
            "operational_priority_score",
            "maximum_anomaly_score",
        ],
        ascending=False,
    ).reset_index(drop=True)


def save_outputs(
    model: IsolationForest,
    scaler: StandardScaler,
    metrics: dict[str, Any],
    anomaly_output: pd.DataFrame,
    machine_summary: pd.DataFrame,
    contamination: float,
) -> None:
    """Save model artifacts and reporting outputs."""

    model_path = (
        MODELS_DIR
        / "machine_anomaly_isolation_forest.joblib"
    )

    scaler_path = (
        MODELS_DIR
        / "machine_anomaly_scaler.joblib"
    )

    metrics_path = (
        METRICS_DIR
        / "machine_anomaly_metrics.csv"
    )

    predictions_path = (
        ML_DATA_DIR
        / "machine_anomaly_predictions.csv"
    )

    summary_path = (
        METRICS_DIR
        / "machine_anomaly_machine_summary.csv"
    )

    metadata_path = (
        METRICS_DIR
        / "machine_anomaly_model_metadata.txt"
    )

    joblib.dump(
        model,
        model_path,
    )

    joblib.dump(
        scaler,
        scaler_path,
    )

    pd.DataFrame(
        [metrics]
    ).to_csv(
        metrics_path,
        index=False,
    )

    anomaly_output.to_csv(
        predictions_path,
        index=False,
    )

    machine_summary.to_csv(
        summary_path,
        index=False,
    )

    metadata_path.write_text(
        (
            "Model: Isolation Forest\n"
            f"Contamination: {contamination:.4f}\n"
            "Dataset: Synthetic machine-day gaming data\n"
            "Learning type: Unsupervised anomaly detection\n"
            "Validation benchmark: SQL rule-based anomaly label\n"
            "Important note: Rule-based labels are not true "
            "ground-truth anomalies and are used only for "
            "benchmark comparison.\n"
        ),
        encoding="utf-8",
    )

    print("\nSaved outputs:")
    print(f"Model: {model_path}")
    print(f"Scaler: {scaler_path}")
    print(f"Metrics: {metrics_path}")
    print(f"Predictions: {predictions_path}")
    print(f"Machine summary: {summary_path}")
    print(f"Metadata: {metadata_path}")


def main() -> None:
    """Run the complete anomaly-detection pipeline."""

    create_directories()

    print(
        "Loading machine anomaly dataset "
        "from SQL Server..."
    )

    dataframe = load_anomaly_dataset()

    validate_dataset(
        dataframe
    )

    dataset_path = (
        ML_DATA_DIR
        / "machine_anomaly_dataset.csv"
    )

    dataframe.to_csv(
        dataset_path,
        index=False,
    )

    print(
        f"Rows loaded: {len(dataframe):,}"
    )

    print(
        f"Machines represented: "
        f"{dataframe['machine_id'].nunique():,}"
    )

    print("\nRule-based anomaly distribution:")

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

    rule_anomaly_rate = float(
        target.mean()
    )

    contamination = float(
        np.clip(
            rule_anomaly_rate,
            0.02,
            0.20,
        )
    )

    print(
        f"\nIsolation Forest contamination: "
        f"{contamination:.4f}"
    )

    (
        model,
        scaler,
        predictions,
        anomaly_scores,
    ) = fit_isolation_forest(
        features=features,
        contamination=contamination,
    )

    metrics = (
        evaluate_against_rule_based_labels(
            target=target,
            predictions=predictions,
        )
    )

    anomaly_output = (
        create_anomaly_output(
            dataframe=dataframe,
            predictions=predictions,
            anomaly_scores=anomaly_scores,
        )
    )

    machine_summary = (
        create_machine_summary(
            anomaly_output
        )
    )

    detected_anomalies = int(
        predictions.sum()
    )

    print(
        f"\nDetected anomalies: "
        f"{detected_anomalies:,}"
    )

    print(
        f"Detected anomaly rate: "
        f"{detected_anomalies / len(predictions):.2%}"
    )

    print(
        "\nBenchmark metrics against "
        "rule-based anomaly labels:"
    )

    for key, value in metrics.items():
        if isinstance(
            value,
            float,
        ):
            print(
                f"{key}: {value:.4f}"
            )
        else:
            print(
                f"{key}: {value}"
            )

    print(
        "\nClassification report against "
        "rule-based benchmark:"
    )

    print(
        classification_report(
            target,
            predictions,
            digits=4,
            zero_division=0,
        )
    )

    print(
        "\nTop 10 anomalous machine-days:"
    )

    print(
        anomaly_output[
            [
                "activity_date",
                "machine_id",
                "manufacturer",
                "net_gaming_revenue",
                "downtime_minutes",
                "critical_event_count",
                "anomaly_score",
                "anomaly_risk_level",
                "anomaly_reason",
                "recommended_action",
            ]
        ]
        .head(10)
        .to_string(
            index=False
        )
    )

    print(
        "\nTop 10 machines by operational priority:"
    )

    print(
        machine_summary[
            [
                "machine_id",
                "manufacturer",
                "anomaly_day_count",
                "anomaly_rate",
                "maximum_anomaly_score",
                "total_critical_events",
                "total_revenue_exposure",
                "operational_priority_score",
                "priority_rank",
            ]
        ]
        .head(10)
        .to_string(
            index=False
        )
    )

    save_outputs(
        model=model,
        scaler=scaler,
        metrics=metrics,
        anomaly_output=anomaly_output,
        machine_summary=machine_summary,
        contamination=contamination,
    )


if __name__ == "__main__":
    main()
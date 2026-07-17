import sys
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    PrecisionRecallDisplay,
    RocCurveDisplay,
    confusion_matrix,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODEL_PATH = (
    PROJECT_ROOT
    / "models"
    / "player_churn_validated_model.joblib"
)

DATASET_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "ml"
    / "player_churn_dataset.csv"
)

PREDICTIONS_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "ml"
    / "player_churn_all_predictions.csv"
)

VALIDATION_DIR = (
    PROJECT_ROOT
    / "reports"
    / "model_validation"
)

EXPLAINABILITY_DIR = (
    PROJECT_ROOT
    / "reports"
    / "model_explainability"
)

TARGET_COLUMN = "churn_flag"

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


def create_directories() -> None:
    """Create output folders."""

    EXPLAINABILITY_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


def load_inputs() -> tuple[
    object,
    pd.DataFrame,
    pd.DataFrame,
]:
    """Load the validated model and saved datasets."""

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


def prepare_features(
    dataset: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series]:
    """Prepare feature matrix and target."""

    features = dataset[
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

    target = dataset[
        TARGET_COLUMN
    ].astype(int)

    return features, target


def extract_coefficients(
    model: object,
) -> pd.DataFrame:
    """Extract Logistic Regression coefficients."""

    preprocessor = model.named_steps[
        "preprocessor"
    ]

    estimator = model.named_steps[
        "model"
    ]

    if not hasattr(
        estimator,
        "coef_",
    ):
        raise ValueError(
            "The validated model does not expose "
            "Logistic Regression coefficients."
        )

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

    coefficients = estimator.coef_[0]

    dataframe = pd.DataFrame(
        {
            "feature": cleaned_names,
            "coefficient": coefficients,
        }
    )

    dataframe[
        "absolute_importance"
    ] = dataframe[
        "coefficient"
    ].abs()

    dataframe[
        "effect_direction"
    ] = np.where(
        dataframe["coefficient"] > 0,
        "Higher churn risk",
        np.where(
            dataframe["coefficient"] < 0,
            "Lower churn risk",
            "Neutral",
        ),
    )

    return dataframe.sort_values(
        "absolute_importance",
        ascending=False,
    ).reset_index(drop=True)


def plot_top_coefficients(
    coefficients: pd.DataFrame,
) -> None:
    """Plot the most influential model coefficients."""

    top_features = coefficients.head(
        15
    ).sort_values(
        "coefficient"
    )

    plt.figure(
        figsize=(10, 7)
    )

    plt.barh(
        top_features["feature"],
        top_features["coefficient"],
    )

    plt.axvline(
        0,
        linewidth=1,
    )

    plt.title(
        "Top Player Churn Model Coefficients"
    )

    plt.xlabel(
        "Coefficient"
    )

    plt.ylabel(
        "Feature"
    )

    plt.tight_layout()

    plt.savefig(
        EXPLAINABILITY_DIR
        / "player_churn_feature_coefficients.png",
        dpi=200,
        bbox_inches="tight",
    )

    plt.close()


def plot_probability_distribution(
    predictions: pd.DataFrame,
) -> None:
    """Plot churn probability distribution."""

    plt.figure(
        figsize=(9, 6)
    )

    plt.hist(
        predictions.loc[
            predictions[
                "churn_flag"
            ] == 0,
            "churn_probability",
        ],
        bins=30,
        alpha=0.6,
        label="No Churn",
    )

    plt.hist(
        predictions.loc[
            predictions[
                "churn_flag"
            ] == 1,
            "churn_probability",
        ],
        bins=30,
        alpha=0.6,
        label="Churn",
    )

    plt.title(
        "Churn Probability Distribution"
    )

    plt.xlabel(
        "Predicted Churn Probability"
    )

    plt.ylabel(
        "Player Count"
    )

    plt.legend()

    plt.tight_layout()

    plt.savefig(
        EXPLAINABILITY_DIR
        / "player_churn_probability_distribution.png",
        dpi=200,
        bbox_inches="tight",
    )

    plt.close()


def plot_confusion_matrix(
    target: pd.Series,
    probabilities: np.ndarray,
    threshold: float = 0.50,
) -> None:
    """Save confusion matrix visualization."""

    predictions = (
        probabilities >= threshold
    ).astype(int)

    matrix = confusion_matrix(
        target,
        predictions,
    )

    display = ConfusionMatrixDisplay(
        confusion_matrix=matrix,
        display_labels=[
            "No Churn",
            "Churn",
        ],
    )

    display.plot()

    plt.title(
        f"Player Churn Confusion Matrix "
        f"(Threshold = {threshold:.2f})"
    )

    plt.tight_layout()

    plt.savefig(
        EXPLAINABILITY_DIR
        / "player_churn_confusion_matrix.png",
        dpi=200,
        bbox_inches="tight",
    )

    plt.close()


def plot_roc_curve(
    target: pd.Series,
    probabilities: np.ndarray,
) -> None:
    """Save ROC curve."""

    RocCurveDisplay.from_predictions(
        target,
        probabilities,
    )

    plt.title(
        "Player Churn ROC Curve"
    )

    plt.tight_layout()

    plt.savefig(
        EXPLAINABILITY_DIR
        / "player_churn_roc_curve.png",
        dpi=200,
        bbox_inches="tight",
    )

    plt.close()


def plot_precision_recall_curve(
    target: pd.Series,
    probabilities: np.ndarray,
) -> None:
    """Save precision-recall curve."""

    PrecisionRecallDisplay.from_predictions(
        target,
        probabilities,
    )

    plt.title(
        "Player Churn Precision-Recall Curve"
    )

    plt.tight_layout()

    plt.savefig(
        EXPLAINABILITY_DIR
        / "player_churn_precision_recall_curve.png",
        dpi=200,
        bbox_inches="tight",
    )

    plt.close()


def create_revenue_at_risk(
    predictions: pd.DataFrame,
) -> pd.DataFrame:
    """Rank players by expected revenue at risk."""

    required_columns = {
        "player_id",
        "loyalty_tier",
        "days_since_last_session",
        "player_net_revenue",
        "churn_probability",
        "risk_level",
        "recommended_action",
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

    output = predictions[
        [
            "player_id",
            "loyalty_tier",
            "days_since_last_session",
            "total_historical_sessions",
            "player_net_revenue",
            "churn_probability",
            "risk_level",
            "recommended_action",
        ]
    ].copy()

    output[
        "expected_revenue_at_risk"
    ] = (
        output[
            "player_net_revenue"
        ].clip(lower=0)
        * output[
            "churn_probability"
        ]
    ).round(2)

    output[
        "retention_priority_score"
    ] = (
        output[
            "expected_revenue_at_risk"
        ]
        * (
            1
            + output[
                "days_since_last_session"
            ].fillna(0)
            / 365
        )
    ).round(2)

    output[
        "priority_rank"
    ] = output[
        "retention_priority_score"
    ].rank(
        method="dense",
        ascending=False,
    ).astype(int)

    return output.sort_values(
        [
            "retention_priority_score",
            "churn_probability",
        ],
        ascending=False,
    ).reset_index(drop=True)


def create_priority_summary(
    prioritized_players: pd.DataFrame,
) -> pd.DataFrame:
    """Create Power BI-ready retention summary."""

    summary = (
        prioritized_players
        .groupby(
            "risk_level",
            observed=False,
        )
        .agg(
            player_count=(
                "player_id",
                "count",
            ),
            total_player_revenue=(
                "player_net_revenue",
                "sum",
            ),
            expected_revenue_at_risk=(
                "expected_revenue_at_risk",
                "sum",
            ),
            average_churn_probability=(
                "churn_probability",
                "mean",
            ),
            average_days_since_last_session=(
                "days_since_last_session",
                "mean",
            ),
        )
        .reset_index()
    )

    return summary.sort_values(
        "expected_revenue_at_risk",
        ascending=False,
    )


def write_business_summary(
    coefficients: pd.DataFrame,
    prioritized_players: pd.DataFrame,
    priority_summary: pd.DataFrame,
) -> None:
    """Write model interpretation and business recommendations."""

    top_risk_features = coefficients.loc[
        coefficients[
            "coefficient"
        ] > 0
    ].head(5)

    top_retention_features = coefficients.loc[
        coefficients[
            "coefficient"
        ] < 0
    ].head(5)

    top_risk_lines = "\n".join(
        f"- {row.feature}"
        for row in top_risk_features.itertuples()
    )

    top_retention_lines = "\n".join(
        f"- {row.feature}"
        for row in top_retention_features.itertuples()
    )

    top_priority = prioritized_players.head(
        100
    )

    summary = f"""
PLAYER CHURN EXPLAINABILITY & BUSINESS PRIORITIZATION
=====================================================

Dataset
-------
Players scored: {len(prioritized_players):,}

Critical and High-Risk Players
------------------------------
Critical risk: {
    int(
        (
            prioritized_players[
                "risk_level"
            ] == "Critical"
        ).sum()
    )
:,}

High risk: {
    int(
        (
            prioritized_players[
                "risk_level"
            ] == "High"
        ).sum()
    )
:,}

Revenue at Risk
---------------
Estimated total revenue at risk: ${
    prioritized_players[
        "expected_revenue_at_risk"
    ].sum()
:,.2f}

Top 100 priority-player revenue at risk: ${
    top_priority[
        "expected_revenue_at_risk"
    ].sum()
:,.2f}

Features Associated with Higher Churn Risk
------------------------------------------
{top_risk_lines}

Features Associated with Lower Churn Risk
-----------------------------------------
{top_retention_lines}

Recommended Business Actions
----------------------------
1. Prioritize the highest retention-priority scores, not only
   the highest churn probabilities.
2. Contact Critical-risk players immediately.
3. Send targeted loyalty offers to High-risk players with
   positive historical revenue.
4. Monitor Medium-risk players for reduced recent engagement.
5. Use player value and probability together to control
   campaign costs.

Interpretation Note
-------------------
Results are based on synthetic behavioral gaming data.
Model performance and revenue-at-risk estimates must be
externally validated before production use.
""".strip()

    (
        EXPLAINABILITY_DIR
        / "player_churn_business_summary.txt"
    ).write_text(
        summary,
        encoding="utf-8",
    )

    priority_summary.to_csv(
        EXPLAINABILITY_DIR
        / "player_churn_risk_summary.csv",
        index=False,
    )


def main() -> None:
    create_directories()

    model, dataset, predictions = (
        load_inputs()
    )

    features, target = prepare_features(
        dataset
    )

    model.fit(
        features,
        target,
    )

    probabilities = model.predict_proba(
        features
    )[:, 1]

    coefficients = extract_coefficients(
        model
    )

    prioritized_players = (
        create_revenue_at_risk(
            predictions
        )
    )

    priority_summary = (
        create_priority_summary(
            prioritized_players
        )
    )

    coefficients.to_csv(
        EXPLAINABILITY_DIR
        / "player_churn_coefficients.csv",
        index=False,
    )

    prioritized_players.to_csv(
        EXPLAINABILITY_DIR
        / "player_churn_retention_priority.csv",
        index=False,
    )

    plot_top_coefficients(
        coefficients
    )

    plot_probability_distribution(
        predictions
    )

    plot_confusion_matrix(
        target,
        probabilities,
        threshold=0.50,
    )

    plot_roc_curve(
        target,
        probabilities,
    )

    plot_precision_recall_curve(
        target,
        probabilities,
    )

    write_business_summary(
        coefficients=coefficients,
        prioritized_players=(
            prioritized_players
        ),
        priority_summary=priority_summary,
    )

    print(
        "Player churn explainability completed."
    )

    print(
        f"Outputs saved to: "
        f"{EXPLAINABILITY_DIR}"
    )

    print(
        "\nTop 10 retention priorities:"
    )

    print(
        prioritized_players.head(
            10
        ).to_string(
            index=False
        )
    )


if __name__ == "__main__":
    main()
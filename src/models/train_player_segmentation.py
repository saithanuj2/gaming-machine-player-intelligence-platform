import os
import sys
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import pyodbc
from dotenv import load_dotenv
from sklearn.cluster import KMeans
from sklearn.impute import SimpleImputer
from sklearn.metrics import silhouette_score
from sklearn.pipeline import Pipeline
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

RANDOM_SEED = 42


FEATURE_COLUMNS = [
    "session_count",
    "locations_visited",
    "machines_played",
    "total_session_minutes",
    "total_rounds",
    "total_wager",
    "player_net_revenue",
    "average_session_minutes",
    "average_wager_per_session",
    "days_since_last_session",
]


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


def load_player_dataset() -> pd.DataFrame:
    """Load active player-level metrics from SQL Server."""

    query = """
        SELECT
            player_id,
            loyalty_tier,
            age_band,
            home_region,
            marketing_opt_in,
            session_count,
            locations_visited,
            machines_played,
            total_session_minutes,
            total_rounds,
            total_wager,
            player_net_revenue,
            average_session_minutes,
            average_wager_per_session,
            days_since_last_session
        FROM dbo.vw_player_summary
        WHERE session_count > 0
        ORDER BY player_id;
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
            "The player summary view returned zero active players."
        )

    return dataframe


def validate_dataset(
    dataframe: pd.DataFrame,
) -> None:
    """Validate player identifiers and required features."""

    required_columns = {
        "player_id",
        "loyalty_tier",
        "age_band",
        "home_region",
        "marketing_opt_in",
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
        "player_id"
    ].duplicated().any():
        raise ValueError(
            "Duplicate player IDs were found."
        )

    if len(dataframe) < 100:
        raise ValueError(
            "At least 100 active players are required "
            "for segmentation."
        )


def prepare_features(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """Prepare segmentation features."""

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

    return features


def build_preprocessing_pipeline() -> Pipeline:
    """Create imputation and scaling pipeline."""

    return Pipeline(
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


def evaluate_cluster_counts(
    scaled_features: np.ndarray,
    minimum_clusters: int = 2,
    maximum_clusters: int = 8,
) -> pd.DataFrame:
    """Evaluate candidate K values using silhouette and inertia."""

    records = []

    for cluster_count in range(
        minimum_clusters,
        maximum_clusters + 1,
    ):
        model = KMeans(
            n_clusters=cluster_count,
            n_init=30,
            max_iter=500,
            random_state=RANDOM_SEED,
        )

        labels = model.fit_predict(
            scaled_features
        )

        silhouette = silhouette_score(
            scaled_features,
            labels,
        )

        records.append(
            {
                "cluster_count": cluster_count,
                "silhouette_score": silhouette,
                "inertia": model.inertia_,
            }
        )

        print(
            f"K={cluster_count}: "
            f"Silhouette={silhouette:.4f}, "
            f"Inertia={model.inertia_:,.2f}"
        )

    return pd.DataFrame(
        records
    )


def select_best_cluster_count(
    evaluation_results: pd.DataFrame,
) -> int:
    """Select K with the highest silhouette score."""

    best_row = evaluation_results.sort_values(
        [
            "silhouette_score",
            "cluster_count",
        ],
        ascending=[
            False,
            True,
        ],
    ).iloc[0]

    return int(
        best_row[
            "cluster_count"
        ]
    )


def train_kmeans(
    scaled_features: np.ndarray,
    cluster_count: int,
) -> tuple[KMeans, np.ndarray]:
    """Train the final K-Means model."""

    model = KMeans(
        n_clusters=cluster_count,
        n_init=50,
        max_iter=500,
        random_state=RANDOM_SEED,
    )

    labels = model.fit_predict(
        scaled_features
    )

    return model, labels


def create_cluster_profiles(
    dataframe: pd.DataFrame,
    cluster_labels: np.ndarray,
) -> pd.DataFrame:
    """Create average behavioral metrics for each cluster."""

    output = dataframe.copy()

    output[
        "cluster_id"
    ] = cluster_labels

    cluster_profiles = (
        output
        .groupby(
            "cluster_id",
            as_index=False,
        )
        .agg(
            player_count=(
                "player_id",
                "count",
            ),
            average_sessions=(
                "session_count",
                "mean",
            ),
            average_locations_visited=(
                "locations_visited",
                "mean",
            ),
            average_machines_played=(
                "machines_played",
                "mean",
            ),
            average_session_minutes=(
                "average_session_minutes",
                "mean",
            ),
            average_wager_per_session=(
                "average_wager_per_session",
                "mean",
            ),
            average_total_wager=(
                "total_wager",
                "mean",
            ),
            average_player_revenue=(
                "player_net_revenue",
                "mean",
            ),
            average_days_since_last_session=(
                "days_since_last_session",
                "mean",
            ),
            total_segment_revenue=(
                "player_net_revenue",
                "sum",
            ),
        )
    )

    cluster_profiles[
        "player_distribution_pct"
    ] = (
        cluster_profiles[
            "player_count"
        ]
        / cluster_profiles[
            "player_count"
        ].sum()
        * 100
    )

    cluster_profiles[
        "revenue_contribution_pct"
    ] = (
        cluster_profiles[
            "total_segment_revenue"
        ]
        / cluster_profiles[
            "total_segment_revenue"
        ].sum()
        * 100
    )

    return cluster_profiles


def calculate_cluster_scores(
    cluster_profiles: pd.DataFrame,
) -> pd.DataFrame:
    """Create relative value, engagement, and churn-risk scores."""

    output = cluster_profiles.copy()

    output[
        "value_rank"
    ] = output[
        "average_player_revenue"
    ].rank(
        method="dense",
        ascending=False,
    )

    output[
        "wager_rank"
    ] = output[
        "average_total_wager"
    ].rank(
        method="dense",
        ascending=False,
    )

    output[
        "engagement_rank"
    ] = output[
        "average_sessions"
    ].rank(
        method="dense",
        ascending=False,
    )

    output[
        "recency_risk_rank"
    ] = output[
        "average_days_since_last_session"
    ].rank(
        method="dense",
        ascending=False,
    )

    max_rank = max(
        len(output),
        1,
    )

    output[
        "value_score"
    ] = (
        max_rank
        - output["value_rank"]
        + 1
    )

    output[
        "engagement_score"
    ] = (
        max_rank
        - output["engagement_rank"]
        + 1
    )

    output[
        "risk_score"
    ] = (
        max_rank
        - output["recency_risk_rank"]
        + 1
    )

    return output


def assign_business_labels(
    scored_profiles: pd.DataFrame,
) -> dict[int, str]:
    """Assign unique business-friendly names to each cluster."""

    profiles = scored_profiles.copy()

    label_map: dict[int, str] = {}

    available_clusters = set(
        profiles[
            "cluster_id"
        ].astype(int)
    )

    if not available_clusters:
        raise ValueError(
            "No clusters are available for labeling."
        )

    vip_cluster = int(
        profiles.sort_values(
            [
                "average_player_revenue",
                "average_total_wager",
                "average_sessions",
            ],
            ascending=False,
        ).iloc[0]["cluster_id"]
    )

    label_map[
        vip_cluster
    ] = "VIP High Value"

    available_clusters.discard(
        vip_cluster
    )

    if available_clusters:
        remaining = profiles.loc[
            profiles[
                "cluster_id"
            ].isin(
                available_clusters
            )
        ]

        at_risk_cluster = int(
            remaining.sort_values(
                [
                    "average_days_since_last_session",
                    "average_sessions",
                ],
                ascending=[
                    False,
                    True,
                ],
            ).iloc[0]["cluster_id"]
        )

        label_map[
            at_risk_cluster
        ] = "At-Risk Players"

        available_clusters.discard(
            at_risk_cluster
        )

    if available_clusters:
        remaining = profiles.loc[
            profiles[
                "cluster_id"
            ].isin(
                available_clusters
            )
        ]

        loyal_cluster = int(
            remaining.sort_values(
                [
                    "average_sessions",
                    "average_days_since_last_session",
                ],
                ascending=[
                    False,
                    True,
                ],
            ).iloc[0]["cluster_id"]
        )

        label_map[
            loyal_cluster
        ] = "Loyal Regulars"

        available_clusters.discard(
            loyal_cluster
        )

    if available_clusters:
        remaining = profiles.loc[
            profiles[
                "cluster_id"
            ].isin(
                available_clusters
            )
        ]

        casual_cluster = int(
            remaining.sort_values(
                [
                    "average_sessions",
                    "average_total_wager",
                ],
                ascending=[
                    True,
                    True,
                ],
            ).iloc[0]["cluster_id"]
        )

        label_map[
            casual_cluster
        ] = "Casual Players"

        available_clusters.discard(
            casual_cluster
        )

    additional_labels = [
        "Emerging High Value",
        "Multi-Location Explorers",
        "Moderate Engagement",
        "Dormant Low Value",
    ]

    for cluster_id, label in zip(
        sorted(available_clusters),
        additional_labels,
    ):
        label_map[
            int(cluster_id)
        ] = label

    for cluster_id in available_clusters:
        if int(cluster_id) not in label_map:
            label_map[
                int(cluster_id)
            ] = (
                f"Player Segment {int(cluster_id) + 1}"
            )

    return label_map


def create_segment_actions(
    segment_name: str,
) -> tuple[str, str]:
    """Return a strategy and recommended action for each segment."""

    action_map = {
        "VIP High Value": (
            "Protect high-value relationships",
            "Offer exclusive rewards, VIP support, "
            "and personalized premium promotions",
        ),
        "Loyal Regulars": (
            "Increase wallet share and loyalty",
            "Provide frequency-based rewards and "
            "cross-location loyalty incentives",
        ),
        "At-Risk Players": (
            "Reduce churn and reactivate engagement",
            "Launch targeted retention outreach and "
            "time-sensitive return offers",
        ),
        "Casual Players": (
            "Increase visit frequency",
            "Use low-cost promotional offers and "
            "beginner-friendly engagement campaigns",
        ),
        "Emerging High Value": (
            "Accelerate movement toward VIP status",
            "Offer tier-up incentives and personalized "
            "high-value promotions",
        ),
        "Multi-Location Explorers": (
            "Strengthen cross-location loyalty",
            "Recommend nearby locations and portable "
            "loyalty rewards",
        ),
        "Moderate Engagement": (
            "Increase engagement consistency",
            "Use personalized reminders and recurring "
            "visit incentives",
        ),
        "Dormant Low Value": (
            "Evaluate economical reactivation",
            "Use low-cost automated win-back messaging",
        ),
    }

    return action_map.get(
        segment_name,
        (
            "Monitor player behavior",
            "Apply segment-specific engagement strategy",
        ),
    )


def create_player_output(
    dataframe: pd.DataFrame,
    cluster_labels: np.ndarray,
    label_map: dict[int, str],
) -> pd.DataFrame:
    """Create player-level segmentation output."""

    output = dataframe.copy()

    output[
        "cluster_id"
    ] = cluster_labels

    output[
        "player_segment"
    ] = output[
        "cluster_id"
    ].map(
        label_map
    )

    strategies = output[
        "player_segment"
    ].apply(
        create_segment_actions
    )

    output[
        "segment_strategy"
    ] = strategies.apply(
        lambda item: item[0]
    )

    output[
        "recommended_action"
    ] = strategies.apply(
        lambda item: item[1]
    )

    output[
        "estimated_player_value"
    ] = (
        output[
            "player_net_revenue"
        ].clip(lower=0)
        * (
            1
            + output[
                "session_count"
            ]
            / output[
                "session_count"
            ].max()
        )
    ).round(2)

    return output.sort_values(
        [
            "player_segment",
            "estimated_player_value",
        ],
        ascending=[
            True,
            False,
        ],
    ).reset_index(drop=True)


def create_final_segment_profiles(
    scored_profiles: pd.DataFrame,
    label_map: dict[int, str],
) -> pd.DataFrame:
    """Attach names and actions to cluster profiles."""

    output = scored_profiles.copy()

    output[
        "player_segment"
    ] = output[
        "cluster_id"
    ].map(
        label_map
    )

    strategies = output[
        "player_segment"
    ].apply(
        create_segment_actions
    )

    output[
        "segment_strategy"
    ] = strategies.apply(
        lambda item: item[0]
    )

    output[
        "recommended_action"
    ] = strategies.apply(
        lambda item: item[1]
    )

    return output.sort_values(
        "average_player_revenue",
        ascending=False,
    ).reset_index(drop=True)


def save_outputs(
    preprocessing_pipeline: Pipeline,
    model: KMeans,
    evaluation_results: pd.DataFrame,
    player_output: pd.DataFrame,
    segment_profiles: pd.DataFrame,
    best_cluster_count: int,
    best_silhouette_score: float,
) -> None:
    """Save model, preprocessing, results, and metadata."""

    model_path = (
        MODELS_DIR
        / "player_segmentation_kmeans.joblib"
    )

    preprocessing_path = (
        MODELS_DIR
        / "player_segmentation_preprocessor.joblib"
    )

    evaluation_path = (
        METRICS_DIR
        / "player_segmentation_cluster_evaluation.csv"
    )

    player_output_path = (
        ML_DATA_DIR
        / "player_segmentation_predictions.csv"
    )

    profile_path = (
        METRICS_DIR
        / "player_segmentation_profiles.csv"
    )

    metadata_path = (
        METRICS_DIR
        / "player_segmentation_metadata.txt"
    )

    joblib.dump(
        model,
        model_path,
    )

    joblib.dump(
        preprocessing_pipeline,
        preprocessing_path,
    )

    evaluation_results.to_csv(
        evaluation_path,
        index=False,
    )

    player_output.to_csv(
        player_output_path,
        index=False,
    )

    segment_profiles.to_csv(
        profile_path,
        index=False,
    )

    metadata_path.write_text(
        (
            "Model: K-Means Player Segmentation\n"
            f"Selected cluster count: {best_cluster_count}\n"
            f"Silhouette score: {best_silhouette_score:.4f}\n"
            f"Players segmented: {len(player_output):,}\n"
            "Selection method: Maximum silhouette score\n"
            "Preprocessing: Median imputation and "
            "standard scaling\n"
            "Dataset type: Synthetic gaming player data\n"
            "Learning type: Unsupervised clustering\n"
            "Important note: Business segment names are "
            "assigned after clustering using aggregated "
            "behavioral profiles.\n"
        ),
        encoding="utf-8",
    )

    print("\nSaved outputs:")
    print(
        f"Model: {model_path}"
    )
    print(
        f"Preprocessor: {preprocessing_path}"
    )
    print(
        f"Cluster evaluation: {evaluation_path}"
    )
    print(
        f"Player segments: {player_output_path}"
    )
    print(
        f"Segment profiles: {profile_path}"
    )
    print(
        f"Metadata: {metadata_path}"
    )


def main() -> None:
    """Run the complete player-segmentation workflow."""

    create_directories()

    print(
        "Loading player segmentation dataset "
        "from SQL Server..."
    )

    dataframe = load_player_dataset()

    validate_dataset(
        dataframe
    )

    dataset_path = (
        ML_DATA_DIR
        / "player_segmentation_dataset.csv"
    )

    dataframe.to_csv(
        dataset_path,
        index=False,
    )

    print(
        f"Players loaded: {len(dataframe):,}"
    )

    print(
        f"Features used: {len(FEATURE_COLUMNS):,}"
    )

    features = prepare_features(
        dataframe
    )

    preprocessing_pipeline = (
        build_preprocessing_pipeline()
    )

    scaled_features = (
        preprocessing_pipeline
        .fit_transform(
            features
        )
    )

    print(
        "\nEvaluating cluster counts..."
    )

    evaluation_results = (
        evaluate_cluster_counts(
            scaled_features=scaled_features,
            minimum_clusters=2,
            maximum_clusters=8,
        )
    )

    best_cluster_count = (
        select_best_cluster_count(
            evaluation_results
        )
    )

    best_silhouette_score = float(
        evaluation_results.loc[
            evaluation_results[
                "cluster_count"
            ] == best_cluster_count,
            "silhouette_score",
        ].iloc[0]
    )

    print(
        f"\nSelected cluster count: "
        f"{best_cluster_count}"
    )

    print(
        f"Best silhouette score: "
        f"{best_silhouette_score:.4f}"
    )

    model, cluster_labels = (
        train_kmeans(
            scaled_features=scaled_features,
            cluster_count=best_cluster_count,
        )
    )

    cluster_profiles = (
        create_cluster_profiles(
            dataframe=dataframe,
            cluster_labels=cluster_labels,
        )
    )

    scored_profiles = (
        calculate_cluster_scores(
            cluster_profiles
        )
    )

    label_map = (
        assign_business_labels(
            scored_profiles
        )
    )

    player_output = (
        create_player_output(
            dataframe=dataframe,
            cluster_labels=cluster_labels,
            label_map=label_map,
        )
    )

    final_segment_profiles = (
        create_final_segment_profiles(
            scored_profiles=scored_profiles,
            label_map=label_map,
        )
    )

    print(
        "\nCluster evaluation:"
    )

    print(
        evaluation_results.to_string(
            index=False
        )
    )

    print(
        "\nPlayer segment profiles:"
    )

    print(
        final_segment_profiles[
            [
                "cluster_id",
                "player_segment",
                "player_count",
                "average_sessions",
                "average_total_wager",
                "average_player_revenue",
                "average_days_since_last_session",
                "player_distribution_pct",
                "revenue_contribution_pct",
            ]
        ].to_string(
            index=False
        )
    )

    print(
        "\nSegment distribution:"
    )

    print(
        player_output[
            "player_segment"
        ]
        .value_counts()
        .to_string()
    )

    save_outputs(
        preprocessing_pipeline=(
            preprocessing_pipeline
        ),
        model=model,
        evaluation_results=(
            evaluation_results
        ),
        player_output=(
            player_output
        ),
        segment_profiles=(
            final_segment_profiles
        ),
        best_cluster_count=(
            best_cluster_count
        ),
        best_silhouette_score=(
            best_silhouette_score
        ),
    )


if __name__ == "__main__":
    main()
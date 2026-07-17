import random
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (
    END_DATE,
    NUM_SESSIONS,
    RANDOM_SEED,
    RAW_DATA_DIR,
    START_DATE,
)


random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)


TIER_ENGAGEMENT_BONUS = {
    "Standard": 0.00,
    "Silver": 0.08,
    "Gold": 0.16,
    "Platinum": 0.24,
}

TIER_SPEND_MULTIPLIER = {
    "Standard": 1.00,
    "Silver": 1.15,
    "Gold": 1.35,
    "Platinum": 1.65,
}


def sigmoid(values: np.ndarray) -> np.ndarray:
    """Convert raw scores into probabilities."""

    return 1.0 / (1.0 + np.exp(-values))


def build_player_profiles(
    players: pd.DataFrame,
) -> pd.DataFrame:
    """
    Create synthetic player behavior profiles.

    These profiles are used only for data generation and are not
    included as model features. This prevents direct target leakage.
    """

    active_players = players.loc[
        players["active_flag"] == 1
    ].copy()

    if active_players.empty:
        raise ValueError(
            "No active players are available."
        )

    tier_bonus = (
        active_players["loyalty_tier"]
        .map(TIER_ENGAGEMENT_BONUS)
        .fillna(0.0)
        .to_numpy()
    )

    marketing_bonus = (
        active_players["marketing_opt_in"]
        .astype(float)
        .to_numpy()
        * 0.07
    )

    baseline_engagement = np.random.beta(
        a=2.3,
        b=2.1,
        size=len(active_players),
    )

    random_behavior_noise = np.random.normal(
        loc=0.0,
        scale=0.07,
        size=len(active_players),
    )

    engagement_score = np.clip(
        baseline_engagement * 0.72
        + tier_bonus
        + marketing_bonus
        + random_behavior_noise,
        0.05,
        0.98,
    )

    # Players with low engagement, lower loyalty and no marketing
    # opt-in have a greater probability of not returning.
    churn_logit = (
        1.55
        - 3.05 * engagement_score
        - 0.35 * tier_bonus
        - 0.25 * marketing_bonus
        + np.random.normal(
            loc=0.0,
            scale=0.35,
            size=len(active_players),
        )
    )

    churn_probability = np.clip(
        sigmoid(churn_logit),
        0.05,
        0.92,
    )

    synthetic_churn_profile = (
        np.random.random(
            len(active_players)
        )
        < churn_probability
    ).astype(int)

    # Guarantee that both retained and churn-profile players exist.
    if synthetic_churn_profile.sum() == 0:
        synthetic_churn_profile[
            np.argmax(churn_probability)
        ] = 1

    if synthetic_churn_profile.sum() == len(
        synthetic_churn_profile
    ):
        synthetic_churn_profile[
            np.argmin(churn_probability)
        ] = 0

    active_players[
        "engagement_score"
    ] = engagement_score

    active_players[
        "churn_probability"
    ] = churn_probability

    active_players[
        "synthetic_churn_profile"
    ] = synthetic_churn_profile

    active_players[
        "spend_multiplier"
    ] = (
        active_players["loyalty_tier"]
        .map(TIER_SPEND_MULTIPLIER)
        .fillna(1.0)
        .astype(float)
    )

    return active_players.reset_index(
        drop=True
    )


def allocate_session_counts(
    profiles: pd.DataFrame,
) -> pd.DataFrame:
    """
    Allocate historical and future sessions.

    Historical sessions occur before the prediction cutoff.
    Retained players receive at least one session in the final
    60-day target window. Churn-profile players receive none.
    """

    player_count = len(profiles)

    historical_target = int(
        NUM_SESSIONS * 0.72
    )

    future_target = (
        NUM_SESSIONS - historical_target
    )

    if historical_target < player_count:
        raise ValueError(
            "NUM_SESSIONS is too small to provide "
            "at least one historical session per "
            "active player."
        )

    historical_counts = np.ones(
        player_count,
        dtype=int,
    )

    remaining_historical = (
        historical_target - player_count
    )

    historical_weights = (
        0.15
        + profiles[
            "engagement_score"
        ].to_numpy() ** 1.7
    )

    historical_weights = (
        historical_weights
        / historical_weights.sum()
    )

    historical_counts += np.random.multinomial(
        remaining_historical,
        historical_weights,
    )

    retained_mask = (
        profiles[
            "synthetic_churn_profile"
        ].to_numpy()
        == 0
    )

    retained_indexes = np.flatnonzero(
        retained_mask
    )

    if future_target < len(retained_indexes):
        raise ValueError(
            "The future session allocation is too "
            "small to provide one return session "
            "per retained player."
        )

    future_counts = np.zeros(
        player_count,
        dtype=int,
    )

    future_counts[
        retained_indexes
    ] = 1

    remaining_future = (
        future_target
        - len(retained_indexes)
    )

    retained_weights = (
        profiles.loc[
            retained_mask,
            "engagement_score",
        ].to_numpy() ** 2.0
    )

    retained_weights = (
        retained_weights
        / retained_weights.sum()
    )

    additional_future_counts = (
        np.random.multinomial(
            remaining_future,
            retained_weights,
        )
    )

    future_counts[
        retained_indexes
    ] += additional_future_counts

    profiles = profiles.copy()

    profiles[
        "historical_session_count"
    ] = historical_counts

    profiles[
        "target_window_session_count"
    ] = future_counts

    if (
        profiles[
            "historical_session_count"
        ].sum()
        + profiles[
            "target_window_session_count"
        ].sum()
        != NUM_SESSIONS
    ):
        raise ValueError(
            "Allocated session counts do not match "
            "NUM_SESSIONS."
        )

    return profiles


def generate_historical_timestamps(
    repeated_profiles: pd.DataFrame,
    cutoff_date: pd.Timestamp,
) -> pd.DatetimeIndex:
    """
    Generate historical timestamps.

    Retained and highly engaged players are skewed toward more
    recent dates. Churn-profile players are skewed toward earlier
    dates, producing meaningful recency behavior.
    """

    start_timestamp = pd.Timestamp(
        START_DATE
    )

    historical_end = (
        cutoff_date
        + pd.Timedelta(
            hours=23,
            minutes=59,
        )
    )

    engagement = repeated_profiles[
        "engagement_score"
    ].to_numpy()

    churn_profile = repeated_profiles[
        "synthetic_churn_profile"
    ].to_numpy()

    retained_alpha = (
        2.2 + 2.8 * engagement
    )

    retained_beta = np.full(
        len(repeated_profiles),
        1.45,
    )

    churn_alpha = (
        1.05 + 0.55 * engagement
    )

    churn_beta = (
        2.7
        + 2.0 * (
            1.0 - engagement
        )
    )

    alpha = np.where(
        churn_profile == 1,
        churn_alpha,
        retained_alpha,
    )

    beta = np.where(
        churn_profile == 1,
        churn_beta,
        retained_beta,
    )

    date_fraction = np.random.beta(
        alpha,
        beta,
    )

    total_seconds = int(
        (
            historical_end
            - start_timestamp
        ).total_seconds()
    )

    timestamp_seconds = (
        date_fraction * total_seconds
    ).astype(np.int64)

    return pd.DatetimeIndex(
        start_timestamp
        + pd.to_timedelta(
            timestamp_seconds,
            unit="s",
        )
    )


def generate_future_timestamps(
    number_of_records: int,
    cutoff_date: pd.Timestamp,
) -> pd.DatetimeIndex:
    """Generate sessions inside the final 60-day target window."""

    if number_of_records <= 0:
        return pd.DatetimeIndex([])

    future_start = (
        cutoff_date
        + pd.Timedelta(days=1)
    )

    future_end = (
        pd.Timestamp(END_DATE)
        + pd.Timedelta(
            hours=23,
            minutes=59,
        )
    )

    date_fraction = np.random.beta(
        a=1.7,
        b=1.45,
        size=number_of_records,
    )

    total_seconds = int(
        (
            future_end
            - future_start
        ).total_seconds()
    )

    timestamp_seconds = (
        date_fraction * total_seconds
    ).astype(np.int64)

    timestamps = pd.DatetimeIndex(
        future_start
        + pd.to_timedelta(
            timestamp_seconds,
            unit="s",
        )
    )

    # Stabilize the SQL predictive-view cutoff by guaranteeing
    # that the dataset contains activity on END_DATE.
    timestamps_array = timestamps.to_numpy(
        copy=True
    )

    timestamps_array[-1] = (
        pd.Timestamp(END_DATE)
        + pd.Timedelta(hours=20)
    ).to_datetime64()

    return pd.DatetimeIndex(
        timestamps_array
    )


def create_session_records(
    profiles: pd.DataFrame,
) -> pd.DataFrame:
    """Expand player profiles into one record per session."""

    cutoff_date = (
        pd.Timestamp(END_DATE)
        - pd.Timedelta(days=60)
    )

    historical_player_indexes = np.repeat(
        profiles.index.to_numpy(),
        profiles[
            "historical_session_count"
        ].to_numpy(),
    )

    future_player_indexes = np.repeat(
        profiles.index.to_numpy(),
        profiles[
            "target_window_session_count"
        ].to_numpy(),
    )

    historical_profiles = profiles.loc[
        historical_player_indexes
    ].reset_index(drop=True)

    future_profiles = profiles.loc[
        future_player_indexes
    ].reset_index(drop=True)

    historical_profiles[
        "session_start"
    ] = generate_historical_timestamps(
        historical_profiles,
        cutoff_date,
    )

    future_profiles[
        "session_start"
    ] = generate_future_timestamps(
        len(future_profiles),
        cutoff_date,
    )

    historical_profiles[
        "session_period"
    ] = "Historical"

    future_profiles[
        "session_period"
    ] = "Target Window"

    session_profiles = pd.concat(
        [
            historical_profiles,
            future_profiles,
        ],
        ignore_index=True,
    )

    if len(session_profiles) != NUM_SESSIONS:
        raise ValueError(
            f"Expected {NUM_SESSIONS} expanded sessions "
            f"but found {len(session_profiles)}."
        )

    return session_profiles


def generate_sessions(
    players: pd.DataFrame,
    machines: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate behavioral player sessions."""

    active_machines = machines.loc[
        machines[
            "machine_status"
        ] == "Active",
        [
            "machine_id",
            "location_id",
        ],
    ].copy()

    if active_machines.empty:
        raise ValueError(
            "No active machines are available."
        )

    profiles = build_player_profiles(
        players
    )

    profiles = allocate_session_counts(
        profiles
    )

    session_profiles = create_session_records(
        profiles
    )

    selected_machine_indexes = np.random.choice(
        active_machines.index,
        size=NUM_SESSIONS,
        replace=True,
    )

    selected_machines = active_machines.loc[
        selected_machine_indexes
    ].reset_index(drop=True)

    engagement = session_profiles[
        "engagement_score"
    ].to_numpy()

    spend_multiplier = session_profiles[
        "spend_multiplier"
    ].to_numpy()

    churn_profile = session_profiles[
        "synthetic_churn_profile"
    ].to_numpy()

    session_period = session_profiles[
        "session_period"
    ].to_numpy()

    # Highly engaged players generally play longer.
    duration_scale = (
        14
        + 28 * engagement
        + 5 * (
            spend_multiplier - 1
        )
    )

    # Churn-profile players exhibit slightly shorter historical
    # sessions, reinforcing declining engagement behavior.
    churn_duration_multiplier = np.where(
        churn_profile == 1,
        0.78,
        1.0,
    )

    target_window_multiplier = np.where(
        session_period == "Target Window",
        1.06,
        1.0,
    )

    session_duration_minutes = np.clip(
        np.random.gamma(
            shape=2.25,
            scale=duration_scale / 2.25,
        )
        * churn_duration_multiplier
        * target_window_multiplier,
        5,
        360,
    ).astype(int)

    session_start = pd.to_datetime(
        session_profiles[
            "session_start"
        ]
    )

    session_end = (
        session_start
        + pd.to_timedelta(
            session_duration_minutes,
            unit="m",
        )
    )

    rounds_per_minute = np.clip(
        np.random.normal(
            loc=1.0
            + 0.85 * engagement,
            scale=0.24,
            size=NUM_SESSIONS,
        ),
        0.45,
        2.8,
    )

    total_rounds = np.maximum(
        (
            session_duration_minutes
            * rounds_per_minute
        ).astype(int),
        1,
    )

    base_wager = np.random.gamma(
        shape=2.0,
        scale=1.25,
        size=NUM_SESSIONS,
    )

    average_wager_per_round = np.clip(
        base_wager
        * (
            0.65
            + engagement
        )
        * spend_multiplier,
        0.25,
        35,
    )

    total_wager = np.round(
        total_rounds
        * average_wager_per_round,
        2,
    )

    actual_hold_percentage = np.clip(
        np.random.normal(
            loc=0.09,
            scale=0.035,
            size=NUM_SESSIONS,
        ),
        -0.20,
        0.35,
    )

    net_gaming_revenue = np.round(
        total_wager
        * actual_hold_percentage,
        2,
    )

    total_payout = np.maximum(
        np.round(
            total_wager
            - net_gaming_revenue,
            2,
        ),
        0,
    )

    sessions = pd.DataFrame(
        {
            "session_id": np.arange(
                1,
                NUM_SESSIONS + 1,
            ),
            "player_id": session_profiles[
                "player_id"
            ].to_numpy(),
            "machine_id": selected_machines[
                "machine_id"
            ].to_numpy(),
            "location_id": selected_machines[
                "location_id"
            ].to_numpy(),
            "session_start": session_start,
            "session_end": session_end,
            "session_duration_minutes": (
                session_duration_minutes
            ),
            "total_rounds": total_rounds,
            "total_wager": total_wager,
            "total_payout": total_payout,
            "net_gaming_revenue": (
                total_wager
                - total_payout
            ).round(2),
        }
    )

    sessions = sessions.sort_values(
        "session_start"
    ).reset_index(drop=True)

    return sessions, profiles


def validate_sessions(
    sessions: pd.DataFrame,
    machines: pd.DataFrame,
    players: pd.DataFrame,
) -> None:
    """Validate session quality and relationships."""

    if len(sessions) != NUM_SESSIONS:
        raise ValueError(
            f"Expected {NUM_SESSIONS} sessions, "
            f"but found {len(sessions)}."
        )

    if sessions[
        "session_id"
    ].duplicated().any():
        raise ValueError(
            "Duplicate session IDs found."
        )

    if sessions.isna().any().any():
        null_columns = sessions.columns[
            sessions.isna().any()
        ].tolist()

        raise ValueError(
            f"Null values found in: "
            f"{null_columns}"
        )

    if (
        sessions["session_end"]
        <= sessions["session_start"]
    ).any():
        raise ValueError(
            "One or more sessions have "
            "invalid timestamps."
        )

    if (
        sessions[
            "session_duration_minutes"
        ] <= 0
    ).any():
        raise ValueError(
            "Invalid session durations found."
        )

    if (
        sessions["total_rounds"] <= 0
    ).any():
        raise ValueError(
            "Invalid round counts found."
        )

    if (
        sessions["total_wager"] < 0
    ).any():
        raise ValueError(
            "Negative wagers found."
        )

    if (
        sessions["total_payout"] < 0
    ).any():
        raise ValueError(
            "Negative payouts found."
        )

    valid_players = set(
        players["player_id"]
    )

    valid_machines = set(
        machines["machine_id"]
    )

    if not set(
        sessions["player_id"]
    ).issubset(valid_players):
        raise ValueError(
            "Unknown player IDs found in sessions."
        )

    if not set(
        sessions["machine_id"]
    ).issubset(valid_machines):
        raise ValueError(
            "Unknown machine IDs found in sessions."
        )

    machine_location_map = machines.set_index(
        "machine_id"
    )["location_id"]

    expected_locations = sessions[
        "machine_id"
    ].map(machine_location_map)

    if not expected_locations.equals(
        sessions["location_id"]
    ):
        raise ValueError(
            "Machine and location relationships "
            "do not match."
        )


def main() -> None:
    players_path = (
        RAW_DATA_DIR
        / "players.csv"
    )

    machines_path = (
        RAW_DATA_DIR
        / "machines.csv"
    )

    if not players_path.exists():
        raise FileNotFoundError(
            "players.csv was not found. Run "
            "generate_reference_data.py first."
        )

    if not machines_path.exists():
        raise FileNotFoundError(
            "machines.csv was not found. Run "
            "generate_reference_data.py first."
        )

    players = pd.read_csv(
        players_path
    )

    machines = pd.read_csv(
        machines_path
    )

    sessions, profiles = generate_sessions(
        players=players,
        machines=machines,
    )

    validate_sessions(
        sessions=sessions,
        machines=machines,
        players=players,
    )

    session_output_path = (
        RAW_DATA_DIR
        / "player_sessions.csv"
    )

    profile_output_path = (
        RAW_DATA_DIR
        / "player_behavior_profiles.csv"
    )

    sessions.to_csv(
        session_output_path,
        index=False,
    )

    profiles[
        [
            "player_id",
            "loyalty_tier",
            "marketing_opt_in",
            "engagement_score",
            "churn_probability",
            "synthetic_churn_profile",
            "historical_session_count",
            "target_window_session_count",
        ]
    ].to_csv(
        profile_output_path,
        index=False,
    )

    cutoff_date = (
        pd.Timestamp(END_DATE)
        - pd.Timedelta(days=60)
    )

    target_window_players = sessions.loc[
        pd.to_datetime(
            sessions["session_start"]
        ).dt.date
        > cutoff_date.date(),
        "player_id",
    ].nunique()

    profile_churn_count = profiles[
        "synthetic_churn_profile"
    ].sum()

    print(
        "Behavioral player sessions generated "
        "successfully."
    )
    print(
        f"Sessions: {len(sessions):,}"
    )
    print(
        "Unique players:",
        f"{sessions['player_id'].nunique():,}",
    )
    print(
        "Unique machines:",
        f"{sessions['machine_id'].nunique():,}",
    )
    print(
        "Players returning in target window:",
        f"{target_window_players:,}",
    )
    print(
        "Synthetic churn-profile players:",
        f"{profile_churn_count:,}",
    )
    print(
        "Total wager:",
        f"${sessions['total_wager'].sum():,.2f}",
    )
    print(
        "Net gaming revenue:",
        f"${sessions['net_gaming_revenue'].sum():,.2f}",
    )
    print(
        f"Session output: {session_output_path}"
    )
    print(
        f"Behavior profiles: {profile_output_path}"
    )


if __name__ == "__main__":
    main()
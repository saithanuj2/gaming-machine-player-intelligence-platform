import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (
    NUM_TRANSACTIONS,
    RANDOM_SEED,
    RAW_DATA_DIR,
)


np.random.seed(RANDOM_SEED)


def allocate_transactions(
    sessions: pd.DataFrame,
) -> np.ndarray:
    """Allocate transaction counts across player sessions."""

    if NUM_TRANSACTIONS < len(sessions):
        raise ValueError(
            "NUM_TRANSACTIONS must be greater than "
            "or equal to the number of sessions."
        )

    base_transactions = np.ones(
        len(sessions),
        dtype=int,
    )

    remaining_transactions = (
        NUM_TRANSACTIONS - len(sessions)
    )

    session_weights = (
        sessions["total_rounds"]
        / sessions["total_rounds"].sum()
    ).to_numpy()

    additional_transactions = np.random.multinomial(
        remaining_transactions,
        session_weights,
    )

    return base_transactions + additional_transactions


def generate_transactions(
    sessions: pd.DataFrame,
) -> pd.DataFrame:
    """Generate gaming transactions linked to player sessions."""

    session_transaction_counts = allocate_transactions(
        sessions
    )

    repeated_session_indexes = np.repeat(
        sessions.index.to_numpy(),
        session_transaction_counts,
    )

    transaction_sessions = sessions.loc[
        repeated_session_indexes
    ].reset_index(drop=True)

    transaction_positions = (
        transaction_sessions.groupby(
            "session_id"
        ).cumcount()
    )

    transaction_count_map = pd.Series(
        session_transaction_counts,
        index=sessions["session_id"],
    )

    transactions_per_session = (
        transaction_sessions["session_id"]
        .map(transaction_count_map)
        .to_numpy()
    )

    position_fraction = (
        transaction_positions.to_numpy()
        + np.random.random(NUM_TRANSACTIONS)
    ) / transactions_per_session

    session_start = pd.to_datetime(
        transaction_sessions["session_start"]
    )

    session_duration = pd.to_timedelta(
        transaction_sessions[
            "session_duration_minutes"
        ],
        unit="m",
    )

    transaction_timestamp = (
        session_start
        + session_duration * position_fraction
    )

    session_total_wager = (
        transaction_sessions[
            "total_wager"
        ].to_numpy()
    )

    wager_weights = np.random.gamma(
        shape=2.0,
        scale=1.0,
        size=NUM_TRANSACTIONS,
    )

    wager_weight_totals = pd.Series(
        wager_weights
    ).groupby(
        transaction_sessions[
            "session_id"
        ].to_numpy()
    ).transform("sum")

    wager_amount = (
        wager_weights
        / wager_weight_totals.to_numpy()
        * session_total_wager
    )

    wager_amount = np.round(
        wager_amount,
        2,
    )

    session_total_payout = (
        transaction_sessions[
            "total_payout"
        ].to_numpy()
    )

    payout_weights = np.random.gamma(
        shape=1.7,
        scale=1.0,
        size=NUM_TRANSACTIONS,
    )

    payout_weight_totals = pd.Series(
        payout_weights
    ).groupby(
        transaction_sessions[
            "session_id"
        ].to_numpy()
    ).transform("sum")

    payout_amount = (
        payout_weights
        / payout_weight_totals.to_numpy()
        * session_total_payout
    )

    payout_amount = np.round(
        payout_amount,
        2,
    )

    jackpot_flag = (
        np.random.random(NUM_TRANSACTIONS)
        < 0.001
    )

    jackpot_amount = np.where(
        jackpot_flag,
        np.round(
            np.random.uniform(
                100,
                2_500,
                NUM_TRANSACTIONS,
            ),
            2,
        ),
        0.0,
    )

    transactions = pd.DataFrame(
        {
            "transaction_id": np.arange(
                1,
                NUM_TRANSACTIONS + 1,
            ),
            "session_id": transaction_sessions[
                "session_id"
            ].to_numpy(),
            "player_id": transaction_sessions[
                "player_id"
            ].to_numpy(),
            "machine_id": transaction_sessions[
                "machine_id"
            ].to_numpy(),
            "location_id": transaction_sessions[
                "location_id"
            ].to_numpy(),
            "transaction_timestamp": (
                transaction_timestamp
            ),
            "wager_amount": wager_amount,
            "payout_amount": payout_amount,
            "jackpot_amount": jackpot_amount,
        }
    )

    # The session payout already includes all player winnings.
    # Jackpot amount is tracked separately for analysis only,
    # so it must not be subtracted again.
    transactions[
        "net_gaming_revenue"
    ] = (
        transactions["wager_amount"]
        - transactions["payout_amount"]
    ).round(2)

    transactions[
        "transaction_type"
    ] = np.where(
        transactions["jackpot_amount"] > 0,
        "Jackpot",
        np.where(
            transactions["payout_amount"]
            > transactions["wager_amount"],
            "Winning Round",
            "Standard Round",
        ),
    )

    return transactions.sort_values(
        "transaction_timestamp"
    ).reset_index(drop=True)


def validate_transactions(
    transactions: pd.DataFrame,
    sessions: pd.DataFrame,
) -> None:
    """Validate transaction quality and relationships."""

    if len(transactions) != NUM_TRANSACTIONS:
        raise ValueError(
            f"Expected {NUM_TRANSACTIONS} "
            f"transactions but found "
            f"{len(transactions)}."
        )

    if transactions[
        "transaction_id"
    ].duplicated().any():
        raise ValueError(
            "Duplicate transaction IDs found."
        )

    if transactions.isna().any().any():
        columns_with_nulls = (
            transactions.columns[
                transactions.isna().any()
            ].tolist()
        )

        raise ValueError(
            f"Null values found in: "
            f"{columns_with_nulls}"
        )

    if (
        transactions["wager_amount"] < 0
    ).any():
        raise ValueError(
            "Negative wager values found."
        )

    if (
        transactions["payout_amount"] < 0
    ).any():
        raise ValueError(
            "Negative payout values found."
        )

    if (
        transactions["jackpot_amount"] < 0
    ).any():
        raise ValueError(
            "Negative jackpot values found."
        )

    valid_sessions = set(
        sessions["session_id"]
    )

    if not set(
        transactions["session_id"]
    ).issubset(valid_sessions):
        raise ValueError(
            "Unknown session IDs found."
        )

    session_relationships = sessions.set_index(
        "session_id"
    )[
        [
            "player_id",
            "machine_id",
            "location_id",
        ]
    ]

    merged = transactions.merge(
        session_relationships,
        left_on="session_id",
        right_index=True,
        suffixes=("", "_expected"),
    )

    for column in [
        "player_id",
        "machine_id",
        "location_id",
    ]:
        if not (
            merged[column]
            == merged[f"{column}_expected"]
        ).all():
            raise ValueError(
                f"Invalid {column} relationships."
            )

    transaction_revenue = round(
        transactions[
            "net_gaming_revenue"
        ].sum(),
        2,
    )

    session_revenue = round(
        sessions[
            "net_gaming_revenue"
        ].sum(),
        2,
    )

    revenue_difference = abs(
        transaction_revenue
        - session_revenue
    )

    if revenue_difference > 5:
        raise ValueError(
            "Transaction revenue does not reconcile "
            "with session revenue. "
            f"Difference: ${revenue_difference:,.2f}"
        )


def main() -> None:
    sessions_path = (
        RAW_DATA_DIR
        / "player_sessions.csv"
    )

    if not sessions_path.exists():
        raise FileNotFoundError(
            "player_sessions.csv was not found. "
            "Run generate_sessions.py first."
        )

    sessions = pd.read_csv(
        sessions_path,
        parse_dates=[
            "session_start",
            "session_end",
        ],
    )

    transactions = generate_transactions(
        sessions
    )

    validate_transactions(
        transactions,
        sessions,
    )

    output_path = (
        RAW_DATA_DIR
        / "gaming_transactions.csv"
    )

    transactions.to_csv(
        output_path,
        index=False,
    )

    session_revenue = round(
        sessions[
            "net_gaming_revenue"
        ].sum(),
        2,
    )

    transaction_revenue = round(
        transactions[
            "net_gaming_revenue"
        ].sum(),
        2,
    )

    revenue_difference = round(
        transaction_revenue
        - session_revenue,
        2,
    )

    print(
        "Gaming transactions generated "
        "successfully."
    )
    print(
        f"Transactions: "
        f"{len(transactions):,}"
    )
    print(
        "Unique sessions:",
        f"{transactions['session_id'].nunique():,}",
    )
    print(
        "Total wager:",
        f"${transactions['wager_amount'].sum():,.2f}",
    )
    print(
        "Total payout:",
        f"${transactions['payout_amount'].sum():,.2f}",
    )
    print(
        "Jackpot amount:",
        f"${transactions['jackpot_amount'].sum():,.2f}",
    )
    print(
        "Transaction revenue:",
        f"${transaction_revenue:,.2f}",
    )
    print(
        "Session revenue:",
        f"${session_revenue:,.2f}",
    )
    print(
        "Revenue difference:",
        f"${revenue_difference:,.2f}",
    )
    print(
        "Jackpot transactions:",
        f"{(transactions['jackpot_amount'] > 0).sum():,}",
    )
    print(f"Output file: {output_path}")


if __name__ == "__main__":
    main()

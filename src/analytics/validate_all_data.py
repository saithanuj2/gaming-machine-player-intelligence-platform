import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import RAW_DATA_DIR


def load_data() -> dict[str, pd.DataFrame]:
    """Load all generated CSV files."""

    file_map = {
        "locations": "locations.csv",
        "machines": "machines.csv",
        "players": "players.csv",
        "sessions": "player_sessions.csv",
        "transactions": "gaming_transactions.csv",
        "events": "machine_events.csv",
    }

    datasets = {}

    for dataset_name, filename in file_map.items():
        file_path = RAW_DATA_DIR / filename

        if not file_path.exists():
            raise FileNotFoundError(
                f"Missing required file: {file_path}"
            )

        datasets[dataset_name] = pd.read_csv(
            file_path
        )

    return datasets


def validate_primary_keys(
    datasets: dict[str, pd.DataFrame],
) -> None:
    """Validate uniqueness and nulls in primary identifiers."""

    primary_keys = {
        "locations": "location_id",
        "machines": "machine_id",
        "players": "player_id",
        "sessions": "session_id",
        "transactions": "transaction_id",
        "events": "event_id",
    }

    for dataset_name, primary_key in primary_keys.items():
        dataframe = datasets[dataset_name]

        if dataframe[primary_key].isna().any():
            raise ValueError(
                f"Null values found in "
                f"{dataset_name}.{primary_key}"
            )

        if dataframe[primary_key].duplicated().any():
            raise ValueError(
                f"Duplicate values found in "
                f"{dataset_name}.{primary_key}"
            )


def validate_relationships(
    datasets: dict[str, pd.DataFrame],
) -> None:
    """Validate foreign-key-style relationships across files."""

    locations = datasets["locations"]
    machines = datasets["machines"]
    players = datasets["players"]
    sessions = datasets["sessions"]
    transactions = datasets["transactions"]
    events = datasets["events"]

    valid_locations = set(
        locations["location_id"]
    )

    valid_machines = set(
        machines["machine_id"]
    )

    valid_players = set(
        players["player_id"]
    )

    valid_sessions = set(
        sessions["session_id"]
    )

    if not set(
        machines["location_id"]
    ).issubset(valid_locations):
        raise ValueError(
            "Machines contain invalid location IDs."
        )

    if not set(
        sessions["location_id"]
    ).issubset(valid_locations):
        raise ValueError(
            "Sessions contain invalid location IDs."
        )

    if not set(
        sessions["machine_id"]
    ).issubset(valid_machines):
        raise ValueError(
            "Sessions contain invalid machine IDs."
        )

    if not set(
        sessions["player_id"]
    ).issubset(valid_players):
        raise ValueError(
            "Sessions contain invalid player IDs."
        )

    if not set(
        transactions["session_id"]
    ).issubset(valid_sessions):
        raise ValueError(
            "Transactions contain invalid session IDs."
        )

    if not set(
        transactions["machine_id"]
    ).issubset(valid_machines):
        raise ValueError(
            "Transactions contain invalid machine IDs."
        )

    if not set(
        transactions["player_id"]
    ).issubset(valid_players):
        raise ValueError(
            "Transactions contain invalid player IDs."
        )

    if not set(
        events["machine_id"]
    ).issubset(valid_machines):
        raise ValueError(
            "Events contain invalid machine IDs."
        )

    machine_location_map = machines.set_index(
        "machine_id"
    )["location_id"]

    expected_session_locations = sessions[
        "machine_id"
    ].map(machine_location_map)

    if not expected_session_locations.equals(
        sessions["location_id"]
    ):
        raise ValueError(
            "Session machine-location relationships "
            "are invalid."
        )

    expected_event_locations = events[
        "machine_id"
    ].map(machine_location_map)

    if not expected_event_locations.equals(
        events["location_id"]
    ):
        raise ValueError(
            "Event machine-location relationships "
            "are invalid."
        )


def validate_financial_data(
    datasets: dict[str, pd.DataFrame],
) -> None:
    """Validate wagers, payouts, revenue, and reconciliation."""

    sessions = datasets["sessions"]
    transactions = datasets["transactions"]

    financial_columns = [
        "total_wager",
        "total_payout",
    ]

    for column in financial_columns:
        if (sessions[column] < 0).any():
            raise ValueError(
                f"Negative session values found in {column}."
            )

    transaction_financial_columns = [
        "wager_amount",
        "payout_amount",
        "jackpot_amount",
    ]

    for column in transaction_financial_columns:
        if (transactions[column] < 0).any():
            raise ValueError(
                f"Negative transaction values found "
                f"in {column}."
            )

    calculated_session_revenue = (
        sessions["total_wager"]
        - sessions["total_payout"]
    ).round(2)

    session_revenue_difference = (
        calculated_session_revenue
        - sessions["net_gaming_revenue"]
    ).abs()

    if session_revenue_difference.max() > 0.02:
        raise ValueError(
            "Session revenue calculations do not match."
        )

    calculated_transaction_revenue = (
        transactions["wager_amount"]
        - transactions["payout_amount"]
    ).round(2)

    transaction_revenue_difference = (
        calculated_transaction_revenue
        - transactions["net_gaming_revenue"]
    ).abs()

    if transaction_revenue_difference.max() > 0.02:
        raise ValueError(
            "Transaction revenue calculations do not match."
        )

    total_session_revenue = round(
        sessions["net_gaming_revenue"].sum(),
        2,
    )

    total_transaction_revenue = round(
        transactions["net_gaming_revenue"].sum(),
        2,
    )

    reconciliation_difference = abs(
        total_session_revenue
        - total_transaction_revenue
    )

    if reconciliation_difference > 5:
        raise ValueError(
            "Session and transaction revenue do not "
            "reconcile. Difference: "
            f"${reconciliation_difference:,.2f}"
        )


def validate_timestamps(
    datasets: dict[str, pd.DataFrame],
) -> None:
    """Validate session and transaction timestamp ranges."""

    sessions = datasets["sessions"].copy()
    transactions = datasets["transactions"].copy()

    sessions["session_start"] = pd.to_datetime(
        sessions["session_start"]
    )

    sessions["session_end"] = pd.to_datetime(
        sessions["session_end"]
    )

    transactions["transaction_timestamp"] = (
        pd.to_datetime(
            transactions["transaction_timestamp"]
        )
    )

    if (
        sessions["session_end"]
        <= sessions["session_start"]
    ).any():
        raise ValueError(
            "Invalid session start and end timestamps."
        )

    session_times = sessions.set_index(
        "session_id"
    )[
        [
            "session_start",
            "session_end",
        ]
    ]

    merged = transactions.merge(
        session_times,
        left_on="session_id",
        right_index=True,
    )

    outside_session = (
        merged["transaction_timestamp"]
        < merged["session_start"]
    ) | (
        merged["transaction_timestamp"]
        > merged["session_end"]
    )

    if outside_session.any():
        raise ValueError(
            "Transactions found outside their "
            "associated session times."
        )


def print_summary(
    datasets: dict[str, pd.DataFrame],
) -> None:
    """Print project data-quality summary."""

    sessions = datasets["sessions"]
    transactions = datasets["transactions"]
    events = datasets["events"]

    print("\nDATA QUALITY VALIDATION PASSED")
    print("-" * 45)

    for dataset_name, dataframe in datasets.items():
        print(
            f"{dataset_name.title():15}: "
            f"{len(dataframe):,} rows"
        )

    print("-" * 45)

    print(
        "Session revenue:",
        f"${sessions['net_gaming_revenue'].sum():,.2f}",
    )

    print(
        "Transaction revenue:",
        f"${transactions['net_gaming_revenue'].sum():,.2f}",
    )

    print(
        "Total machine downtime:",
        f"{events['downtime_minutes'].sum():,} minutes",
    )

    print(
        "Critical events:",
        f"{(events['severity'] == 'Critical').sum():,}",
    )

    print(
        "Events requiring investigation:",
        f"{events['requires_investigation'].sum():,}",
    )


def main() -> None:
    datasets = load_data()

    validate_primary_keys(datasets)
    validate_relationships(datasets)
    validate_financial_data(datasets)
    validate_timestamps(datasets)

    print_summary(datasets)


if __name__ == "__main__":
    main()
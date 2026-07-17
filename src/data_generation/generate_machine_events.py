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
    NUM_MACHINE_EVENTS,
    RANDOM_SEED,
    RAW_DATA_DIR,
    START_DATE,
)


random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)


EVENT_CONFIG = {
    "Door Open": {
        "severity": ["Low", "Medium"],
        "severity_weights": [0.88, 0.12],
        "downtime_range": (0, 8),
        "error_prefix": "DR",
    },
    "Cash Refill": {
        "severity": ["Low"],
        "severity_weights": [1.0],
        "downtime_range": (3, 15),
        "error_prefix": "CR",
    },
    "Ticket Jam": {
        "severity": ["Medium", "High"],
        "severity_weights": [0.85, 0.15],
        "downtime_range": (5, 35),
        "error_prefix": "TJ",
    },
    "Printer Error": {
        "severity": ["Medium", "High"],
        "severity_weights": [0.82, 0.18],
        "downtime_range": (5, 40),
        "error_prefix": "PR",
    },
    "Hopper Empty": {
        "severity": ["Medium"],
        "severity_weights": [1.0],
        "downtime_range": (5, 25),
        "error_prefix": "HP",
    },
    "Bill Acceptor Error": {
        "severity": ["Medium", "High"],
        "severity_weights": [0.78, 0.22],
        "downtime_range": (8, 45),
        "error_prefix": "BA",
    },
    "Communication Loss": {
        "severity": ["Medium", "High", "Critical"],
        "severity_weights": [0.68, 0.27, 0.05],
        "downtime_range": (10, 120),
        "error_prefix": "CM",
    },
    "Software Restart": {
        "severity": ["Low", "Medium"],
        "severity_weights": [0.72, 0.28],
        "downtime_range": (2, 20),
        "error_prefix": "SR",
    },
    "Software Upgrade": {
        "severity": ["Low", "Medium"],
        "severity_weights": [0.85, 0.15],
        "downtime_range": (15, 60),
        "error_prefix": "SU",
    },
    "Preventive Maintenance": {
        "severity": ["Low", "Medium"],
        "severity_weights": [0.88, 0.12],
        "downtime_range": (20, 90),
        "error_prefix": "PM",
    },
    "Hardware Failure": {
        "severity": ["High", "Critical"],
        "severity_weights": [0.72, 0.28],
        "downtime_range": (30, 240),
        "error_prefix": "HF",
    },
    "Power Failure": {
        "severity": ["High", "Critical"],
        "severity_weights": [0.70, 0.30],
        "downtime_range": (15, 180),
        "error_prefix": "PF",
    },
}


PLANNED_EVENT_TYPES = {
    "Software Upgrade",
    "Preventive Maintenance",
    "Cash Refill",
}

QUALIFYING_FAILURE_TYPES = {
    "Hardware Failure",
    "Power Failure",
    "Communication Loss",
}

HEALTHY_EVENT_WEIGHTS = {
    "Door Open": 0.22,
    "Cash Refill": 0.18,
    "Ticket Jam": 0.07,
    "Printer Error": 0.07,
    "Hopper Empty": 0.07,
    "Bill Acceptor Error": 0.06,
    "Communication Loss": 0.04,
    "Software Restart": 0.10,
    "Software Upgrade": 0.07,
    "Preventive Maintenance": 0.10,
    "Hardware Failure": 0.01,
    "Power Failure": 0.01,
}

WARNING_EVENT_WEIGHTS = {
    "Door Open": 0.10,
    "Cash Refill": 0.07,
    "Ticket Jam": 0.13,
    "Printer Error": 0.13,
    "Hopper Empty": 0.08,
    "Bill Acceptor Error": 0.12,
    "Communication Loss": 0.15,
    "Software Restart": 0.10,
    "Software Upgrade": 0.03,
    "Preventive Maintenance": 0.06,
    "Hardware Failure": 0.02,
    "Power Failure": 0.01,
}

HIGH_RISK_EVENT_WEIGHTS = {
    "Door Open": 0.05,
    "Cash Refill": 0.04,
    "Ticket Jam": 0.13,
    "Printer Error": 0.13,
    "Hopper Empty": 0.06,
    "Bill Acceptor Error": 0.13,
    "Communication Loss": 0.21,
    "Software Restart": 0.08,
    "Software Upgrade": 0.02,
    "Preventive Maintenance": 0.04,
    "Hardware Failure": 0.08,
    "Power Failure": 0.03,
}


def weighted_choice(weight_map: dict[str, float]) -> str:
    """Select one value from a weighted dictionary."""

    values = list(weight_map.keys())
    weights = list(weight_map.values())

    return random.choices(
        population=values,
        weights=weights,
        k=1,
    )[0]


def generate_timestamps(
    start_timestamp: pd.Timestamp,
    end_timestamp: pd.Timestamp,
    number_of_records: int,
    recent_bias: float = 1.0,
) -> pd.DatetimeIndex:
    """Generate timestamps with optional bias toward recent dates."""

    if number_of_records <= 0:
        return pd.DatetimeIndex([])

    if end_timestamp <= start_timestamp:
        raise ValueError(
            "Timestamp range must have a positive duration."
        )

    if recent_bias > 1:
        fractions = np.random.beta(
            a=recent_bias,
            b=1.35,
            size=number_of_records,
        )
    else:
        fractions = np.random.random(
            number_of_records
        )

    total_seconds = int(
        (
            end_timestamp
            - start_timestamp
        ).total_seconds()
    )

    offsets = (
        fractions * total_seconds
    ).astype(np.int64)

    return pd.DatetimeIndex(
        start_timestamp
        + pd.to_timedelta(
            offsets,
            unit="s",
        )
    )


def assign_machine_profiles(
    machines: pd.DataFrame,
) -> pd.DataFrame:
    """
    Assign controlled machine-health profiles.

    Approximately 32% of machines are future-failure machines.
    """

    eligible = machines.loc[
        machines["machine_status"].isin(
            ["Active", "Maintenance"]
        ),
        [
            "machine_id",
            "location_id",
            "software_version",
            "manufacturer",
            "install_date",
        ],
    ].copy()

    if eligible.empty:
        raise ValueError(
            "No eligible machines were found."
        )

    machine_count = len(eligible)

    failure_machine_count = max(
        1,
        round(machine_count * 0.32),
    )

    warning_machine_count = max(
        1,
        round(machine_count * 0.33),
    )

    shuffled_indexes = np.random.permutation(
        eligible.index
    )

    failure_indexes = shuffled_indexes[
        :failure_machine_count
    ]

    warning_indexes = shuffled_indexes[
        failure_machine_count:
        failure_machine_count
        + warning_machine_count
    ]

    eligible["health_profile"] = "Healthy"

    eligible.loc[
        warning_indexes,
        "health_profile",
    ] = "Warning"

    eligible.loc[
        failure_indexes,
        "health_profile",
    ] = "High Risk"

    eligible["future_failure_machine"] = (
        eligible["health_profile"]
        == "High Risk"
    ).astype(int)

    profile_multiplier = {
        "Healthy": 0.70,
        "Warning": 1.05,
        "High Risk": 1.40,
    }

    eligible["event_weight"] = (
        eligible["health_profile"]
        .map(profile_multiplier)
        .astype(float)
    )

    return eligible.reset_index(drop=True)


def allocate_event_counts(
    profiles: pd.DataFrame,
) -> np.ndarray:
    """Allocate the total event volume across machine profiles."""

    base_counts = np.full(
        len(profiles),
        10,
        dtype=int,
    )

    base_total = int(base_counts.sum())

    if base_total > NUM_MACHINE_EVENTS:
        raise ValueError(
            "NUM_MACHINE_EVENTS is too small."
        )

    remaining_events = (
        NUM_MACHINE_EVENTS - base_total
    )

    weights = profiles[
        "event_weight"
    ].to_numpy()

    weights = weights / weights.sum()

    additional_counts = np.random.multinomial(
        remaining_events,
        weights,
    )

    return base_counts + additional_counts


def assign_severity(
    event_type: str,
    health_profile: str,
    target_window: bool,
) -> str:
    """Assign severity using machine health and event timing."""

    if (
        target_window
        and health_profile != "High Risk"
    ):
        if event_type in QUALIFYING_FAILURE_TYPES:
            return "Medium"

    if (
        target_window
        and health_profile == "High Risk"
        and event_type in QUALIFYING_FAILURE_TYPES
    ):
        return random.choices(
            ["High", "Critical"],
            weights=[0.72, 0.28],
            k=1,
        )[0]

    config = EVENT_CONFIG[event_type]

    severity = random.choices(
        population=config["severity"],
        weights=config["severity_weights"],
        k=1,
    )[0]

    if health_profile == "Healthy":
        if severity == "Critical":
            return "Medium"

        if severity == "High":
            return random.choices(
                ["Medium", "High"],
                weights=[0.90, 0.10],
                k=1,
            )[0]

    if health_profile == "Warning":
        if severity == "Critical":
            return random.choices(
                ["High", "Critical"],
                weights=[0.88, 0.12],
                k=1,
            )[0]

    return severity


def assign_downtime(
    event_type: str,
    severity: str,
    health_profile: str,
) -> int:
    """Assign downtime based on event, severity, and profile."""

    minimum, maximum = EVENT_CONFIG[
        event_type
    ]["downtime_range"]

    severity_multiplier = {
        "Low": 0.40,
        "Medium": 0.65,
        "High": 0.88,
        "Critical": 1.00,
    }[severity]

    profile_multiplier = {
        "Healthy": 0.75,
        "Warning": 1.00,
        "High Risk": 1.20,
    }[health_profile]

    adjusted_maximum = max(
        minimum,
        int(
            maximum
            * severity_multiplier
            * profile_multiplier
        ),
    )

    return random.randint(
        minimum,
        adjusted_maximum,
    )


def build_error_code(
    event_type: str,
) -> str:
    """Create an event-specific error code."""

    prefix = EVENT_CONFIG[
        event_type
    ]["error_prefix"]

    return (
        f"{prefix}-"
        f"{random.randint(100, 999)}"
    )


def select_event_type(
    health_profile: str,
    target_window: bool,
) -> str:
    """Select a profile-specific event type."""

    if health_profile == "Healthy":
        weight_map = HEALTHY_EVENT_WEIGHTS

    elif health_profile == "Warning":
        weight_map = WARNING_EVENT_WEIGHTS

    else:
        weight_map = HIGH_RISK_EVENT_WEIGHTS

    event_type = weighted_choice(
        weight_map
    )

    if (
        target_window
        and health_profile != "High Risk"
        and event_type in {
            "Hardware Failure",
            "Power Failure",
        }
    ):
        event_type = random.choice(
            [
                "Ticket Jam",
                "Printer Error",
                "Software Restart",
                "Preventive Maintenance",
            ]
        )

    return event_type


def create_machine_event_records(
    machine: pd.Series,
    event_count: int,
    observation_cutoff: pd.Timestamp,
    dataset_end: pd.Timestamp,
) -> list[dict]:
    """Generate events for one machine."""

    profile = machine[
        "health_profile"
    ]

    if profile == "Healthy":
        target_window_ratio = 0.06
        recent_bias = 1.00

    elif profile == "Warning":
        target_window_ratio = 0.10
        recent_bias = 1.35

    else:
        target_window_ratio = 0.14
        recent_bias = 1.75

    target_event_count = max(
        1,
        round(
            event_count
            * target_window_ratio
        ),
    )

    historical_event_count = (
        event_count
        - target_event_count
    )

    project_start = pd.Timestamp(
        START_DATE
    )

    historical_end = (
        observation_cutoff
        + pd.Timedelta(
            hours=23,
            minutes=59,
        )
    )

    target_start = (
        observation_cutoff
        + pd.Timedelta(days=1)
    )

    target_end = (
        dataset_end
        + pd.Timedelta(
            hours=23,
            minutes=59,
        )
    )

    historical_timestamps = generate_timestamps(
        start_timestamp=project_start,
        end_timestamp=historical_end,
        number_of_records=(
            historical_event_count
        ),
        recent_bias=recent_bias,
    )

    target_timestamps = generate_timestamps(
        start_timestamp=target_start,
        end_timestamp=target_end,
        number_of_records=(
            target_event_count
        ),
        recent_bias=1.50,
    )

    records = []

    for timestamp in historical_timestamps:
        event_type = select_event_type(
            health_profile=profile,
            target_window=False,
        )

        severity = assign_severity(
            event_type=event_type,
            health_profile=profile,
            target_window=False,
        )

        records.append(
            {
                "machine_id": machine[
                    "machine_id"
                ],
                "location_id": machine[
                    "location_id"
                ],
                "event_timestamp": timestamp,
                "event_type": event_type,
                "severity": severity,
                "downtime_minutes": (
                    assign_downtime(
                        event_type,
                        severity,
                        profile,
                    )
                ),
                "software_version": machine[
                    "software_version"
                ],
                "error_code": build_error_code(
                    event_type
                ),
                "health_profile": profile,
                "future_failure_machine": int(
                    machine[
                        "future_failure_machine"
                    ]
                ),
            }
        )

    target_records = []

    for timestamp in target_timestamps:
        event_type = select_event_type(
            health_profile=profile,
            target_window=True,
        )

        severity = assign_severity(
            event_type=event_type,
            health_profile=profile,
            target_window=True,
        )

        target_records.append(
            {
                "machine_id": machine[
                    "machine_id"
                ],
                "location_id": machine[
                    "location_id"
                ],
                "event_timestamp": timestamp,
                "event_type": event_type,
                "severity": severity,
                "downtime_minutes": (
                    assign_downtime(
                        event_type,
                        severity,
                        profile,
                    )
                ),
                "software_version": machine[
                    "software_version"
                ],
                "error_code": build_error_code(
                    event_type
                ),
                "health_profile": profile,
                "future_failure_machine": int(
                    machine[
                        "future_failure_machine"
                    ]
                ),
            }
        )

    if profile == "High Risk":
        failure_index = random.randrange(
            len(target_records)
        )

        target_records[
            failure_index
        ]["event_type"] = random.choice(
            [
                "Hardware Failure",
                "Power Failure",
                "Communication Loss",
            ]
        )

        target_records[
            failure_index
        ]["severity"] = random.choices(
            ["High", "Critical"],
            weights=[0.70, 0.30],
            k=1,
        )[0]

        failure_type = target_records[
            failure_index
        ]["event_type"]

        failure_severity = target_records[
            failure_index
        ]["severity"]

        target_records[
            failure_index
        ]["downtime_minutes"] = (
            assign_downtime(
                failure_type,
                failure_severity,
                profile,
            )
        )

        target_records[
            failure_index
        ]["error_code"] = (
            build_error_code(
                failure_type
            )
        )

    records.extend(
        target_records
    )

    return records


def generate_machine_events(
    machines: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate controlled machine-health events."""

    profiles = assign_machine_profiles(
        machines
    )

    event_counts = allocate_event_counts(
        profiles
    )

    profiles[
        "allocated_event_count"
    ] = event_counts

    dataset_end = pd.Timestamp(
        END_DATE
    )

    observation_cutoff = (
        dataset_end
        - pd.Timedelta(days=30)
    )

    event_records = []

    for machine_row in profiles.itertuples(
        index=False
    ):
        machine_series = pd.Series(
            machine_row._asdict()
        )

        event_records.extend(
            create_machine_event_records(
                machine=machine_series,
                event_count=int(
                    machine_series[
                        "allocated_event_count"
                    ]
                ),
                observation_cutoff=(
                    observation_cutoff
                ),
                dataset_end=dataset_end,
            )
        )

    events = pd.DataFrame(
        event_records
    )

    if len(events) != NUM_MACHINE_EVENTS:
        raise ValueError(
            f"Expected {NUM_MACHINE_EVENTS} events "
            f"but generated {len(events)}."
        )

    events = events.sort_values(
        [
            "event_timestamp",
            "machine_id",
        ]
    ).reset_index(drop=True)

    events["event_id"] = np.arange(
        1,
        len(events) + 1,
    )

    events["event_date"] = pd.to_datetime(
        events["event_timestamp"]
    ).dt.date

    events[
        "requires_investigation"
    ] = events["severity"].isin(
        ["High", "Critical"]
    ).astype(int)

    events[
        "planned_event_flag"
    ] = events["event_type"].isin(
        PLANNED_EVENT_TYPES
    ).astype(int)

    csv_columns = [
        "event_id",
        "machine_id",
        "location_id",
        "event_timestamp",
        "event_type",
        "severity",
        "downtime_minutes",
        "software_version",
        "error_code",
        "event_date",
        "requires_investigation",
        "planned_event_flag",
    ]

    return events[csv_columns], profiles


def validate_machine_events(
    events: pd.DataFrame,
    machines: pd.DataFrame,
) -> None:
    """Validate generated machine-event data."""

    if len(events) != NUM_MACHINE_EVENTS:
        raise ValueError(
            f"Expected {NUM_MACHINE_EVENTS} events "
            f"but found {len(events)}."
        )

    if events[
        "event_id"
    ].duplicated().any():
        raise ValueError(
            "Duplicate event IDs found."
        )

    if events.isna().any().any():
        null_columns = events.columns[
            events.isna().any()
        ].tolist()

        raise ValueError(
            f"Null values found in: "
            f"{null_columns}"
        )

    if (
        events["downtime_minutes"] < 0
    ).any():
        raise ValueError(
            "Negative downtime values found."
        )

    valid_machines = set(
        machines["machine_id"]
    )

    if not set(
        events["machine_id"]
    ).issubset(valid_machines):
        raise ValueError(
            "Unknown machine IDs found."
        )

    machine_location_map = machines.set_index(
        "machine_id"
    )["location_id"]

    expected_locations = events[
        "machine_id"
    ].map(machine_location_map)

    if not expected_locations.equals(
        events["location_id"]
    ):
        raise ValueError(
            "Machine-location relationships "
            "do not match."
        )

    valid_severities = {
        "Low",
        "Medium",
        "High",
        "Critical",
    }

    if not set(
        events["severity"]
    ).issubset(valid_severities):
        raise ValueError(
            "Unexpected severity values found."
        )

    expected_investigation = (
        events["severity"].isin(
            ["High", "Critical"]
        )
    ).astype(int)

    if not expected_investigation.equals(
        events[
            "requires_investigation"
        ]
    ):
        raise ValueError(
            "Investigation flags do not match "
            "event severity."
        )


def main() -> None:
    machines_path = (
        RAW_DATA_DIR
        / "machines.csv"
    )

    if not machines_path.exists():
        raise FileNotFoundError(
            "machines.csv was not found. Run "
            "generate_reference_data.py first."
        )

    machines = pd.read_csv(
        machines_path
    )

    events, profiles = (
        generate_machine_events(
            machines
        )
    )

    validate_machine_events(
        events,
        machines,
    )

    event_output_path = (
        RAW_DATA_DIR
        / "machine_events.csv"
    )

    profile_output_path = (
        RAW_DATA_DIR
        / "machine_health_profiles.csv"
    )

    events.to_csv(
        event_output_path,
        index=False,
    )

    profiles[
        [
            "machine_id",
            "location_id",
            "software_version",
            "health_profile",
            "future_failure_machine",
            "allocated_event_count",
        ]
    ].to_csv(
        profile_output_path,
        index=False,
    )

    cutoff_date = (
        pd.Timestamp(END_DATE)
        - pd.Timedelta(days=30)
    ).date()

    future_failure_machines = (
        events.loc[
            (
                pd.to_datetime(
                    events["event_date"]
                ).dt.date
                > cutoff_date
            )
            & (
                events[
                    "planned_event_flag"
                ] == 0
            )
            & (
                events["severity"].isin(
                    ["High", "Critical"]
                )
            ),
            "machine_id",
        ]
        .nunique()
    )

    print(
        "Controlled machine events generated "
        "successfully."
    )

    print(
        f"Events: {len(events):,}"
    )

    print(
        "Unique machines:",
        f"{events['machine_id'].nunique():,}",
    )

    print(
        "Healthy-profile machines:",
        f"{(profiles['health_profile'] == 'Healthy').sum():,}",
    )

    print(
        "Warning-profile machines:",
        f"{(profiles['health_profile'] == 'Warning').sum():,}",
    )

    print(
        "High-risk profile machines:",
        f"{(profiles['health_profile'] == 'High Risk').sum():,}",
    )

    print(
        "Machines with qualifying future failures:",
        f"{future_failure_machines:,}",
    )

    print(
        "Critical events:",
        f"{(events['severity'] == 'Critical').sum():,}",
    )

    print(
        "Planned events:",
        f"{events['planned_event_flag'].sum():,}",
    )

    print(
        "Unplanned events:",
        f"{(events['planned_event_flag'] == 0).sum():,}",
    )

    print(
        "Total downtime:",
        f"{events['downtime_minutes'].sum():,} minutes",
    )

    print(
        "Average downtime:",
        f"{events['downtime_minutes'].mean():,.2f} minutes",
    )

    print(
        "Events requiring investigation:",
        f"{events['requires_investigation'].sum():,}",
    )

    print(
        f"Event output: {event_output_path}"
    )

    print(
        f"Machine profiles: {profile_output_path}"
    )


if __name__ == "__main__":
    main()
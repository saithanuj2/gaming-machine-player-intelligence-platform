import random
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (
    NUM_LOCATIONS,
    NUM_MACHINES,
    NUM_PLAYERS,
    RANDOM_SEED,
    RAW_DATA_DIR,
)


fake = Faker()
Faker.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)


def generate_locations() -> pd.DataFrame:
    """Generate synthetic gaming location records."""

    regions = [
        "Northeast",
        "Southeast",
        "Midwest",
        "Southwest",
        "West",
    ]

    location_types = [
        "Casino",
        "Bar",
        "Restaurant",
        "Route Location",
        "Entertainment Center",
    ]

    records = []

    for location_number in range(1, NUM_LOCATIONS + 1):
        records.append(
            {
                "location_id": f"LOC{location_number:04d}",
                "location_name": f"{fake.city()} Gaming Center",
                "city": fake.city(),
                "state": fake.state_abbr(),
                "region": random.choice(regions),
                "route_manager": fake.name(),
                "location_type": random.choice(location_types),
                "opening_date": fake.date_between(
                    start_date="-10y",
                    end_date="-1y",
                ),
                "active_flag": 1,
            }
        )

    return pd.DataFrame(records)


def generate_machines(locations: pd.DataFrame) -> pd.DataFrame:
    """Generate synthetic gaming machine records."""

    manufacturers = [
        "IGT",
        "Aristocrat",
        "Light & Wonder",
        "Konami",
        "Everi",
    ]

    cabinet_types = [
        "Standard",
        "Upright",
        "Slant Top",
        "Premium",
    ]

    game_categories = [
        "Video Slots",
        "Reel Slots",
        "Video Poker",
    ]

    software_versions = [
        "v4.1",
        "v4.2",
        "v5.0",
        "v5.1",
    ]

    location_ids = locations["location_id"].tolist()
    records = []

    for machine_number in range(1, NUM_MACHINES + 1):
        records.append(
            {
                "machine_id": f"MCH{machine_number:06d}",
                "location_id": random.choice(location_ids),
                "manufacturer": random.choice(manufacturers),
                "cabinet_type": random.choice(cabinet_types),
                "game_title": f"Game {random.randint(1, 50):03d}",
                "game_category": random.choice(game_categories),
                "install_date": fake.date_between(
                    start_date="-8y",
                    end_date="-30d",
                ),
                "software_version": random.choice(software_versions),
                "machine_status": random.choices(
                    population=[
                        "Active",
                        "Maintenance",
                        "Inactive",
                    ],
                    weights=[0.93, 0.05, 0.02],
                    k=1,
                )[0],
                "theoretical_hold_pct": round(
                    np.random.uniform(0.05, 0.14),
                    4,
                ),
            }
        )

    return pd.DataFrame(records)


def generate_players() -> pd.DataFrame:
    """Generate synthetic loyalty-player records."""

    loyalty_tiers = [
        "Standard",
        "Silver",
        "Gold",
        "Platinum",
    ]

    age_bands = [
        "21-29",
        "30-39",
        "40-49",
        "50-59",
        "60+",
    ]

    home_regions = [
        "Northeast",
        "Southeast",
        "Midwest",
        "Southwest",
        "West",
    ]

    records = []

    for player_number in range(1, NUM_PLAYERS + 1):
        records.append(
            {
                "player_id": f"PLY{player_number:08d}",
                "enrollment_date": fake.date_between(
                    start_date="-5y",
                    end_date="-30d",
                ),
                "loyalty_tier": random.choices(
                    population=loyalty_tiers,
                    weights=[0.55, 0.25, 0.15, 0.05],
                    k=1,
                )[0],
                "age_band": random.choice(age_bands),
                "home_region": random.choice(home_regions),
                "marketing_opt_in": random.choices(
                    population=[1, 0],
                    weights=[0.72, 0.28],
                    k=1,
                )[0],
                "active_flag": random.choices(
                    population=[1, 0],
                    weights=[0.94, 0.06],
                    k=1,
                )[0],
            }
        )

    return pd.DataFrame(records)


def validate_dataframe(
    dataframe: pd.DataFrame,
    id_column: str,
    expected_count: int,
) -> None:
    """Validate row count and identifier quality."""

    if len(dataframe) != expected_count:
        raise ValueError(
            f"Expected {expected_count} rows but found {len(dataframe)}."
        )

    if dataframe[id_column].duplicated().any():
        raise ValueError(
            f"Duplicate values found in {id_column}."
        )

    if dataframe[id_column].isna().any():
        raise ValueError(
            f"Null values found in {id_column}."
        )


def main() -> None:
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    locations = generate_locations()
    machines = generate_machines(locations)
    players = generate_players()

    validate_dataframe(
        locations,
        "location_id",
        NUM_LOCATIONS,
    )

    validate_dataframe(
        machines,
        "machine_id",
        NUM_MACHINES,
    )

    validate_dataframe(
        players,
        "player_id",
        NUM_PLAYERS,
    )

    locations.to_csv(
        RAW_DATA_DIR / "locations.csv",
        index=False,
    )

    machines.to_csv(
        RAW_DATA_DIR / "machines.csv",
        index=False,
    )

    players.to_csv(
        RAW_DATA_DIR / "players.csv",
        index=False,
    )

    print("Reference data generated successfully.")
    print(f"Locations: {len(locations):,}")
    print(f"Machines: {len(machines):,}")
    print(f"Players: {len(players):,}")
    print(f"Output folder: {RAW_DATA_DIR}")


if __name__ == "__main__":
    main()
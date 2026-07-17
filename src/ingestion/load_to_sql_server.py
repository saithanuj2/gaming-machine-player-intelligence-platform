import sys
from pathlib import Path

import pandas as pd
import pyodbc

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import RAW_DATA_DIR


CONNECTION_STRING = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=localhost,1433;"
    "DATABASE=GamingIntelligenceDB;"
    "UID=sa;"
    "PWD=Gaming@2026Strong;"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
)


def load_csv(filename: str) -> pd.DataFrame:
    file_path = RAW_DATA_DIR / filename

    if not file_path.exists():
        raise FileNotFoundError(
            f"Required file not found: {file_path}"
        )

    return pd.read_csv(file_path)


def clear_tables(cursor: pyodbc.Cursor) -> None:
    """Delete existing rows in reverse foreign-key order."""

    tables = [
        "dbo.fact_gaming_transaction",
        "dbo.fact_machine_event",
        "dbo.fact_player_session",
        "dbo.dim_machine",
        "dbo.dim_player",
        "dbo.dim_location",
    ]

    for table in tables:
        cursor.execute(f"DELETE FROM {table};")
        print(f"Cleared {table}")


def insert_dataframe(
    cursor: pyodbc.Cursor,
    dataframe: pd.DataFrame,
    insert_sql: str,
    table_name: str,
) -> None:
    """Insert a DataFrame using fast executemany."""

    cursor.fast_executemany = True

    rows = [
        tuple(
            None if pd.isna(value) else value
            for value in row
        )
        for row in dataframe.itertuples(
            index=False,
            name=None,
        )
    ]

    cursor.executemany(
        insert_sql,
        rows,
    )

    print(
        f"Loaded {len(dataframe):,} rows into "
        f"{table_name}"
    )


def main() -> None:
    connection = None

    try:
        locations = load_csv("locations.csv")
        players = load_csv("players.csv")
        machines = load_csv("machines.csv")
        sessions = load_csv("player_sessions.csv")
        transactions = load_csv("gaming_transactions.csv")
        events = load_csv("machine_events.csv")

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

        events["event_timestamp"] = pd.to_datetime(
            events["event_timestamp"]
        )
        events["event_date"] = pd.to_datetime(
            events["event_date"]
        ).dt.date

        locations["opening_date"] = pd.to_datetime(
            locations["opening_date"]
        ).dt.date

        players["enrollment_date"] = pd.to_datetime(
            players["enrollment_date"]
        ).dt.date

        machines["install_date"] = pd.to_datetime(
            machines["install_date"]
        ).dt.date

        connection = pyodbc.connect(
            CONNECTION_STRING,
            timeout=15,
        )

        cursor = connection.cursor()

        clear_tables(cursor)

        insert_dataframe(
            cursor,
            locations,
            """
            INSERT INTO dbo.dim_location
            (
                location_id,
                location_name,
                city,
                state,
                region,
                route_manager,
                location_type,
                opening_date,
                active_flag
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            "dbo.dim_location",
        )

        insert_dataframe(
            cursor,
            players,
            """
            INSERT INTO dbo.dim_player
            (
                player_id,
                enrollment_date,
                loyalty_tier,
                age_band,
                home_region,
                marketing_opt_in,
                active_flag
            )
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            "dbo.dim_player",
        )

        insert_dataframe(
            cursor,
            machines,
            """
            INSERT INTO dbo.dim_machine
            (
                machine_id,
                location_id,
                manufacturer,
                cabinet_type,
                game_title,
                game_category,
                install_date,
                software_version,
                machine_status,
                theoretical_hold_pct
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            "dbo.dim_machine",
        )

        insert_dataframe(
            cursor,
            sessions,
            """
            INSERT INTO dbo.fact_player_session
            (
                session_id,
                player_id,
                machine_id,
                location_id,
                session_start,
                session_end,
                session_duration_minutes,
                total_rounds,
                total_wager,
                total_payout,
                net_gaming_revenue
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            "dbo.fact_player_session",
        )

        insert_dataframe(
            cursor,
            transactions,
            """
            INSERT INTO dbo.fact_gaming_transaction
            (
                transaction_id,
                session_id,
                player_id,
                machine_id,
                location_id,
                transaction_timestamp,
                wager_amount,
                payout_amount,
                jackpot_amount,
                net_gaming_revenue,
                transaction_type
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            "dbo.fact_gaming_transaction",
        )

        insert_dataframe(
            cursor,
            events,
            """
            INSERT INTO dbo.fact_machine_event
            (
                event_id,
                machine_id,
                location_id,
                event_timestamp,
                event_type,
                severity,
                downtime_minutes,
                software_version,
                error_code,
                event_date,
                requires_investigation,
                planned_event_flag
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            "dbo.fact_machine_event",
        )

        connection.commit()

        print("\nAll datasets loaded successfully.")

        cursor.close()

    except Exception:
        if connection is not None:
            connection.rollback()

        print("\nLoad failed. All changes were rolled back.")
        raise

    finally:
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    main()
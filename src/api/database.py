import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

import pyodbc
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")


def build_connection_string() -> str:
    """Build the SQL Server connection string from environment variables."""

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
        raise RuntimeError(
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


@contextmanager
def get_database_connection() -> Generator[
    pyodbc.Connection,
    None,
    None,
]:
    """Create and safely close a SQL Server connection."""

    connection = None

    try:
        connection = pyodbc.connect(
            build_connection_string(),
            timeout=15,
        )

        yield connection

    finally:
        if connection is not None:
            connection.close()


def fetch_one(
    query: str,
    parameters: tuple[Any, ...] = (),
) -> dict[str, Any] | None:
    """Execute a query and return one row as a dictionary."""

    with get_database_connection() as connection:
        cursor = connection.cursor()

        cursor.execute(
            query,
            parameters,
        )

        row = cursor.fetchone()

        if row is None:
            return None

        column_names = [
            description[0]
            for description in cursor.description
        ]

        return dict(
            zip(
                column_names,
                row,
            )
        )


def fetch_all(
    query: str,
    parameters: tuple[Any, ...] = (),
) -> list[dict[str, Any]]:
    """Execute a query and return all rows as dictionaries."""

    with get_database_connection() as connection:
        cursor = connection.cursor()

        cursor.execute(
            query,
            parameters,
        )

        rows = cursor.fetchall()

        if not rows:
            return []

        column_names = [
            description[0]
            for description in cursor.description
        ]

        return [
            dict(
                zip(
                    column_names,
                    row,
                )
            )
            for row in rows
        ]


def test_database_connection() -> dict[str, Any]:
    """Test SQL Server connectivity and return database details."""

    query = """
        SELECT
            DB_NAME() AS database_name,
            @@SERVERNAME AS server_name,
            CAST(SERVERPROPERTY('ProductVersion') AS VARCHAR(100))
                AS product_version;
    """

    result = fetch_one(query)

    if result is None:
        raise RuntimeError(
            "Database connection test returned no result."
        )

    return result
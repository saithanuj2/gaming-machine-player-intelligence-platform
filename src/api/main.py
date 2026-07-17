import math
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.api.database import (
    fetch_all,
    fetch_one,
    test_database_connection,
)
from src.api.routers.forecast import (
    router as forecast_router,
)
from src.api.routers.machines import (
    router as machines_router,
)
from src.api.routers.players import (
    router as players_router,
)
from src.api.schemas import (
    ExecutiveKPIResponse,
    HealthResponse,
)


API_VERSION = "1.0.0"


app = FastAPI(
    title="Gaming Machine Player Intelligence API",
    description=(
        "Enterprise API for executive gaming analytics, "
        "player intelligence, machine health, predictive "
        "maintenance, anomaly detection, segmentation, "
        "and revenue forecasting."
    ),
    version=API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def serialize_value(value: Any) -> Any:
    """Convert SQL Server values into JSON-safe Python values."""

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, datetime):
        return value.isoformat()

    return value


def serialize_record(
    record: dict[str, Any],
) -> dict[str, Any]:
    """Convert a database record into JSON-safe values."""

    return {
        key: serialize_value(value)
        for key, value in record.items()
    }


@app.get(
    "/",
    include_in_schema=False,
)
def root() -> RedirectResponse:
    """Redirect the root URL to Swagger documentation."""

    return RedirectResponse(
        url="/docs"
    )


@app.get(
    "/api/v1/health",
    response_model=HealthResponse,
    tags=["System"],
)
def health_check() -> HealthResponse:
    """Check API and SQL Server availability."""

    try:
        database_details = (
            test_database_connection()
        )

        return HealthResponse(
            status="healthy",
            service=(
                "Gaming Machine Player "
                "Intelligence API"
            ),
            version=API_VERSION,
            database_connected=True,
            database_name=database_details.get(
                "database_name"
            ),
            server_name=database_details.get(
                "server_name"
            ),
            timestamp=datetime.now(
                timezone.utc
            ),
        )

    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "database_connected": False,
                "error": str(error),
            },
        ) from error


@app.get(
    "/api/v1/dashboard/kpis",
    response_model=ExecutiveKPIResponse,
    tags=["Executive Dashboard"],
)
def get_executive_kpis() -> ExecutiveKPIResponse:
    """Return executive gaming and operational KPIs."""

    query = """
        SELECT
            k.active_location_count,

            k.revenue_generating_machine_count
                AS active_machine_count,

            (
                SELECT COUNT(*)
                FROM dbo.dim_machine
            ) AS registered_machine_count,

            k.active_player_count,

            (
                SELECT COUNT(*)
                FROM dbo.dim_player
            ) AS registered_player_count,

            k.total_session_count,
            k.total_transaction_count,
            k.total_wager,
            k.total_payout,
            k.net_gaming_revenue,
            k.actual_hold_pct,
            k.revenue_per_session,
            k.revenue_per_machine,

            (
                SELECT
                    SUM(total_downtime_minutes)
                FROM dbo.vw_machine_health
            ) AS total_downtime_minutes,

            (
                SELECT
                    SUM(critical_event_count)
                FROM dbo.vw_machine_health
            ) AS total_critical_events,

            (
                SELECT
                    AVG(
                        CAST(
                            annual_availability_pct
                            AS FLOAT
                        )
                    )
                FROM dbo.vw_machine_health
            ) AS average_machine_availability_pct

        FROM dbo.vw_executive_kpis AS k;
    """

    try:
        result = fetch_one(
            query
        )

        if result is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Executive KPI data was not found."
                ),
            )

        serialized_result = (
            serialize_record(
                result
            )
        )

        return ExecutiveKPIResponse(
            **serialized_result,
            generated_at=datetime.now(
                timezone.utc
            ),
        )

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to retrieve executive KPIs: "
                f"{error}"
            ),
        ) from error


@app.get(
    "/api/v1/dashboard/revenue-trend",
    tags=["Executive Dashboard"],
)
def get_revenue_trend(
    days: int = Query(
        default=30,
        ge=1,
        le=365,
        description=(
            "Number of recent activity dates "
            "to return."
        ),
    ),
) -> dict[str, Any]:
    """Return recent daily gaming revenue activity."""

    query = """
        WITH daily_revenue AS
        (
            SELECT
                CAST(
                    transaction_timestamp AS DATE
                ) AS activity_date,

                COUNT_BIG(*) AS transaction_count,

                COUNT(
                    DISTINCT session_id
                ) AS session_count,

                COUNT(
                    DISTINCT player_id
                ) AS active_player_count,

                COUNT(
                    DISTINCT machine_id
                ) AS active_machine_count,

                SUM(
                    wager_amount
                ) AS total_wager,

                SUM(
                    payout_amount
                ) AS total_payout,

                SUM(
                    net_gaming_revenue
                ) AS net_gaming_revenue

            FROM dbo.fact_gaming_transaction

            GROUP BY
                CAST(
                    transaction_timestamp AS DATE
                )
        ),

        ranked_dates AS
        (
            SELECT
                *,
                DENSE_RANK() OVER
                (
                    ORDER BY activity_date DESC
                ) AS date_rank

            FROM daily_revenue
        )

        SELECT
            activity_date,
            transaction_count,
            session_count,
            active_player_count,
            active_machine_count,
            total_wager,
            total_payout,
            net_gaming_revenue,

            CAST(
                net_gaming_revenue
                / NULLIF(total_wager, 0)
                AS DECIMAL(10,4)
            ) AS actual_hold_pct

        FROM ranked_dates

        WHERE date_rank <= ?

        ORDER BY activity_date;
    """

    try:
        results = fetch_all(
            query,
            (days,),
        )

        serialized_results = [
            serialize_record(record)
            for record in results
        ]

        return {
            "days_requested": days,
            "record_count": len(
                serialized_results
            ),
            "data": serialized_results,
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to retrieve revenue trend: "
                f"{error}"
            ),
        ) from error


@app.get(
    "/api/v1/machines/high-risk",
    tags=["Machine Intelligence"],
)
def get_high_risk_machines(
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
) -> dict[str, Any]:
    """Return SQL-derived high-risk machines."""

    offset = (
        page - 1
    ) * page_size

    count_query = """
        SELECT
            COUNT(*) AS total_records

        FROM dbo.vw_machine_health

        WHERE
            critical_event_count >= 4
            OR total_downtime_minutes >= 3500;
    """

    data_query = """
        SELECT
            machine_id,
            location_id,
            location_name,
            manufacturer,
            game_title,
            game_category,
            software_version,
            total_event_count,
            unplanned_event_count,
            critical_event_count,
            total_downtime_minutes,
            annual_availability_pct,

            CASE
                WHEN
                    critical_event_count >= 8
                    OR total_downtime_minutes >= 5000
                THEN 'Critical'

                WHEN
                    critical_event_count >= 4
                    OR total_downtime_minutes >= 3500
                THEN 'High'

                ELSE 'Medium'
            END AS health_risk_level

        FROM dbo.vw_machine_health

        WHERE
            critical_event_count >= 4
            OR total_downtime_minutes >= 3500

        ORDER BY
            critical_event_count DESC,
            total_downtime_minutes DESC

        OFFSET ? ROWS
        FETCH NEXT ? ROWS ONLY;
    """

    try:
        count_result = fetch_one(
            count_query
        )

        total_records = int(
            count_result[
                "total_records"
            ]
            if count_result
            else 0
        )

        records = fetch_all(
            data_query,
            (
                offset,
                page_size,
            ),
        )

        total_pages = (
            math.ceil(
                total_records
                / page_size
            )
            if total_records
            else 0
        )

        return {
            "page": page,
            "page_size": page_size,
            "total_records": total_records,
            "total_pages": total_pages,
            "data": [
                serialize_record(record)
                for record in records
            ],
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to retrieve high-risk "
                f"machines: {error}"
            ),
        ) from error


# Router registration is intentionally placed after the
# fixed machine route so /machines/high-risk is not captured
# by the dynamic /machines/{machine_id} endpoint.
app.include_router(
    players_router
)

app.include_router(
    machines_router
)

app.include_router(
    forecast_router
)
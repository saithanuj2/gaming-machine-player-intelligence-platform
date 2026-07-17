import math
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import APIRouter, HTTPException, Query


PROJECT_ROOT = Path(__file__).resolve().parents[3]

FAILURE_PREDICTIONS_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "ml"
    / "machine_failure_all_predictions.csv"
)

ANOMALY_PREDICTIONS_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "ml"
    / "machine_anomaly_predictions.csv"
)

ANOMALY_SUMMARY_PATH = (
    PROJECT_ROOT
    / "reports"
    / "model_metrics"
    / "machine_anomaly_machine_summary.csv"
)

MAINTENANCE_PRIORITY_PATH = (
    PROJECT_ROOT
    / "reports"
    / "machine_failure_validation"
    / "machine_failure_maintenance_priority.csv"
)


router = APIRouter(
    prefix="/api/v1/machines",
    tags=["Machine Intelligence"],
)


def load_csv(file_path: Path) -> pd.DataFrame:
    """Load and validate a required model-output CSV."""

    if not file_path.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                f"Required output {file_path.name} was not found. "
                "Run the corresponding model pipeline first."
            ),
        )

    try:
        dataframe = pd.read_csv(file_path)

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to read {file_path.name}: {error}",
        ) from error

    if dataframe.empty:
        raise HTTPException(
            status_code=503,
            detail=f"{file_path.name} contains no records.",
        )

    return dataframe


def clean_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Convert missing and infinite values into JSON-safe values."""

    output = dataframe.copy()

    output = output.replace(
        [float("inf"), float("-inf")],
        pd.NA,
    )

    return output.where(
        pd.notna(output),
        None,
    )


def paginate_dataframe(
    dataframe: pd.DataFrame,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    """Return a paginated response."""

    total_records = len(dataframe)

    total_pages = (
        math.ceil(total_records / page_size)
        if total_records
        else 0
    )

    start_index = (page - 1) * page_size
    end_index = start_index + page_size

    page_data = dataframe.iloc[
        start_index:end_index
    ]

    return {
        "page": page,
        "page_size": page_size,
        "total_records": total_records,
        "total_pages": total_pages,
        "data": clean_dataframe(
            page_data
        ).to_dict(orient="records"),
    }


def validate_required_columns(
    dataframe: pd.DataFrame,
    required_columns: set[str],
    dataset_name: str,
) -> None:
    """Ensure expected columns exist."""

    missing_columns = (
        required_columns
        - set(dataframe.columns)
    )

    if missing_columns:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Missing columns in {dataset_name}: "
                + ", ".join(
                    sorted(missing_columns)
                )
            ),
        )


@router.get("/summary")
def get_machine_summary() -> dict[str, Any]:
    """Return machine failure and anomaly KPIs."""

    failure_data = load_csv(
        FAILURE_PREDICTIONS_PATH
    )

    anomaly_data = load_csv(
        ANOMALY_PREDICTIONS_PATH
    )

    validate_required_columns(
        failure_data,
        {
            "machine_id",
            "failure_probability",
            "failure_risk_level",
            "revenue_at_risk",
        },
        "machine failure predictions",
    )

    validate_required_columns(
        anomaly_data,
        {
            "machine_id",
            "isolation_forest_anomaly_flag",
            "anomaly_risk_level",
            "revenue_exposure",
        },
        "machine anomaly predictions",
    )

    total_machines = int(
        failure_data["machine_id"].nunique()
    )

    high_risk_machines = int(
        failure_data[
            "failure_risk_level"
        ].isin(
            ["High", "Critical"]
        ).sum()
    )

    critical_failure_machines = int(
        (
            failure_data[
                "failure_risk_level"
            ] == "Critical"
        ).sum()
    )

    average_failure_probability = float(
        pd.to_numeric(
            failure_data[
                "failure_probability"
            ],
            errors="coerce",
        ).mean()
    )

    failure_revenue_at_risk = float(
        pd.to_numeric(
            failure_data[
                "revenue_at_risk"
            ],
            errors="coerce",
        ).fillna(0).sum()
    )

    detected_anomalies = int(
        pd.to_numeric(
            anomaly_data[
                "isolation_forest_anomaly_flag"
            ],
            errors="coerce",
        ).fillna(0).sum()
    )

    critical_anomaly_days = int(
        (
            anomaly_data[
                "anomaly_risk_level"
            ].astype(str)
            == "Critical"
        ).sum()
    )

    anomaly_revenue_exposure = float(
        pd.to_numeric(
            anomaly_data[
                "revenue_exposure"
            ],
            errors="coerce",
        ).fillna(0).sum()
    )

    return {
        "total_machines_scored": total_machines,
        "high_and_critical_failure_risk_machines": (
            high_risk_machines
        ),
        "critical_failure_risk_machines": (
            critical_failure_machines
        ),
        "average_failure_probability": round(
            average_failure_probability,
            4,
        ),
        "failure_revenue_at_risk": round(
            failure_revenue_at_risk,
            2,
        ),
        "detected_anomalous_machine_days": (
            detected_anomalies
        ),
        "critical_anomaly_days": (
            critical_anomaly_days
        ),
        "anomaly_revenue_exposure": round(
            anomaly_revenue_exposure,
            2,
        ),
    }


@router.get("/failure-risk")
def get_failure_risk_machines(
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=200,
    ),
    risk_level: str | None = Query(
        default=None,
        description=(
            "Filter by Low, Medium, High, or Critical."
        ),
    ),
    manufacturer: str | None = Query(
        default=None,
    ),
    location_id: str | None = Query(
        default=None,
    ),
    minimum_probability: float = Query(
        default=0.0,
        ge=0.0,
        le=1.0,
    ),
    search: str | None = Query(
        default=None,
        description="Search by machine ID.",
    ),
) -> dict[str, Any]:
    """Return machines ranked by predicted failure risk."""

    dataframe = load_csv(
        FAILURE_PREDICTIONS_PATH
    )

    validate_required_columns(
        dataframe,
        {
            "machine_id",
            "failure_probability",
            "failure_risk_level",
        },
        "machine failure predictions",
    )

    filtered = dataframe.copy()

    filtered[
        "failure_probability"
    ] = pd.to_numeric(
        filtered[
            "failure_probability"
        ],
        errors="coerce",
    )

    filtered = filtered.loc[
        filtered[
            "failure_probability"
        ] >= minimum_probability
    ]

    if risk_level:
        filtered = filtered.loc[
            filtered[
                "failure_risk_level"
            ].astype(str).str.lower()
            == risk_level.lower()
        ]

    if (
        manufacturer
        and "manufacturer" in filtered.columns
    ):
        filtered = filtered.loc[
            filtered[
                "manufacturer"
            ].astype(str).str.lower()
            == manufacturer.lower()
        ]

    if (
        location_id
        and "location_id" in filtered.columns
    ):
        filtered = filtered.loc[
            filtered[
                "location_id"
            ].astype(str).str.upper()
            == location_id.upper()
        ]

    if search:
        filtered = filtered.loc[
            filtered[
                "machine_id"
            ]
            .astype(str)
            .str.contains(
                search,
                case=False,
                na=False,
            )
        ]

    sort_columns = [
        column
        for column in [
            "failure_probability",
            "revenue_at_risk",
            "total_downtime_minutes",
        ]
        if column in filtered.columns
    ]

    if sort_columns:
        filtered = filtered.sort_values(
            sort_columns,
            ascending=False,
        )

    filtered = filtered.reset_index(
        drop=True
    )

    response = paginate_dataframe(
        filtered,
        page,
        page_size,
    )

    response["filters"] = {
        "risk_level": risk_level,
        "manufacturer": manufacturer,
        "location_id": location_id,
        "minimum_probability": (
            minimum_probability
        ),
        "search": search,
    }

    return response


@router.get("/anomalies")
def get_machine_anomalies(
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=200,
    ),
    risk_level: str | None = Query(
        default=None,
    ),
    manufacturer: str | None = Query(
        default=None,
    ),
    machine_id: str | None = Query(
        default=None,
    ),
    anomaly_only: bool = Query(
        default=True,
    ),
) -> dict[str, Any]:
    """Return machine-day anomaly alerts."""

    dataframe = load_csv(
        ANOMALY_PREDICTIONS_PATH
    )

    validate_required_columns(
        dataframe,
        {
            "machine_id",
            "activity_date",
            "isolation_forest_anomaly_flag",
            "anomaly_score",
            "anomaly_risk_level",
        },
        "machine anomaly predictions",
    )

    filtered = dataframe.copy()

    if anomaly_only:
        filtered = filtered.loc[
            pd.to_numeric(
                filtered[
                    "isolation_forest_anomaly_flag"
                ],
                errors="coerce",
            ) == 1
        ]

    if risk_level:
        filtered = filtered.loc[
            filtered[
                "anomaly_risk_level"
            ].astype(str).str.lower()
            == risk_level.lower()
        ]

    if (
        manufacturer
        and "manufacturer" in filtered.columns
    ):
        filtered = filtered.loc[
            filtered[
                "manufacturer"
            ].astype(str).str.lower()
            == manufacturer.lower()
        ]

    if machine_id:
        filtered = filtered.loc[
            filtered[
                "machine_id"
            ].astype(str).str.upper()
            == machine_id.upper()
        ]

    filtered[
        "anomaly_score"
    ] = pd.to_numeric(
        filtered[
            "anomaly_score"
        ],
        errors="coerce",
    )

    filtered = filtered.sort_values(
        [
            "anomaly_score",
            "revenue_exposure",
        ],
        ascending=False,
    ).reset_index(drop=True)

    response = paginate_dataframe(
        filtered,
        page,
        page_size,
    )

    response["filters"] = {
        "risk_level": risk_level,
        "manufacturer": manufacturer,
        "machine_id": machine_id,
        "anomaly_only": anomaly_only,
    }

    return response


@router.get("/maintenance-priority")
def get_maintenance_priorities(
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=200,
    ),
) -> dict[str, Any]:
    """Return ranked maintenance recommendations."""

    dataframe = load_csv(
        MAINTENANCE_PRIORITY_PATH
    )

    validate_required_columns(
        dataframe,
        {
            "machine_id",
            "failure_probability",
            "maintenance_priority_score",
            "maintenance_priority_rank",
            "recommended_action",
        },
        "maintenance priority output",
    )

    dataframe = dataframe.sort_values(
        [
            "maintenance_priority_rank",
            "failure_probability",
        ],
        ascending=[
            True,
            False,
        ],
    ).reset_index(drop=True)

    return paginate_dataframe(
        dataframe,
        page,
        page_size,
    )


@router.get("/anomaly-summary")
def get_machine_anomaly_summary(
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=200,
    ),
) -> dict[str, Any]:
    """Return machine-level anomaly priority rankings."""

    dataframe = load_csv(
        ANOMALY_SUMMARY_PATH
    )

    validate_required_columns(
        dataframe,
        {
            "machine_id",
            "anomaly_day_count",
            "anomaly_rate",
            "operational_priority_score",
            "priority_rank",
        },
        "machine anomaly summary",
    )

    dataframe = dataframe.sort_values(
        [
            "priority_rank",
            "operational_priority_score",
        ],
        ascending=[
            True,
            False,
        ],
    ).reset_index(drop=True)

    return paginate_dataframe(
        dataframe,
        page,
        page_size,
    )


@router.get("/{machine_id}")
def get_machine_details(
    machine_id: str,
) -> dict[str, Any]:
    """Return combined failure, anomaly, and maintenance details."""

    failure_data = load_csv(
        FAILURE_PREDICTIONS_PATH
    )

    anomaly_data = load_csv(
        ANOMALY_PREDICTIONS_PATH
    )

    anomaly_summary = load_csv(
        ANOMALY_SUMMARY_PATH
    )

    maintenance_data = load_csv(
        MAINTENANCE_PRIORITY_PATH
    )

    normalized_id = machine_id.upper()

    failure_match = failure_data.loc[
        failure_data[
            "machine_id"
        ].astype(str).str.upper()
        == normalized_id
    ]

    anomaly_matches = anomaly_data.loc[
        anomaly_data[
            "machine_id"
        ].astype(str).str.upper()
        == normalized_id
    ].copy()

    summary_match = anomaly_summary.loc[
        anomaly_summary[
            "machine_id"
        ].astype(str).str.upper()
        == normalized_id
    ]

    maintenance_match = maintenance_data.loc[
        maintenance_data[
            "machine_id"
        ].astype(str).str.upper()
        == normalized_id
    ]

    if (
        failure_match.empty
        and anomaly_matches.empty
        and summary_match.empty
        and maintenance_match.empty
    ):
        raise HTTPException(
            status_code=404,
            detail=(
                f"Machine {normalized_id} was not found."
            ),
        )

    if not anomaly_matches.empty:
        anomaly_matches[
            "anomaly_score"
        ] = pd.to_numeric(
            anomaly_matches[
                "anomaly_score"
            ],
            errors="coerce",
        )

        anomaly_matches = (
            anomaly_matches.sort_values(
                "anomaly_score",
                ascending=False,
            )
        )

    failure_record = clean_dataframe(
        failure_match.head(1)
    ).to_dict(orient="records")

    anomaly_records = clean_dataframe(
        anomaly_matches.head(20)
    ).to_dict(orient="records")

    summary_record = clean_dataframe(
        summary_match.head(1)
    ).to_dict(orient="records")

    maintenance_record = clean_dataframe(
        maintenance_match.head(1)
    ).to_dict(orient="records")

    return {
        "machine_id": normalized_id,
        "failure_profile": (
            failure_record[0]
            if failure_record
            else None
        ),
        "maintenance_profile": (
            maintenance_record[0]
            if maintenance_record
            else None
        ),
        "anomaly_summary": (
            summary_record[0]
            if summary_record
            else None
        ),
        "recent_top_anomalies": (
            anomaly_records
        ),
    }
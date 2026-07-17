import math
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import APIRouter, HTTPException, Query


PROJECT_ROOT = Path(__file__).resolve().parents[3]

CHURN_PREDICTIONS_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "ml"
    / "player_churn_all_predictions.csv"
)

SEGMENTATION_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "ml"
    / "player_segmentation_predictions.csv"
)


router = APIRouter(
    prefix="/api/v1/players",
    tags=["Player Intelligence"],
)


def load_csv(
    file_path: Path,
) -> pd.DataFrame:
    """Load a CSV model output and validate its availability."""

    if not file_path.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                "Required model output was not found: "
                f"{file_path.name}. Run the corresponding "
                "model pipeline first."
            ),
        )

    try:
        dataframe = pd.read_csv(
            file_path
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Unable to read {file_path.name}: "
                f"{error}"
            ),
        ) from error

    if dataframe.empty:
        raise HTTPException(
            status_code=503,
            detail=(
                f"{file_path.name} contains no records."
            ),
        )

    return dataframe


def clean_dataframe(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """Convert NaN and infinite values into JSON-safe values."""

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
    """Return a paginated JSON-ready response."""

    total_records = len(
        dataframe
    )

    total_pages = (
        math.ceil(
            total_records / page_size
        )
        if total_records
        else 0
    )

    start_index = (
        page - 1
    ) * page_size

    end_index = (
        start_index
        + page_size
    )

    page_data = dataframe.iloc[
        start_index:end_index
    ]

    clean_page_data = clean_dataframe(
        page_data
    )

    return {
        "page": page,
        "page_size": page_size,
        "total_records": total_records,
        "total_pages": total_pages,
        "data": clean_page_data.to_dict(
            orient="records"
        ),
    }


@router.get(
    "/summary",
)
def get_player_summary() -> dict[str, Any]:
    """Return player churn and segmentation KPIs."""

    churn_data = load_csv(
        CHURN_PREDICTIONS_PATH
    )

    segmentation_data = load_csv(
        SEGMENTATION_PATH
    )

    required_churn_columns = {
        "player_id",
        "churn_probability",
        "risk_level",
        "player_net_revenue",
    }

    missing_churn_columns = (
        required_churn_columns
        - set(churn_data.columns)
    )

    if missing_churn_columns:
        raise HTTPException(
            status_code=500,
            detail=(
                "Missing churn columns: "
                + ", ".join(
                    sorted(
                        missing_churn_columns
                    )
                )
            ),
        )

    required_segment_columns = {
        "player_id",
        "player_segment",
        "player_net_revenue",
    }

    missing_segment_columns = (
        required_segment_columns
        - set(segmentation_data.columns)
    )

    if missing_segment_columns:
        raise HTTPException(
            status_code=500,
            detail=(
                "Missing segmentation columns: "
                + ", ".join(
                    sorted(
                        missing_segment_columns
                    )
                )
            ),
        )

    total_players = int(
        churn_data[
            "player_id"
        ].nunique()
    )

    high_risk_players = int(
        churn_data[
            "risk_level"
        ].isin(
            [
                "High",
                "Critical",
            ]
        ).sum()
    )

    critical_risk_players = int(
        (
            churn_data[
                "risk_level"
            ] == "Critical"
        ).sum()
    )

    average_churn_probability = float(
        churn_data[
            "churn_probability"
        ].mean()
    )

    estimated_revenue_at_risk = float(
        (
            churn_data[
                "player_net_revenue"
            ].clip(lower=0)
            * churn_data[
                "churn_probability"
            ]
        ).sum()
    )

    vip_players = int(
        (
            segmentation_data[
                "player_segment"
            ] == "VIP High Value"
        ).sum()
    )

    at_risk_segment_players = int(
        (
            segmentation_data[
                "player_segment"
            ] == "At-Risk Players"
        ).sum()
    )

    segment_distribution = (
        segmentation_data[
            "player_segment"
        ]
        .value_counts()
        .rename_axis(
            "player_segment"
        )
        .reset_index(
            name="player_count"
        )
    )

    return {
        "total_players_scored": total_players,
        "high_and_critical_risk_players": (
            high_risk_players
        ),
        "critical_risk_players": (
            critical_risk_players
        ),
        "average_churn_probability": round(
            average_churn_probability,
            4,
        ),
        "estimated_revenue_at_risk": round(
            estimated_revenue_at_risk,
            2,
        ),
        "vip_players": vip_players,
        "at_risk_segment_players": (
            at_risk_segment_players
        ),
        "segment_distribution": (
            segment_distribution
            .to_dict(
                orient="records"
            )
        ),
    }


@router.get(
    "/churn-risk",
)
def get_churn_risk_players(
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
    loyalty_tier: str | None = Query(
        default=None,
    ),
    home_region: str | None = Query(
        default=None,
    ),
    minimum_probability: float = Query(
        default=0.0,
        ge=0.0,
        le=1.0,
    ),
    search: str | None = Query(
        default=None,
        description=(
            "Search by player ID."
        ),
    ),
) -> dict[str, Any]:
    """Return paginated players ranked by churn probability."""

    dataframe = load_csv(
        CHURN_PREDICTIONS_PATH
    )

    required_columns = {
        "player_id",
        "churn_probability",
        "risk_level",
    }

    missing_columns = (
        required_columns
        - set(dataframe.columns)
    )

    if missing_columns:
        raise HTTPException(
            status_code=500,
            detail=(
                "Missing churn prediction columns: "
                + ", ".join(
                    sorted(missing_columns)
                )
            ),
        )

    filtered = dataframe.copy()

    filtered[
        "churn_probability"
    ] = pd.to_numeric(
        filtered[
            "churn_probability"
        ],
        errors="coerce",
    )

    filtered = filtered.loc[
        filtered[
            "churn_probability"
        ] >= minimum_probability
    ]

    if risk_level:
        filtered = filtered.loc[
            filtered[
                "risk_level"
            ].astype(str).str.lower()
            == risk_level.lower()
        ]

    if (
        loyalty_tier
        and "loyalty_tier"
        in filtered.columns
    ):
        filtered = filtered.loc[
            filtered[
                "loyalty_tier"
            ].astype(str).str.lower()
            == loyalty_tier.lower()
        ]

    if (
        home_region
        and "home_region"
        in filtered.columns
    ):
        filtered = filtered.loc[
            filtered[
                "home_region"
            ].astype(str).str.lower()
            == home_region.lower()
        ]

    if search:
        filtered = filtered.loc[
            filtered[
                "player_id"
            ]
            .astype(str)
            .str.contains(
                search,
                case=False,
                na=False,
            )
        ]

    filtered = filtered.sort_values(
        [
            "churn_probability",
            "player_net_revenue",
        ],
        ascending=False,
    ).reset_index(drop=True)

    response = paginate_dataframe(
        dataframe=filtered,
        page=page,
        page_size=page_size,
    )

    response[
        "filters"
    ] = {
        "risk_level": risk_level,
        "loyalty_tier": loyalty_tier,
        "home_region": home_region,
        "minimum_probability": (
            minimum_probability
        ),
        "search": search,
    }

    return response


@router.get(
    "/segments",
)
def get_player_segments(
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=200,
    ),
    segment: str | None = Query(
        default=None,
    ),
    loyalty_tier: str | None = Query(
        default=None,
    ),
    search: str | None = Query(
        default=None,
    ),
) -> dict[str, Any]:
    """Return paginated player segmentation results."""

    dataframe = load_csv(
        SEGMENTATION_PATH
    )

    required_columns = {
        "player_id",
        "player_segment",
        "cluster_id",
    }

    missing_columns = (
        required_columns
        - set(dataframe.columns)
    )

    if missing_columns:
        raise HTTPException(
            status_code=500,
            detail=(
                "Missing segmentation columns: "
                + ", ".join(
                    sorted(missing_columns)
                )
            ),
        )

    filtered = dataframe.copy()

    if segment:
        filtered = filtered.loc[
            filtered[
                "player_segment"
            ].astype(str).str.lower()
            == segment.lower()
        ]

    if (
        loyalty_tier
        and "loyalty_tier"
        in filtered.columns
    ):
        filtered = filtered.loc[
            filtered[
                "loyalty_tier"
            ].astype(str).str.lower()
            == loyalty_tier.lower()
        ]

    if search:
        filtered = filtered.loc[
            filtered[
                "player_id"
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
            "estimated_player_value",
            "player_net_revenue",
            "total_wager",
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
        dataframe=filtered,
        page=page,
        page_size=page_size,
    )

    response[
        "filters"
    ] = {
        "segment": segment,
        "loyalty_tier": loyalty_tier,
        "search": search,
    }

    return response


@router.get(
    "/{player_id}",
)
def get_player_details(
    player_id: str,
) -> dict[str, Any]:
    """Return combined churn and segmentation details for one player."""

    churn_data = load_csv(
        CHURN_PREDICTIONS_PATH
    )

    segmentation_data = load_csv(
        SEGMENTATION_PATH
    )

    churn_match = churn_data.loc[
        churn_data[
            "player_id"
        ].astype(str).str.upper()
        == player_id.upper()
    ]

    segment_match = (
        segmentation_data.loc[
            segmentation_data[
                "player_id"
            ].astype(str).str.upper()
            == player_id.upper()
        ]
    )

    if (
        churn_match.empty
        and segment_match.empty
    ):
        raise HTTPException(
            status_code=404,
            detail=(
                f"Player {player_id} was not found."
            ),
        )

    churn_record = (
        clean_dataframe(
            churn_match.head(1)
        )
        .to_dict(
            orient="records"
        )
    )

    segment_record = (
        clean_dataframe(
            segment_match.head(1)
        )
        .to_dict(
            orient="records"
        )
    )

    return {
        "player_id": player_id.upper(),
        "churn_profile": (
            churn_record[0]
            if churn_record
            else None
        ),
        "segmentation_profile": (
            segment_record[0]
            if segment_record
            else None
        ),
    }
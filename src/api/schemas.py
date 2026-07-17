from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    database_connected: bool
    database_name: str | None = None
    server_name: str | None = None
    timestamp: datetime


class ExecutiveKPIResponse(BaseModel):
    active_location_count: int = 0
    active_machine_count: int = 0
    registered_machine_count: int = 0
    active_player_count: int = 0
    registered_player_count: int = 0
    total_session_count: int = 0
    total_transaction_count: int = 0
    total_wager: float = 0.0
    total_payout: float = 0.0
    net_gaming_revenue: float = 0.0
    actual_hold_pct: float = 0.0
    revenue_per_session: float = 0.0
    revenue_per_machine: float = 0.0
    total_downtime_minutes: int = 0
    total_critical_events: int = 0
    average_machine_availability_pct: float = 0.0
    generated_at: datetime


class RevenueTrendItem(BaseModel):
    activity_date: str
    transaction_count: int
    session_count: int
    active_player_count: int
    active_machine_count: int
    total_wager: float
    total_payout: float
    net_gaming_revenue: float
    actual_hold_pct: float


class APIMessage(BaseModel):
    message: str
    details: dict[str, Any] | None = None


class PaginationMetadata(BaseModel):
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total_records: int
    total_pages: int
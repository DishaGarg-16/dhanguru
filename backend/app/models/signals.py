from datetime import datetime
from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, Field


class SignalCategory(str, Enum):
    VOLATILITY_BREAKOUT = "VOLATILITY_BREAKOUT"
    VOLUME_SURGE = "VOLUME_SURGE"
    CIRCUIT_ALERT = "CIRCUIT_ALERT"
    BENCHMARK_DECOUPLING = "BENCHMARK_DECOUPLING"
    LEVEL_BREACH = "LEVEL_BREACH"
    CALM = "CALM"


class AttentionSignal(BaseModel):
    """A human-translated market signal explaining why an asset moved"""
    category: SignalCategory
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    headline: str = Field(description="Human-friendly headline, e.g. '⚡ 3.2x Volume surge for 1:30 PM'")
    technical_detail: str = Field(description="Underlying quantitative measurement")
    badge_color: Literal["green", "red", "amber", "circuit", "neutral"]


class AnomalyEvaluation(BaseModel):
    """Complete anomaly evaluation for a single ticker"""
    symbol: str
    urgency_score: int = Field(ge=0, le=100, description="Composite attention score 0-100")
    signals: list[AttentionSignal] = Field(default_factory=list)
    primary_driver: str = Field(description="Single strongest reason or 'Normal market drift'")
    requires_attention: bool = Field(description="True if urgency_score >= 60")
    evaluated_at: datetime = Field(default_factory=datetime.now)


class SessionDelta(BaseModel):
    """Deterministic delta between two session checkpoints for a stock"""
    symbol: str
    company_name: str
    price_then: float
    price_now: float
    price_change: float
    price_change_pct: float
    volume_accumulated_while_away: int
    urgency_score: int
    signals: list[AttentionSignal]
    is_meaningful_change: bool


class WatchlistDeltaReport(BaseModel):
    """Executive session delta report comparing T_last_seen to T_now"""
    duration_away_seconds: int
    duration_away_human: str
    last_seen_at: datetime
    current_time: datetime
    total_tracked: int
    meaningful_changes_count: int
    benchmark_symbol: str = "NIFTY50"
    benchmark_change_pct: float
    top_attention: list[SessionDelta] = Field(description="Stocks with meaningful structural change")
    calm_stocks: list[SessionDelta] = Field(description="Stocks within normal noise limits")

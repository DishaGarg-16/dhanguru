from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field
from backend.app.models.signals import SessionDelta


class WatchlistItem(BaseModel):
    symbol: str
    added_at: datetime = Field(default_factory=datetime.now)


class UserWatchlist(BaseModel):
    user_id: str = "default_user"
    name: str = "Primary Watchlist"
    symbols: list[str] = Field(default_factory=list)
    last_seen_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class WatchlistSymbolRequest(BaseModel):
    symbol: str = Field(
        min_length=1,
        max_length=20,
        pattern=r"^[A-Za-z0-9&._-]+$",
        description="NSE/BSE ticker symbol (alphanumeric, &, -, _, .)",
    )


class ExecutiveBriefing(BaseModel):
    """Structured executive briefing delivered to the user upon returning"""
    time_away_human: str = Field(description="e.g. '2h 45m'")
    headline: str = Field(description="Crisp 1-sentence macro headline")
    market_mood: Literal["BULLISH", "BEARISH", "VOLATILE", "CALM"]
    key_takeaways: list[str] = Field(description="Top 2-3 bullet points on structural changes")
    top_anomalies: list[SessionDelta] = Field(default_factory=list)
    calm_count: int = Field(description="Number of stocks with normal drift")
    fomo_guard_notice: Optional[str] = Field(default=None, description="Responsible investing risk note")
    generated_by: Literal["AI_AGENT", "RULE_ENGINE_FALLBACK"]
    generated_at: datetime = Field(default_factory=datetime.now)

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Query
from backend.app.models.watchlist import ExecutiveBriefing
from backend.app.services.agent.synthesizer import briefing_service
from backend.app.services.analytics.diff_engine import CheckpointDiffEngine
from backend.app.services.market_data.store import central_store
from backend.app.services.watchlist.store import watchlist_store

router = APIRouter(prefix="/api/briefing", tags=["briefing"])
diff_engine = CheckpointDiffEngine(central_store)

# In-memory briefing cache to protect Gemini API rate limits (15 RPM free quota)
_briefing_cache: dict[str, tuple[datetime, ExecutiveBriefing]] = {}
CACHE_TTL_SECONDS = 20


def _get_cached_briefing(key: str) -> Optional[ExecutiveBriefing]:
    if key in _briefing_cache:
        cached_at, briefing = _briefing_cache[key]
        if (datetime.now() - cached_at).total_seconds() < CACHE_TTL_SECONDS:
            return briefing
    return None


def _set_cached_briefing(key: str, briefing: ExecutiveBriefing) -> None:
    _briefing_cache[key] = (datetime.now(), briefing)


@router.get("/since-last", response_model=ExecutiveBriefing)
async def get_briefing_since_last_visit(user_id: str = "default_user"):
    """
    Generates the 'Since You Checked' executive briefing card
    comparing the user's last recorded visit timestamp to current market state.
    Protected with in-memory TTL caching against rapid reloads.
    """
    wl = watchlist_store.get_watchlist(user_id)
    cache_key = f"since_last:{user_id}:{wl.last_seen_at.isoformat()}"
    cached = _get_cached_briefing(cache_key)
    if cached:
        return cached

    report = diff_engine.compute_diff(
        last_seen_at=wl.last_seen_at,
        symbols=wl.symbols,
    )
    briefing = await briefing_service.generate_briefing(report)
    _set_cached_briefing(cache_key, briefing)
    return briefing


@router.get("/window", response_model=ExecutiveBriefing)
async def get_briefing_for_time_window(
    minutes_ago: int = Query(default=60, ge=1, le=10080, description="Time window in minutes"),
    user_id: str = "default_user",
):
    """
    Generates an executive briefing for a specific past time window (e.g. 15m, 60m, 180m).
    Protected with in-memory TTL caching against rapid reloads.
    """
    cache_key = f"window:{user_id}:{minutes_ago}"
    cached = _get_cached_briefing(cache_key)
    if cached:
        return cached

    wl = watchlist_store.get_watchlist(user_id)
    target_time = datetime.now() - timedelta(minutes=minutes_ago)
    report = diff_engine.compute_diff(
        last_seen_at=target_time,
        symbols=wl.symbols,
    )
    briefing = await briefing_service.generate_briefing(report)
    _set_cached_briefing(cache_key, briefing)
    return briefing



@router.get("/status")
async def get_ai_status():
    """
    Returns live diagnostic status of LLM connection (Ollama/Cloud/Fallback).
    """
    return briefing_service.get_status()


@router.post("/refresh-ai")
async def refresh_ai_connection():
    """
    Force re-initialization of the AI agent from .env
    """
    briefing_service._init_agent()
    return briefing_service.get_status()


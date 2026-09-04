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


@router.get("/since-last", response_model=ExecutiveBriefing)
async def get_briefing_since_last_visit(user_id: str = "default_user"):
    """
    Generates the 'Since You Checked' executive briefing card
    comparing the user's last recorded visit timestamp to current market state.
    """
    wl = watchlist_store.get_watchlist(user_id)
    report = diff_engine.compute_diff(
        last_seen_at=wl.last_seen_at,
        symbols=wl.symbols,
    )
    return await briefing_service.generate_briefing(report)


@router.get("/window", response_model=ExecutiveBriefing)
async def get_briefing_for_time_window(
    minutes_ago: int = Query(default=60, ge=1, le=10080, description="Time window in minutes"),
    user_id: str = "default_user",
):
    """
    Generates an executive briefing for a specific past time window (e.g. 15m, 60m, 180m).
    """
    wl = watchlist_store.get_watchlist(user_id)
    target_time = datetime.now() - timedelta(minutes=minutes_ago)
    report = diff_engine.compute_diff(
        last_seen_at=target_time,
        symbols=wl.symbols,
    )
    return await briefing_service.generate_briefing(report)


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


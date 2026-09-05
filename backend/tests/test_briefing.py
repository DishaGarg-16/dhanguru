import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.models.signals import (
    AttentionSignal,
    SessionDelta,
    SignalCategory,
    WatchlistDeltaReport,
)
from backend.app.services.agent.synthesizer import RuleEngineBriefingFallback, briefing_service
from backend.app.services.watchlist.store import WatchlistStore


def test_rule_engine_briefing_calm_state():
    """Verify synthesizer produces a calm, reassuring briefing when no stocks moved abnormally"""
    report = WatchlistDeltaReport(
        duration_away_seconds=7200,
        duration_away_human="2h",
        last_seen_at=datetime.now() - timedelta(hours=2),
        current_time=datetime.now(),
        total_tracked=5,
        meaningful_changes_count=0,
        benchmark_change_pct=0.15,
        top_attention=[],
        calm_stocks=[
            SessionDelta(
                symbol="RELIANCE",
                company_name="Reliance Ltd",
                price_then=2980.0,
                price_now=2985.0,
                price_change=5.0,
                price_change_pct=0.17,
                volume_accumulated_while_away=200000,
                urgency_score=15,
                signals=[],
                is_meaningful_change=False,
            )
        ],
    )

    briefing = RuleEngineBriefingFallback.synthesize(report)

    assert briefing.market_mood == "CALM"
    assert "Calm session" in briefing.headline
    assert briefing.time_away_human == "2h"
    assert len(briefing.key_takeaways) == 3
    assert briefing.generated_by == "RULE_ENGINE_FALLBACK"


def test_rule_engine_briefing_circuit_alert():
    """Verify synthesizer generates high-priority risk notice if a stock approached circuit limits"""
    circuit_signal = AttentionSignal(
        category=SignalCategory.CIRCUIT_ALERT,
        severity="CRITICAL",
        headline="Approaching Upper Circuit (₹7,560)",
        technical_detail="0.4% from upper band",
        badge_color="circuit",
    )

    trent_delta = SessionDelta(
        symbol="TRENT",
        company_name="Trent Ltd",
        price_then=7200.0,
        price_now=7530.0,
        price_change=330.0,
        price_change_pct=4.58,
        volume_accumulated_while_away=3500000,
        urgency_score=92,
        signals=[circuit_signal],
        is_meaningful_change=True,
    )

    report = WatchlistDeltaReport(
        duration_away_seconds=10800,
        duration_away_human="3h",
        last_seen_at=datetime.now() - timedelta(hours=3),
        current_time=datetime.now(),
        total_tracked=5,
        meaningful_changes_count=1,
        benchmark_change_pct=0.30,
        top_attention=[trent_delta],
        calm_stocks=[],
    )

    briefing = RuleEngineBriefingFallback.synthesize(report)

    assert "circuit limit" in briefing.headline.lower()
    assert briefing.fomo_guard_notice is not None
    assert "Capital Protection Notice" in briefing.fomo_guard_notice
    assert "TRENT" in briefing.fomo_guard_notice


def test_watchlist_store_crud(tmp_path):
    """Verify watchlist add, remove, and acknowledge state changes"""
    test_file = tmp_path / "test_watchlist.json"
    store = WatchlistStore(storage_path=test_file)

    wl = store.get_watchlist("user_1")
    initial_checkpoint = wl.last_seen_at

    # Add symbol
    store.add_symbol("TCS", "user_1")
    assert "TCS" in store.get_watchlist("user_1").symbols

    # Remove symbol
    store.remove_symbol("TCS", "user_1")
    assert "TCS" not in store.get_watchlist("user_1").symbols

    # Acknowledge updates checkpoint to newer timestamp
    store.acknowledge_session("user_1")
    updated_checkpoint = store.get_watchlist("user_1").last_seen_at
    assert updated_checkpoint > initial_checkpoint


@pytest.mark.asyncio
async def test_api_watchlist_and_briefing_routes():
    """Verify end-to-end API endpoints for watchlist and executive briefing"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Get watchlist
        wl_resp = await client.get("/api/watchlist")
        assert wl_resp.status_code == 200
        wl_data = wl_resp.json()
        assert "items" in wl_data
        assert "total_symbols" in wl_data

        # 2. Get Executive Briefing since last visit
        briefing_resp = await client.get("/api/briefing/since-last")
        assert briefing_resp.status_code == 200
        brief_data = briefing_resp.json()
        assert "headline" in brief_data
        assert "key_takeaways" in brief_data
        assert "market_mood" in brief_data
        assert "generated_by" in brief_data

        # 3. Acknowledge session
        ack_resp = await client.post("/api/watchlist/acknowledge")
        assert ack_resp.status_code == 200
        assert ack_resp.json()["status"] == "success"


def test_ollama_provider_initialization(monkeypatch):
    """Verify synthesizer gracefully configures Ollama or falls back if unavailable"""
    import os
    from backend.app.services.agent.synthesizer import ExecutiveBriefingService

    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2")
    service = ExecutiveBriefingService()
    # Even if Ollama server is offline, service must not crash and fallback must remain intact
    assert service is not None


def test_rule_engine_briefing_empty_watchlist():
    """Verify synthesizer produces a clean empty state when user has 0 stocks in watchlist"""
    report = WatchlistDeltaReport(
        duration_away_seconds=120,
        duration_away_human="2m",
        last_seen_at=datetime.now() - timedelta(minutes=2),
        current_time=datetime.now(),
        total_tracked=0,
        meaningful_changes_count=0,
        benchmark_change_pct=0.0,
        top_attention=[],
        calm_stocks=[],
    )

    briefing = RuleEngineBriefingFallback.synthesize(report)

    assert "empty" in briefing.headline.lower()
    assert briefing.market_mood == "CALM"
    assert briefing.top_anomalies == []
    assert briefing.fomo_guard_notice is None

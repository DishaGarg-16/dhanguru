from fastapi import APIRouter, HTTPException
from backend.app.models.watchlist import UserWatchlist, WatchlistSymbolRequest
from backend.app.services.watchlist.store import watchlist_store
from backend.app.services.market_data.store import central_store
from backend.app.services.analytics.anomaly_detector import AnomalyDetector

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


@router.get("", response_model=dict)
async def get_user_watchlist(user_id: str = "default_user"):
    """Fetch user's watchlist enriched with latest market prices and attention scores"""
    wl: UserWatchlist = watchlist_store.get_watchlist(user_id)
    benchmark = central_store.get_benchmark()

    enriched_items = []
    for sym in wl.symbols:
        snap = central_store.get_latest(sym)
        if snap:
            eval_res = AnomalyDetector.evaluate(snap, benchmark)
            enriched_items.append(
                {
                    "symbol": snap.symbol,
                    "company_name": snap.company_name,
                    "exchange": snap.exchange,
                    "current_price": snap.current_price,
                    "change": snap.change,
                    "change_percent": snap.change_percent,
                    "volume": snap.volume,
                    "rvol": snap.rvol,
                    "urgency_score": eval_res.urgency_score,
                    "requires_attention": eval_res.requires_attention,
                    "primary_driver": eval_res.primary_driver,
                    "signals": eval_res.signals,
                    "upper_circuit": snap.price_band.upper_circuit,
                    "lower_circuit": snap.price_band.lower_circuit,
                    "is_near_upper_circuit": snap.is_near_upper_circuit(1.0),
                    "is_near_lower_circuit": snap.is_near_lower_circuit(1.0),
                    "week_52_high": snap.week_52_high,
                    "week_52_low": snap.week_52_low,
                    "timestamp": snap.timestamp,
                }
            )

    # Sort descending by urgency score (attention ranking)
    enriched_items.sort(key=lambda x: x["urgency_score"], reverse=True)

    return {
        "user_id": wl.user_id,
        "name": wl.name,
        "last_seen_at": wl.last_seen_at,
        "total_symbols": len(enriched_items),
        "high_attention_count": sum(1 for item in enriched_items if item["requires_attention"]),
        "benchmark": benchmark,
        "items": enriched_items,
    }


import time

# Bot protection: max 20 additions per 60 seconds per user
_recent_adds: dict[str, list[float]] = {}
MAX_WATCHLIST_CAPACITY = 100


@router.post("/symbols")
async def add_symbol_to_watchlist(req: WatchlistSymbolRequest, user_id: str = "default_user"):
    """Add a symbol to the watchlist, dynamically registering with market provider if new"""
    from backend.app.services.market_data.factory import get_market_provider

    # 1. Capacity check (Generous 100 stocks)
    current_wl = watchlist_store.get_watchlist(user_id)
    if len(current_wl.symbols) >= MAX_WATCHLIST_CAPACITY:
        raise HTTPException(
            status_code=400,
            detail=f"Watchlist capacity limit reached (maximum {MAX_WATCHLIST_CAPACITY} stocks)."
        )

    # 2. Bot throttle (Sliding window: max 20 adds per 60 seconds)
    now = time.time()
    user_adds = [t for t in _recent_adds.get(user_id, []) if now - t < 60.0]
    if len(user_adds) >= 20:
        raise HTTPException(
            status_code=429,
            detail="Too many symbols added rapidly. Please slow down."
        )
    user_adds.append(now)
    _recent_adds[user_id] = user_adds

    sym = req.symbol.strip().upper()
    snap = central_store.get_latest(sym)

    if not snap:
        provider = get_market_provider()
        snap = await provider.register_symbol(sym)
        if snap:
            central_store.update_ticker(snap, force=True)

    if not snap:
        raise HTTPException(
            status_code=400,
            detail=f"Symbol '{sym}' could not be resolved or found in the market feed."
        )

    updated_wl = watchlist_store.add_symbol(sym, user_id=user_id)
    return {"status": "success", "symbols": updated_wl.symbols, "added_ticker": snap}


@router.delete("/symbols/{symbol}")
async def remove_symbol_from_watchlist(symbol: str, user_id: str = "default_user"):
    """Remove a symbol from the watchlist"""
    updated_wl = watchlist_store.remove_symbol(symbol, user_id=user_id)
    return {"status": "success", "symbols": updated_wl.symbols}


@router.post("/acknowledge")
async def acknowledge_session(user_id: str = "default_user"):
    """
    1-Click Catch-Up: Updates last_seen_at to now.
    Subsequent deltas will measure from this new checkpoint.
    """
    updated_wl = watchlist_store.acknowledge_session(user_id=user_id)
    return {
        "status": "success",
        "message": "Session checkpoint synced to current timestamp.",
        "last_seen_at": updated_wl.last_seen_at,
    }

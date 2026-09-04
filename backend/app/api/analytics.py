from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from backend.app.models.signals import AnomalyEvaluation, WatchlistDeltaReport
from backend.app.services.analytics.anomaly_detector import AnomalyDetector
from backend.app.services.analytics.diff_engine import CheckpointDiffEngine
from backend.app.services.market_data.store import central_store

router = APIRouter(prefix="/api/analytics", tags=["analytics"])
diff_engine = CheckpointDiffEngine(central_store)


@router.get("/evaluate/{symbol}", response_model=AnomalyEvaluation)
async def evaluate_symbol(symbol: str):
    """Evaluate anomaly signals and compute 0-100 Urgency Score for a ticker"""
    snap = central_store.get_latest(symbol.upper())
    if not snap:
        raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found in market feed")

    benchmark = central_store.get_benchmark()
    return AnomalyDetector.evaluate(snap, benchmark)


@router.get("/diff", response_model=WatchlistDeltaReport)
async def get_session_diff(
    minutes_ago: Optional[int] = Query(default=None, ge=1, le=10080, description="Minutes away from now"),
    last_seen_at: Optional[datetime] = Query(default=None, description="ISO timestamp of last visit"),
    symbols: Optional[str] = Query(default=None, description="Comma-separated symbols list (optional)"),
):
    """
    Compute deterministic delta between last visit and now.
    Specify either 'minutes_ago' (e.g. 60) or 'last_seen_at' timestamp.
    """
    if last_seen_at is None:
        if minutes_ago is None:
            minutes_ago = 60  # Default to 1 hour away if unspecified
        last_seen_at = datetime.now() - timedelta(minutes=minutes_ago)

    symbol_list = [s.strip().upper() for s in symbols.split(",")] if symbols else None
    return diff_engine.compute_diff(last_seen_at=last_seen_at, symbols=symbol_list)


@router.get("/summary")
async def get_market_attention_summary():
    """Returns all tracked symbols sorted by Urgency Score (0 - 100)"""
    all_snaps = central_store.get_all_latest()
    benchmark = central_store.get_benchmark()

    evaluations = []
    for snap in all_snaps.values():
        ev = AnomalyDetector.evaluate(snap, benchmark)
        evaluations.append(
            {
                "symbol": snap.symbol,
                "company_name": snap.company_name,
                "current_price": snap.current_price,
                "change": snap.change,
                "change_percent": snap.change_percent,
                "urgency_score": ev.urgency_score,
                "primary_driver": ev.primary_driver,
                "signals": ev.signals,
                "requires_attention": ev.requires_attention,
            }
        )

    # Sort descending by urgency score
    evaluations.sort(key=lambda x: x["urgency_score"], reverse=True)
    return {
        "timestamp": datetime.now(),
        "total_tracked": len(evaluations),
        "high_attention_count": sum(1 for e in evaluations if e["requires_attention"]),
        "evaluations": evaluations,
    }

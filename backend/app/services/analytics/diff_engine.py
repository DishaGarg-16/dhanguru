from datetime import datetime, timedelta
from typing import Optional
from backend.app.models.signals import (
    SessionDelta,
    WatchlistDeltaReport,
)
from backend.app.services.analytics.anomaly_detector import AnomalyDetector
from backend.app.services.market_data.store import CentralTickerStore


class CheckpointDiffEngine:
    """
    Computes deterministic state diffs between a user's last session checkpoint
    and the current market state.
    """

    def __init__(self, store: CentralTickerStore):
        self.store = store

    @staticmethod
    def format_duration(seconds: int) -> str:
        """Format elapsed seconds into human readable duration string"""
        if seconds < 60:
            return f"{seconds}s"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes}m"
        hours = minutes // 60
        remaining_mins = minutes % 60
        if remaining_mins == 0:
            return f"{hours}h"
        return f"{hours}h {remaining_mins}m"

    def compute_diff(
        self,
        last_seen_at: datetime,
        symbols: Optional[list[str]] = None,
    ) -> WatchlistDeltaReport:
        now = datetime.now()
        duration_seconds = max(0, int((now - last_seen_at).total_seconds()))
        duration_human = self.format_duration(duration_seconds)

        all_latest = self.store.get_all_latest()
        tracked_symbols = symbols if symbols else list(all_latest.keys())

        benchmark = self.store.get_benchmark()
        benchmark_chg = benchmark.change_percent if benchmark else 0.0

        top_attention: list[SessionDelta] = []
        calm_stocks: list[SessionDelta] = []

        for sym in tracked_symbols:
            curr_snap = all_latest.get(sym.upper())
            if not curr_snap:
                continue

            # Fetch snapshot at or before last_seen_at
            past_snap = self.store.get_snapshot_at_or_before(sym, last_seen_at)
            price_then = past_snap.current_price if past_snap else curr_snap.prev_close
            vol_then = past_snap.volume if past_snap else 0

            # Delta metrics
            price_now = curr_snap.current_price
            price_change = round(price_now - price_then, 2)
            price_change_pct = round((price_change / price_then) * 100, 2) if price_then > 0 else 0.0
            volume_added = max(0, curr_snap.volume - vol_then)

            # Evaluate attention
            eval_res = AnomalyDetector.evaluate(curr_snap, benchmark)
            is_meaningful = eval_res.requires_attention or abs(price_change_pct) >= 2.0

            delta = SessionDelta(
                symbol=curr_snap.symbol,
                company_name=curr_snap.company_name,
                price_then=price_then,
                price_now=price_now,
                price_change=price_change,
                price_change_pct=price_change_pct,
                volume_accumulated_while_away=volume_added,
                urgency_score=eval_res.urgency_score,
                signals=eval_res.signals,
                is_meaningful_change=is_meaningful,
            )

            if is_meaningful:
                top_attention.append(delta)
            else:
                calm_stocks.append(delta)

        # Sort top attention by urgency score descending
        top_attention.sort(key=lambda x: x.urgency_score, reverse=True)
        # Sort calm stocks by symbol name
        calm_stocks.sort(key=lambda x: x.symbol)

        return WatchlistDeltaReport(
            duration_away_seconds=duration_seconds,
            duration_away_human=duration_human,
            last_seen_at=last_seen_at,
            current_time=now,
            total_tracked=len(tracked_symbols),
            meaningful_changes_count=len(top_attention),
            benchmark_symbol="NIFTY50",
            benchmark_change_pct=benchmark_chg,
            top_attention=top_attention,
            calm_stocks=calm_stocks,
        )

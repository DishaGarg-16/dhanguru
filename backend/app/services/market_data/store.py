from collections import deque
from datetime import datetime
from typing import Optional
from backend.app.models.ticker import TickerSnapshot, BenchmarkSnapshot


class CentralTickerStore:
    """
    Central in-memory store for market snapshots and rolling tick history.
    Decouples market feed ingestion from individual user watchlist queries.
    """

    def __init__(self, history_limit: int = 300):
        self.history_limit = history_limit
        # Latest snapshot per symbol
        self._latest: dict[str, TickerSnapshot] = {}
        # Rolling circular buffer of past snapshots per symbol (for delta calculations)
        self._history: dict[str, deque[TickerSnapshot]] = {}
        self._benchmark: Optional[BenchmarkSnapshot] = None
        self._frozen: bool = False
        self._frozen_at: Optional[datetime] = None

    def freeze(self, timestamp: Optional[datetime] = None) -> None:
        """Freeze store to lock official closing prices and reject incoming tick drift"""
        self._frozen = True
        self._frozen_at = timestamp or datetime.now()

    def unfreeze(self) -> None:
        """Unfreeze store to allow live or simulated ticks"""
        self._frozen = False
        self._frozen_at = None

    @property
    def is_frozen(self) -> bool:
        return self._frozen

    @property
    def frozen_at(self) -> Optional[datetime]:
        return self._frozen_at

    def update_ticker(self, snapshot: TickerSnapshot, force: bool = False) -> bool:
        """Store new tick snapshot in latest registry and circular history buffer.
        Returns False if update was rejected due to freeze lock."""
        if self._frozen and not force:
            return False

        sym = snapshot.symbol.upper()
        self._latest[sym] = snapshot

        if sym not in self._history:
            self._history[sym] = deque(maxlen=self.history_limit)
        self._history[sym].append(snapshot)
        return True

    def update_benchmark(self, snapshot: BenchmarkSnapshot) -> None:
        self._benchmark = snapshot

    def get_latest(self, symbol: str) -> Optional[TickerSnapshot]:
        return self._latest.get(symbol.upper())

    def get_all_latest(self) -> dict[str, TickerSnapshot]:
        return self._latest.copy()

    def get_benchmark(self) -> Optional[BenchmarkSnapshot]:
        return self._benchmark

    def get_snapshot_at_or_before(self, symbol: str, target_time: datetime) -> Optional[TickerSnapshot]:
        """
        Retrieve historical snapshot closest to (but <=) target_time.
        Enables deterministic time-travel diffing.
        """
        sym = symbol.upper()
        history = self._history.get(sym)
        if not history:
            return self._latest.get(sym)

        # Search backwards from newest to find snapshot at or before target_time
        for snap in reversed(history):
            if snap.timestamp <= target_time:
                return snap

        # If all snapshots are newer than target_time, return the oldest available
        return history[0]


# Shared singleton instance
central_store = CentralTickerStore()

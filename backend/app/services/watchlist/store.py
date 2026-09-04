import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from backend.app.models.watchlist import UserWatchlist


DEFAULT_SYMBOLS = [
    "ZOMATO",
    "TRENT",
    "TATAMOTORS",
    "RELIANCE",
    "HDFCBANK",
    "INFY",
    "ITC",
]


class WatchlistStore:
    """
    Manages user watchlists and session checkpoints with persistent storage.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or (Path(__file__).resolve().parent.parent.parent.parent / ".watchlist_data.json")
        self._watchlists: dict[str, UserWatchlist] = {}
        self._load()

    def _load(self) -> None:
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for uid, item in data.items():
                        self._watchlists[uid] = UserWatchlist(
                            user_id=item["user_id"],
                            name=item.get("name", "Primary Watchlist"),
                            symbols=item.get("symbols", DEFAULT_SYMBOLS),
                            last_seen_at=datetime.fromisoformat(item["last_seen_at"]),
                            updated_at=datetime.fromisoformat(item["updated_at"]),
                        )
                return
            except Exception:
                pass

        # Pre-seed default user with last_seen_at 2 hours ago (provides instant demo deltas)
        initial_checkpoint = datetime.now() - timedelta(hours=2, minutes=15)
        self._watchlists["default_user"] = UserWatchlist(
            user_id="default_user",
            name="Primary Watchlist",
            symbols=DEFAULT_SYMBOLS.copy(),
            last_seen_at=initial_checkpoint,
            updated_at=datetime.now(),
        )
        self._save()

    def _save(self) -> None:
        try:
            serialized = {}
            for uid, wl in self._watchlists.items():
                serialized[uid] = {
                    "user_id": wl.user_id,
                    "name": wl.name,
                    "symbols": wl.symbols,
                    "last_seen_at": wl.last_seen_at.isoformat(),
                    "updated_at": wl.updated_at.isoformat(),
                }
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(serialized, f, indent=2)
        except Exception:
            pass

    def get_watchlist(self, user_id: str = "default_user") -> UserWatchlist:
        if user_id not in self._watchlists:
            self._watchlists[user_id] = UserWatchlist(
                user_id=user_id,
                name="Primary Watchlist",
                symbols=DEFAULT_SYMBOLS.copy(),
                last_seen_at=datetime.now() - timedelta(hours=2),
                updated_at=datetime.now(),
            )
            self._save()
        return self._watchlists[user_id]

    def add_symbol(self, symbol: str, user_id: str = "default_user") -> UserWatchlist:
        wl = self.get_watchlist(user_id)
        sym = symbol.strip().upper()
        if sym not in wl.symbols:
            wl.symbols.append(sym)
            wl.updated_at = datetime.now()
            self._save()
        return wl

    def remove_symbol(self, symbol: str, user_id: str = "default_user") -> UserWatchlist:
        wl = self.get_watchlist(user_id)
        sym = symbol.strip().upper()
        if sym in wl.symbols:
            wl.symbols.remove(sym)
            wl.updated_at = datetime.now()
            self._save()
        return wl

    def acknowledge_session(self, user_id: str = "default_user") -> UserWatchlist:
        """Mark user as 'caught up', resetting checkpoint timestamp to now"""
        wl = self.get_watchlist(user_id)
        wl.last_seen_at = datetime.now()
        wl.updated_at = datetime.now()
        self._save()
        return wl


watchlist_store = WatchlistStore()

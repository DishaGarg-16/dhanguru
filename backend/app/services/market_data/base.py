from abc import ABC, abstractmethod
from typing import Optional, Callable, Awaitable
from backend.app.models.ticker import TickerSnapshot, BenchmarkSnapshot


class BaseMarketProvider(ABC):
    """Abstract interface for market data providers (simulated or real)"""

    @abstractmethod
    async def get_ticker(self, symbol: str) -> Optional[TickerSnapshot]:
        """Fetch latest snapshot for a single symbol"""
        pass

    @abstractmethod
    async def get_all_tickers(self) -> dict[str, TickerSnapshot]:
        """Fetch latest snapshot for all tracked symbols"""
        pass

    @abstractmethod
    async def get_benchmark(self) -> BenchmarkSnapshot:
        """Fetch latest snapshot for benchmark index (e.g., NIFTY 50)"""
        pass

    @abstractmethod
    async def start(self, on_tick_callback: Optional[Callable[[TickerSnapshot], Awaitable[None]]] = None) -> None:
        """Start provider feed or background simulation loop"""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop provider feed"""
        pass

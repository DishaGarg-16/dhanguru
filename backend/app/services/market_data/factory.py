import asyncio
import logging
from typing import Optional, Callable, Awaitable

from backend.app.core.config import settings
from backend.app.core.schedule import MarketScheduleManager
from backend.app.models.ticker import TickerSnapshot, BenchmarkSnapshot
from backend.app.services.market_data.base import BaseMarketProvider
from backend.app.services.market_data.simulator import IndianMarketSimulator
from backend.app.services.market_data.live import LiveMarketProvider

logger = logging.getLogger(__name__)


class HybridMarketProvider(BaseMarketProvider):
    """
    Intelligent Adaptive Hybrid Provider (AUTO Mode).
    - When market is OPEN (09:15 - 15:30 IST, Mon - Fri): streams real live exchange data.
    - When market is CLOSED (after-hours, weekends): automatically switches to simulated
      market replay so evaluators and developers always have an active, interactive stream.
    """

    def __init__(
        self,
        live_provider: Optional[LiveMarketProvider] = None,
        simulator: Optional[IndianMarketSimulator] = None,
    ):
        self.live_provider = live_provider or LiveMarketProvider(poll_interval=settings.LIVE_POLL_INTERVAL_SEC)
        self.simulator = simulator or IndianMarketSimulator(update_interval=settings.MOCK_UPDATE_INTERVAL_SEC)

        self._active_provider: BaseMarketProvider = self.simulator
        self._running = False
        self._supervisor_task: Optional[asyncio.Task] = None
        self._callback: Optional[Callable[[TickerSnapshot], Awaitable[None]]] = None

    @property
    def active_mode(self) -> str:
        """Return label of currently running sub-provider"""
        return "LIVE" if self._active_provider is self.live_provider else "SIMULATOR_REPLAY"

    async def _handle_tick(self, snap: TickerSnapshot) -> None:
        if self._callback:
            await self._callback(snap)

    async def _sync_real_market_baseline(self) -> None:
        """Fetch actual market closing quotes for all symbols to seed the simulator baseline"""
        try:
            logger.info("HybridMarketProvider: Synchronizing live/closing market quotes to seed simulator baseline...")
            bench = await self.live_provider.fetch_benchmark_quote()
            if bench and bench.current_value > 0:
                self.simulator._benchmark = bench

            syms = list(self.live_provider.symbols)
            tasks = [self.live_provider.fetch_ticker_quote(sym) for sym in syms]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for sym, res in zip(syms, results):
                if isinstance(res, TickerSnapshot) and res.current_price > 0:
                    self.simulator._tickers[sym] = res.model_copy()
                    logger.info("Seeded simulator for %s with market price: %.2f", sym, res.current_price)
        except Exception as e:
            logger.warning("Could not sync live quotes to simulator baseline: %s", e)

    async def _supervise_loop(self) -> None:
        """Periodic background supervisor checking market hours and toggling providers"""
        while self._running:
            try:
                await asyncio.sleep(30.0)
                if not self._running:
                    break

                is_open = MarketScheduleManager.is_market_open()
                target_provider = self.live_provider if is_open else self.simulator

                if target_provider is not self._active_provider:
                    logger.info("Market session changed. Transitioning feed to %s",
                                "LIVE" if is_open else "SIMULATOR_REPLAY")
                    # Stop previous provider
                    await self._active_provider.stop()
                    # When switching to simulator, copy over latest live snapshots
                    if target_provider is self.simulator:
                        for sym, snap in self.live_provider._tickers.items():
                            if snap and snap.current_price > 0:
                                self.simulator._tickers[sym] = snap.model_copy()
                    # Start target provider
                    self._active_provider = target_provider
                    await self._active_provider.start(on_tick_callback=self._handle_tick)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("Error in HybridMarketProvider supervisor: %s", e)

    async def get_ticker(self, symbol: str) -> Optional[TickerSnapshot]:
        return await self._active_provider.get_ticker(symbol)

    async def get_all_tickers(self) -> dict[str, TickerSnapshot]:
        return await self._active_provider.get_all_tickers()

    async def get_benchmark(self) -> BenchmarkSnapshot:
        return await self._active_provider.get_benchmark()

    async def start(self, on_tick_callback: Optional[Callable[[TickerSnapshot], Awaitable[None]]] = None) -> None:
        if self._running:
            return
        self._running = True
        self._callback = on_tick_callback

        # Determine which provider should run at startup
        is_open = MarketScheduleManager.is_market_open()

        # If market is closed, fetch actual market closing quotes first to seed simulator
        if not is_open:
            await self._sync_real_market_baseline()

        self._active_provider = self.live_provider if is_open else self.simulator
        logger.info("HybridMarketProvider starting with mode: %s (is_market_open=%s)",
                    self.active_mode, is_open)

        await self._active_provider.start(on_tick_callback=self._handle_tick)
        self._supervisor_task = asyncio.create_task(self._supervise_loop())

    async def stop(self) -> None:
        self._running = False
        if self._supervisor_task and not self._supervisor_task.done():
            self._supervisor_task.cancel()
            try:
                await self._supervisor_task
            except asyncio.CancelledError:
                pass
            self._supervisor_task = None

        await self._active_provider.stop()

    async def register_symbol(self, symbol: str) -> Optional[TickerSnapshot]:
        """Register on both providers so transitions between live and simulator are seamless"""
        sym = symbol.upper()
        live_snap = await self.live_provider.register_symbol(sym)
        sim_snap = await self.simulator.register_symbol(sym)
        if live_snap and live_snap.current_price > 0:
            self.simulator._tickers[sym] = live_snap.model_copy()
            sim_snap = self.simulator._tickers[sym]
        return live_snap if self._active_provider is self.live_provider else (sim_snap or live_snap)

    @property
    def _tickers(self) -> dict[str, TickerSnapshot]:
        return getattr(self._active_provider, "_tickers", self.simulator._tickers)

    def trigger_circuit_approach(self, symbol: str, upper: bool = True) -> TickerSnapshot:
        if hasattr(self._active_provider, "trigger_circuit_approach"):
            return self._active_provider.trigger_circuit_approach(symbol, upper=upper)
        return self.simulator.trigger_circuit_approach(symbol, upper=upper)

    def trigger_52w_breakout(self, symbol: str) -> TickerSnapshot:
        if hasattr(self._active_provider, "trigger_52w_breakout"):
            return self._active_provider.trigger_52w_breakout(symbol)
        return self.simulator.trigger_52w_breakout(symbol)

    def trigger_volume_surge(self, symbol: str, multiplier: float = 3.0) -> TickerSnapshot:
        if hasattr(self._active_provider, "trigger_volume_surge"):
            return self._active_provider.trigger_volume_surge(symbol, multiplier=multiplier)
        return self.simulator.trigger_volume_surge(symbol, multiplier=multiplier)


_provider_instance: Optional[BaseMarketProvider] = None


def get_market_provider(mode: Optional[str] = None, force_new: bool = False) -> BaseMarketProvider:
    """
    Factory creating appropriate market data provider based on requested mode:
    - "AUTO": Intelligent hybrid (Live during market hours, simulator replay outside)
    - "LIVE": Real exchange data feed (freezes on close)
    - "MOCK": Pure deterministic simulator 24/7 (guaranteed offline presentation mode)
    """
    global _provider_instance
    if _provider_instance is not None and not force_new and mode is None:
        return _provider_instance

    selected_mode = (mode or settings.MARKET_DATA_PROVIDER).upper()

    if selected_mode == "LIVE":
        inst = LiveMarketProvider(poll_interval=settings.LIVE_POLL_INTERVAL_SEC)
    elif selected_mode == "AUTO":
        inst = HybridMarketProvider()
    else:  # Default to MOCK for safety and determinism
        inst = IndianMarketSimulator(update_interval=settings.MOCK_UPDATE_INTERVAL_SEC)

    if mode is None and not force_new:
        _provider_instance = inst
    return inst


def reset_market_provider():
    """Reset cached provider instance (useful for unit testing)"""
    global _provider_instance
    _provider_instance = None

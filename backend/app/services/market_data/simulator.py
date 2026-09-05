import asyncio
import random
from datetime import datetime
from typing import Optional, Callable, Awaitable
from backend.app.models.ticker import TickerSnapshot, PriceBand, BenchmarkSnapshot
from backend.app.services.market_data.base import BaseMarketProvider


# Initial seed data modeled after actual Indian equities on the NSE
SEED_UNIVERSE = {
    "ZOMATO": {
        "company_name": "Zomato Ltd",
        "base_price": 258.40,
        "band_pct": 5.0,
        "avg_volume_20d": 42500000,
        "atr_14": 8.50,
        "week_52_high": 268.00,
        "week_52_low": 98.20,
    },
    "ETERNAL": {
        "company_name": "Eternal Ltd (Zomato)",
        "base_price": 258.40,
        "band_pct": 5.0,
        "avg_volume_20d": 42500000,
        "atr_14": 8.50,
        "week_52_high": 268.00,
        "week_52_low": 98.20,
    },
    "TRENT": {
        "company_name": "Trent Ltd (Tata Retail)",
        "base_price": 7180.00,
        "band_pct": 5.0,
        "avg_volume_20d": 2100000,
        "atr_14": 220.00,
        "week_52_high": 7510.00,
        "week_52_low": 2850.00,
    },
    "TATAMOTORS": {
        "company_name": "Tata Motors Ltd",
        "base_price": 985.00,
        "band_pct": 10.0,
        "avg_volume_20d": 18400000,
        "atr_14": 24.50,
        "week_52_high": 1179.00,
        "week_52_low": 680.00,
    },
    "TMPV": {
        "company_name": "Tata Motors Passenger Vehicles Ltd",
        "base_price": 985.00,
        "band_pct": 10.0,
        "avg_volume_20d": 18400000,
        "atr_14": 24.50,
        "week_52_high": 1179.00,
        "week_52_low": 680.00,
    },
    "RELIANCE": {
        "company_name": "Reliance Industries Ltd",
        "base_price": 2985.00,
        "band_pct": 10.0,
        "avg_volume_20d": 9800000,
        "atr_14": 42.00,
        "week_52_high": 3217.00,
        "week_52_low": 2220.00,
    },
    "HDFCBANK": {
        "company_name": "HDFC Bank Ltd",
        "base_price": 1642.00,
        "band_pct": 10.0,
        "avg_volume_20d": 24500000,
        "atr_14": 26.00,
        "week_52_high": 1794.00,
        "week_52_low": 1363.00,
    },
    "INFY": {
        "company_name": "Infosys Ltd",
        "base_price": 1845.00,
        "band_pct": 10.0,
        "avg_volume_20d": 12200000,
        "atr_14": 31.00,
        "week_52_high": 1991.00,
        "week_52_low": 1358.00,
    },
    "ITC": {
        "company_name": "ITC Ltd",
        "base_price": 482.50,
        "band_pct": 10.0,
        "avg_volume_20d": 16800000,
        "atr_14": 6.80,
        "week_52_high": 528.00,
        "week_52_low": 399.00,
    },
}


class IndianMarketSimulator(BaseMarketProvider):
    """
    High-fidelity deterministic Indian market simulator.
    Simulates price drift, volume accumulation, circuit limits, and test anomalies.
    """

    def __init__(self, update_interval: float = 1.0):
        self.update_interval = update_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._callback: Optional[Callable[[TickerSnapshot], Awaitable[None]]] = None

        # State storage
        self._tickers: dict[str, TickerSnapshot] = {}
        self._benchmark = BenchmarkSnapshot(
            symbol="NIFTY50",
            current_value=24850.00,
            change=28.50,
            change_percent=0.11,
            timestamp=datetime.now(),
        )

        self._initialize_seed_data()

    def _initialize_seed_data(self) -> None:
        """Initialize initial state with calculated circuit limits"""
        for sym, meta in SEED_UNIVERSE.items():
            base = meta["base_price"]
            band_pct = meta["band_pct"]
            upper = round(base * (1 + band_pct / 100), 2)
            lower = round(base * (1 - band_pct / 100), 2)

            price_band = PriceBand(
                band_percent=band_pct,
                upper_circuit=upper,
                lower_circuit=lower,
            )

            # Starting intraday range
            open_p = base
            high_p = round(base * (1 + random.uniform(0.002, 0.01)), 2)
            low_p = round(base * (1 - random.uniform(0.002, 0.01)), 2)
            curr_p = base
            chg = round(curr_p - base, 2)
            chg_pct = round((chg / base) * 100, 2)

            # Start with ~40-60% of average daily volume
            starting_vol = int(meta["avg_volume_20d"] * random.uniform(0.4, 0.6))

            self._tickers[sym] = TickerSnapshot(
                symbol=sym,
                company_name=meta["company_name"],
                exchange="NSE",
                current_price=curr_p,
                open_price=open_p,
                high_price=high_p,
                low_price=low_p,
                prev_close=base,
                change=chg,
                change_percent=chg_pct,
                volume=starting_vol,
                avg_volume_20d=meta["avg_volume_20d"],
                atr_14=meta["atr_14"],
                week_52_high=meta["week_52_high"],
                week_52_low=meta["week_52_low"],
                price_band=price_band,
                timestamp=datetime.now(),
            )

    async def get_ticker(self, symbol: str) -> Optional[TickerSnapshot]:
        return self._tickers.get(symbol.upper())

    async def get_all_tickers(self) -> dict[str, TickerSnapshot]:
        return self._tickers.copy()

    async def get_benchmark(self) -> BenchmarkSnapshot:
        return self._benchmark

    def advance_tick(self, symbol: str) -> TickerSnapshot:
        """Simulate a single market tick for a symbol within realistic bounds"""
        snap = self._tickers[symbol]

        # Standard random walk with tiny mean-reversion drift (-0.25% to +0.25%)
        pct_move = random.gauss(0, 0.0015)
        new_price = round(snap.current_price * (1 + pct_move), 2)

        # Enforce exchange circuit limits (strictly clamped)
        new_price = min(new_price, snap.price_band.upper_circuit)
        new_price = max(new_price, snap.price_band.lower_circuit)

        new_high = max(snap.high_price, new_price)
        new_low = min(snap.low_price, new_price)
        chg = round(new_price - snap.prev_close, 2)
        chg_pct = round((chg / snap.prev_close) * 100, 2)

        # Incremental trade volume (between 500 and 5,000 shares per tick)
        tick_vol = random.randint(500, 5000)
        new_volume = snap.volume + tick_vol

        updated = snap.model_copy(
            update={
                "current_price": new_price,
                "high_price": new_high,
                "low_price": new_low,
                "change": chg,
                "change_percent": chg_pct,
                "volume": new_volume,
                "timestamp": datetime.now(),
            }
        )
        self._tickers[symbol] = updated
        return updated

    # Anomaly testing helpers (Deterministic triggers)
    def trigger_circuit_approach(self, symbol: str, upper: bool = True) -> TickerSnapshot:
        """Force price to within 0.5% of upper or lower circuit for deterministic testing"""
        snap = self._tickers[symbol.upper()]
        if upper:
            target_price = round(snap.price_band.upper_circuit * 0.996, 2)
        else:
            target_price = round(snap.price_band.lower_circuit * 1.004, 2)

        chg = round(target_price - snap.prev_close, 2)
        chg_pct = round((chg / snap.prev_close) * 100, 2)
        updated = snap.model_copy(
            update={
                "current_price": target_price,
                "high_price": max(snap.high_price, target_price),
                "low_price": min(snap.low_price, target_price),
                "change": chg,
                "change_percent": chg_pct,
                "timestamp": datetime.now(),
            }
        )
        self._tickers[symbol.upper()] = updated
        return updated

    def trigger_volume_surge(self, symbol: str, multiplier: float = 3.2) -> TickerSnapshot:
        """Force accumulated volume to surge past 20d average for deterministic testing"""
        snap = self._tickers[symbol.upper()]
        surge_vol = int(snap.avg_volume_20d * multiplier)
        updated = snap.model_copy(
            update={
                "volume": surge_vol,
                "timestamp": datetime.now(),
            }
        )
        self._tickers[symbol.upper()] = updated
        return updated

    def trigger_52w_breakout(self, symbol: str) -> TickerSnapshot:
        """Force price to cross its 52-week high"""
        snap = self._tickers[symbol.upper()]
        breakout_price = round(snap.week_52_high * 1.002, 2)
        chg = round(breakout_price - snap.prev_close, 2)
        chg_pct = round((chg / snap.prev_close) * 100, 2)
        updated = snap.model_copy(
            update={
                "current_price": breakout_price,
                "high_price": breakout_price,
                "week_52_high": breakout_price,
                "change": chg,
                "change_percent": chg_pct,
                "timestamp": datetime.now(),
            }
        )
        self._tickers[symbol.upper()] = updated
        return updated

    async def _simulation_loop(self) -> None:
        """Background loop continuously simulating market activity"""
        symbols = list(self._tickers.keys())
        while self._running:
            # Pick 1-2 random symbols to tick
            num_ticks = random.randint(1, 2)
            selected = random.sample(symbols, num_ticks)

            for sym in selected:
                updated = self.advance_tick(sym)
                if self._callback:
                    try:
                        await self._callback(updated)
                    except Exception:
                        pass

            # Nifty benchmark tiny random drift
            bench_move = random.gauss(0, 0.0003)
            new_val = round(self._benchmark.current_value * (1 + bench_move), 2)
            self._benchmark = self._benchmark.model_copy(
                update={
                    "current_value": new_val,
                    "change": round(new_val - 24821.50, 2),
                    "change_percent": round(((new_val - 24821.50) / 24821.50) * 100, 2),
                    "timestamp": datetime.now(),
                }
            )

            await asyncio.sleep(self.update_interval)

    async def start(self, on_tick_callback: Optional[Callable[[TickerSnapshot], Awaitable[None]]] = None) -> None:
        if self._running:
            return
        self._running = True
        self._callback = on_tick_callback
        self._task = asyncio.create_task(self._simulation_loop())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def register_symbol(self, symbol: str) -> Optional[TickerSnapshot]:
        """Register and immediately seed a new symbol in the simulator"""
        sym = symbol.upper()
        if sym in self._tickers:
            return self._tickers[sym]

        meta = SEED_UNIVERSE.get(sym, {
            "company_name": sym,
            "base_price": 1000.0,
            "band_pct": 10.0,
            "avg_volume_20d": 5000000,
            "atr_14": 15.0,
            "week_52_high": 1200.0,
            "week_52_low": 800.0,
        })
        base = meta["base_price"]
        band_pct = meta["band_pct"]
        upper = round(base * (1 + band_pct / 100), 2)
        lower = round(base * (1 - band_pct / 100), 2)

        snap = TickerSnapshot(
            symbol=sym,
            company_name=meta["company_name"],
            exchange="NSE",
            current_price=base,
            open_price=base,
            high_price=base,
            low_price=base,
            prev_close=base,
            change=0.0,
            change_percent=0.0,
            volume=int(meta["avg_volume_20d"] * 0.5),
            avg_volume_20d=meta["avg_volume_20d"],
            atr_14=meta["atr_14"],
            week_52_high=meta["week_52_high"],
            week_52_low=meta["week_52_low"],
            price_band=PriceBand(band_percent=band_pct, upper_circuit=upper, lower_circuit=lower),
            timestamp=datetime.now(),
        )
        self._tickers[sym] = snap
        return snap

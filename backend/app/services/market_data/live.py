import asyncio
import logging
from datetime import datetime
from typing import Optional, Callable, Awaitable
import httpx

from backend.app.models.ticker import TickerSnapshot, PriceBand, BenchmarkSnapshot
from backend.app.services.market_data.base import BaseMarketProvider
from backend.app.services.market_data.simulator import SEED_UNIVERSE

logger = logging.getLogger(__name__)

# Yahoo Finance mapping for Indian equities and indices
YF_SYMBOL_MAP = {
    "NIFTY50": "^NSEI",
    "SENSEX": "^BSESN",
}

# Known historical aliases for corporate actions / rebranding
YF_KNOWN_ALIASES = {
    "ZOMATO": "ETERNAL.NS",
    "TATAMOTORS": "TMPV.NS",
}

# Standard HTTP headers to avoid web scraping throttles
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


def to_yf_symbol(symbol: str) -> str:
    """Map internal symbol (e.g. RELIANCE, NIFTY50) to Yahoo Finance ticker"""
    sym = symbol.upper()
    if sym in YF_SYMBOL_MAP:
        return YF_SYMBOL_MAP[sym]
    if not sym.endswith(".NS") and not sym.endswith(".BO") and not sym.startswith("^"):
        return f"{sym}.NS"
    return sym


class LiveMarketProvider(BaseMarketProvider):
    """
    Live market data provider fetching real quotes for Indian equities
    via asynchronous Yahoo Finance chart/quote endpoints with dynamic ticker resolution.
    """

    def __init__(
        self,
        symbols: Optional[list[str]] = None,
        poll_interval: float = 5.0,
        benchmark_symbol: str = "NIFTY50",
    ):
        self.symbols = [s.upper() for s in (symbols or list(SEED_UNIVERSE.keys()))]
        self.poll_interval = poll_interval
        self.benchmark_symbol = benchmark_symbol.upper()

        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._callback: Optional[Callable[[TickerSnapshot], Awaitable[None]]] = None

        self._tickers: dict[str, TickerSnapshot] = {}
        self._benchmark: Optional[BenchmarkSnapshot] = None
        self._http_client: Optional[httpx.AsyncClient] = None

        # Dynamic symbol resolution cache & warning deduplication
        self._resolved_symbols: dict[str, str] = {}
        self._warned_symbols: set[str] = set()

        # Pre-seed initial state from SEED_UNIVERSE for instant startup
        self._initialize_fallback_cache()

    def _initialize_fallback_cache(self) -> None:
        """Pre-populate initial cache from SEED_UNIVERSE before live requests resolve"""
        for sym in self.symbols:
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

            self._tickers[sym] = TickerSnapshot(
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

        self._benchmark = BenchmarkSnapshot(
            symbol="NIFTY50",
            current_value=24850.0,
            change=0.0,
            change_percent=0.0,
            timestamp=datetime.now(),
        )

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=10.0, headers=HEADERS)
        return self._http_client

    def _get_candidate_symbols(self, sym: str) -> list[str]:
        """Generate candidate Yahoo Finance symbols in priority order"""
        if sym in self._resolved_symbols:
            return [self._resolved_symbols[sym]]

        candidates = []
        if sym in YF_SYMBOL_MAP:
            candidates.append(YF_SYMBOL_MAP[sym])
        if sym in YF_KNOWN_ALIASES:
            candidates.append(YF_KNOWN_ALIASES[sym])

        if not sym.endswith(".NS") and not sym.endswith(".BO") and not sym.startswith("^"):
            candidates.append(f"{sym}.NS")
            candidates.append(f"{sym}.BO")
        elif sym not in candidates:
            candidates.append(sym)

        return candidates

    async def search_yf_symbol(self, query: str) -> Optional[str]:
        """
        Dynamically query Yahoo Finance search/autocomplete API to resolve
        rebranded, demerged, or alias company tickers to their active Indian listing (.NS / .BO).
        """
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}&quotesCount=5&newsCount=0"
        try:
            client = await self._get_client()
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                quotes = data.get("quotes", [])
                for q in quotes:
                    cand = q.get("symbol", "")
                    if cand.endswith(".NS") or cand.endswith(".BO"):
                        return cand
                for q in quotes:
                    if q.get("quoteType") == "EQUITY":
                        return q.get("symbol")
        except Exception as e:
            logger.debug("Failed dynamic Yahoo search for %s: %s", query, e)
        return None

    def _parse_chart_result(self, sym: str, result: dict) -> Optional[TickerSnapshot]:
        meta = result.get("meta", {})
        curr_p = meta.get("regularMarketPrice")
        if curr_p is None:
            return None

        curr_p = round(float(curr_p), 2)
        prev_close = round(float(meta.get("chartPreviousClose") or meta.get("previousClose") or curr_p), 2)
        open_p = round(float(meta.get("regularMarketOpen") or prev_close), 2)
        high_p = round(float(meta.get("regularMarketDayHigh") or curr_p), 2)
        low_p = round(float(meta.get("regularMarketDayLow") or curr_p), 2)
        vol = int(meta.get("regularMarketVolume") or 0)

        # High / Low 52-week
        seed_meta = SEED_UNIVERSE.get(sym, {})
        w52_high = round(float(meta.get("fiftyTwoWeekHigh") or seed_meta.get("week_52_high") or curr_p * 1.2), 2)
        w52_low = round(float(meta.get("fiftyTwoWeekLow") or seed_meta.get("week_52_low") or curr_p * 0.8), 2)

        chg = round(curr_p - prev_close, 2)
        chg_pct = round((chg / prev_close) * 100, 2) if prev_close > 0 else 0.0

        # Circuit limits
        band_pct = float(seed_meta.get("band_pct", 10.0))
        upper_c = round(prev_close * (1 + band_pct / 100), 2)
        lower_c = round(prev_close * (1 - band_pct / 100), 2)
        price_band = PriceBand(
            band_percent=band_pct,
            upper_circuit=upper_c,
            lower_circuit=lower_c,
        )

        avg_vol = int(seed_meta.get("avg_volume_20d", max(vol, 1000000)))
        atr = float(seed_meta.get("atr_14", round(curr_p * 0.015, 2)))
        comp_name = seed_meta.get("company_name", sym)

        snap = TickerSnapshot(
            symbol=sym,
            company_name=comp_name,
            exchange="NSE",
            current_price=curr_p,
            open_price=open_p,
            high_price=high_p,
            low_price=low_p,
            prev_close=prev_close,
            change=chg,
            change_percent=chg_pct,
            volume=vol,
            avg_volume_20d=avg_vol,
            atr_14=atr,
            week_52_high=w52_high,
            week_52_low=w52_low,
            price_band=price_band,
            timestamp=datetime.now(),
        )
        self._tickers[sym] = snap
        return snap

    async def fetch_ticker_quote(self, symbol: str) -> Optional[TickerSnapshot]:
        """Fetch live quote for a single symbol from Yahoo Finance with dynamic resolution"""
        sym = symbol.upper()
        candidates = self._get_candidate_symbols(sym)

        try:
            client = await self._get_client()

            # 1. Attempt candidate symbols (.NS, .BO, known aliases)
            for cand in candidates:
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{cand}?interval=1d&range=5d"
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("chart", {}).get("result")
                    if results:
                        snap = self._parse_chart_result(sym, results[0])
                        if snap:
                            self._resolved_symbols[sym] = cand
                            return snap

            # 2. Dynamic Yahoo autocomplete search fallback if candidates returned 404
            searched_cand = await self.search_yf_symbol(sym)
            if searched_cand and searched_cand not in candidates:
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{searched_cand}?interval=1d&range=5d"
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("chart", {}).get("result")
                    if results:
                        snap = self._parse_chart_result(sym, results[0])
                        if snap:
                            self._resolved_symbols[sym] = searched_cand
                            return snap

            # 3. If all attempts failed, warn once and return cached snapshot
            if sym not in self._warned_symbols:
                logger.warning("Could not resolve active Yahoo Finance quote for %s, falling back to cached data", sym)
                self._warned_symbols.add(sym)

            return self._tickers.get(sym)

        except Exception as e:
            logger.debug("Error fetching live quote for %s: %s", sym, e)
            return self._tickers.get(sym)

    async def fetch_benchmark_quote(self) -> Optional[BenchmarkSnapshot]:
        """Fetch live benchmark (NIFTY 50) snapshot"""
        yf_sym = to_yf_symbol(self.benchmark_symbol)
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yf_sym}?interval=1d&range=5d"

        try:
            client = await self._get_client()
            resp = await client.get(url)
            if resp.status_code != 200:
                return self._benchmark

            data = resp.json()
            results = data.get("chart", {}).get("result")
            if not results:
                return self._benchmark

            meta = results[0].get("meta", {})
            curr_val = meta.get("regularMarketPrice")
            if curr_val is None:
                return self._benchmark

            curr_val = round(float(curr_val), 2)
            prev_close = round(float(meta.get("chartPreviousClose") or meta.get("previousClose") or curr_val), 2)
            chg = round(curr_val - prev_close, 2)
            chg_pct = round((chg / prev_close) * 100, 2) if prev_close > 0 else 0.0

            bench = BenchmarkSnapshot(
                symbol=self.benchmark_symbol,
                current_value=curr_val,
                change=chg,
                change_percent=chg_pct,
                timestamp=datetime.now(),
            )
            self._benchmark = bench
            return bench
        except Exception as e:
            logger.debug("Error fetching benchmark %s: %s", self.benchmark_symbol, e)
            return self._benchmark

    async def get_ticker(self, symbol: str) -> Optional[TickerSnapshot]:
        return self._tickers.get(symbol.upper())

    async def get_all_tickers(self) -> dict[str, TickerSnapshot]:
        return self._tickers.copy()

    async def get_benchmark(self) -> BenchmarkSnapshot:
        if self._benchmark is None:
            await self.fetch_benchmark_quote()
        return self._benchmark

    async def _poll_loop(self) -> None:
        """Periodic background polling loop updating quotes from live feed"""
        while self._running:
            try:
                # 1. Update benchmark
                await self.fetch_benchmark_quote()

                # 2. Update tickers sequentially or concurrently with polite delay
                for sym in self.symbols:
                    if not self._running:
                        break
                    snap = await self.fetch_ticker_quote(sym)
                    if snap and self._callback:
                        try:
                            await self._callback(snap)
                        except Exception:
                            pass
                    await asyncio.sleep(0.2)  # Polite pacing between Yahoo queries

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("Error in LiveMarketProvider loop: %s", e)

            # Wait for next poll interval
            try:
                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                break

    async def start(self, on_tick_callback: Optional[Callable[[TickerSnapshot], Awaitable[None]]] = None) -> None:
        """Start provider feed background polling loop"""
        if self._running:
            return
        self._running = True
        self._callback = on_tick_callback

        # Initial fetch of all tracked tickers
        for sym in self.symbols:
            await self.fetch_ticker_quote(sym)
        await self.fetch_benchmark_quote()

        self._task = asyncio.create_task(self._poll_loop())

    async def stop(self) -> None:
        """Stop polling loop and close HTTP client"""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None

    async def register_symbol(self, symbol: str) -> Optional[TickerSnapshot]:
        """Register and immediately fetch live quote for a new symbol"""
        sym = symbol.upper()
        if sym not in self.symbols:
            self.symbols.append(sym)

        if sym not in self._tickers:
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
            self._tickers[sym] = TickerSnapshot(
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

        snap = await self.fetch_ticker_quote(sym)
        return snap or self._tickers.get(sym)

    # Anomaly testing helpers (Deterministic triggers for evaluator testing)
    def trigger_circuit_approach(self, symbol: str, upper: bool = True) -> TickerSnapshot:
        snap = self._tickers[symbol.upper()]
        target_price = round(snap.price_band.upper_circuit * 0.996 if upper else snap.price_band.lower_circuit * 1.004, 2)
        chg = round(target_price - snap.prev_close, 2)
        chg_pct = round((chg / snap.prev_close) * 100, 2)
        updated = snap.model_copy(update={"current_price": target_price, "change": chg, "change_percent": chg_pct, "timestamp": datetime.now()})
        self._tickers[symbol.upper()] = updated
        return updated

    def trigger_52w_breakout(self, symbol: str) -> TickerSnapshot:
        snap = self._tickers[symbol.upper()]
        target_price = round(snap.week_52_high * 1.015, 2)
        chg = round(target_price - snap.prev_close, 2)
        chg_pct = round((chg / snap.prev_close) * 100, 2)
        updated = snap.model_copy(update={"current_price": target_price, "high_price": target_price, "change": chg, "change_percent": chg_pct, "timestamp": datetime.now()})
        self._tickers[symbol.upper()] = updated
        return updated

    def trigger_volume_surge(self, symbol: str, multiplier: float = 3.0) -> TickerSnapshot:
        snap = self._tickers[symbol.upper()]
        surge_volume = int(snap.avg_volume_20d * multiplier)
        updated = snap.model_copy(update={"volume": surge_volume, "timestamp": datetime.now()})
        self._tickers[symbol.upper()] = updated
        return updated

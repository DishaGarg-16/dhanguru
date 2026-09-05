import pytest
import httpx
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from backend.app.services.market_data.base import BaseMarketProvider
from backend.app.services.market_data.simulator import IndianMarketSimulator
from backend.app.services.market_data.live import LiveMarketProvider, to_yf_symbol
from backend.app.services.market_data.factory import HybridMarketProvider, get_market_provider
from backend.app.models.ticker import TickerSnapshot, BenchmarkSnapshot


def test_symbol_mapping():
    assert to_yf_symbol("RELIANCE") == "RELIANCE.NS"
    assert to_yf_symbol("ZOMATO") == "ZOMATO.NS"
    assert to_yf_symbol("NIFTY50") == "^NSEI"
    assert to_yf_symbol("SENSEX") == "^BSESN"
    assert to_yf_symbol("INFY.NS") == "INFY.NS"


def test_provider_factory_modes():
    # MOCK mode produces IndianMarketSimulator
    p_mock = get_market_provider("MOCK")
    assert isinstance(p_mock, IndianMarketSimulator)

    # LIVE mode produces LiveMarketProvider
    p_live = get_market_provider("LIVE")
    assert isinstance(p_live, LiveMarketProvider)

    # AUTO mode produces HybridMarketProvider
    p_auto = get_market_provider("AUTO")
    assert isinstance(p_auto, HybridMarketProvider)


def test_live_provider_initial_fallback_cache():
    provider = LiveMarketProvider(symbols=["RELIANCE", "ZOMATO"])
    tickers = provider._tickers
    assert "RELIANCE" in tickers
    assert "ZOMATO" in tickers

    rel = tickers["RELIANCE"]
    assert rel.symbol == "RELIANCE"
    assert rel.price_band.upper_circuit > rel.current_price
    assert rel.price_band.lower_circuit < rel.current_price
    assert rel.exchange == "NSE"


@pytest.mark.asyncio
async def test_live_provider_parsing_mocked_yahoo_response():
    provider = LiveMarketProvider(symbols=["RELIANCE"])

    mock_yahoo_data = {
        "chart": {
            "result": [
                {
                    "meta": {
                        "currency": "INR",
                        "symbol": "RELIANCE.NS",
                        "regularMarketPrice": 3020.50,
                        "chartPreviousClose": 2985.00,
                        "previousClose": 2985.00,
                        "regularMarketOpen": 2990.00,
                        "regularMarketDayHigh": 3030.00,
                        "regularMarketDayLow": 2980.00,
                        "regularMarketVolume": 11200000,
                        "fiftyTwoWeekHigh": 3217.00,
                        "fiftyTwoWeekLow": 2220.00,
                    }
                }
            ]
        }
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_yahoo_data

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_resp

    with patch.object(provider, "_get_client", AsyncMock(return_value=mock_client)):
        snap = await provider.fetch_ticker_quote("RELIANCE")

    assert snap is not None
    assert snap.symbol == "RELIANCE"
    assert snap.current_price == 3020.50
    assert snap.prev_close == 2985.00
    assert snap.change == 35.50
    assert round(snap.change_percent, 2) == 1.19
    assert snap.volume == 11200000
    assert snap.price_band.upper_circuit == round(2985.00 * 1.10, 2)


@pytest.mark.asyncio
async def test_hybrid_provider_toggles_mode_cleanly():
    hybrid = HybridMarketProvider()

    # If market is closed, active mode should be SIMULATOR_REPLAY
    with patch("backend.app.core.schedule.MarketScheduleManager.is_market_open", return_value=False):
        ticks_received = []

        async def on_tick(snap: TickerSnapshot):
            ticks_received.append(snap)

        await hybrid.start(on_tick_callback=on_tick)
        assert hybrid.active_mode == "SIMULATOR_REPLAY"
        await hybrid.stop()

    # If market is open, active mode should be LIVE
    with patch("backend.app.core.schedule.MarketScheduleManager.is_market_open", return_value=True):
        await hybrid.start()
        assert hybrid.active_mode == "LIVE"
        await hybrid.stop()

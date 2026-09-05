import pytest
from datetime import datetime, date, time
from backend.app.core.schedule import MarketScheduleManager, IST_TZ
from backend.app.services.market_data.store import CentralTickerStore
from backend.app.models.ticker import TickerSnapshot, PriceBand


def test_trading_day_and_weekend_detection():
    # Wednesday -> Trading Day
    wednesday = datetime(2026, 9, 2, 11, 0, tzinfo=IST_TZ)
    assert MarketScheduleManager.is_trading_day(wednesday) is True

    # Friday -> Trading Day
    friday = datetime(2026, 9, 4, 15, 0, tzinfo=IST_TZ)
    assert MarketScheduleManager.is_trading_day(friday) is True

    # Saturday -> Weekend
    saturday = datetime(2026, 9, 5, 12, 0, tzinfo=IST_TZ)
    assert MarketScheduleManager.is_trading_day(saturday) is False
    assert MarketScheduleManager.get_session_status(saturday) == "WEEKEND"
    assert MarketScheduleManager.is_market_open(saturday) is False

    # Sunday -> Weekend
    sunday = datetime(2026, 9, 6, 12, 0, tzinfo=IST_TZ)
    assert MarketScheduleManager.is_trading_day(sunday) is False
    assert MarketScheduleManager.get_session_status(sunday) == "WEEKEND"
    assert MarketScheduleManager.is_market_open(sunday) is False


def test_intraday_session_transitions():
    # Regular trading weekday (Wednesday, Sept 2, 2026)
    
    # 08:30 IST -> Pre-Market
    dt_pre_market = datetime(2026, 9, 2, 8, 30, tzinfo=IST_TZ)
    assert MarketScheduleManager.get_session_status(dt_pre_market) == "PRE_MARKET"
    assert MarketScheduleManager.is_market_open(dt_pre_market) is False

    # 09:05 IST -> Pre-Open Auction
    dt_pre_open = datetime(2026, 9, 2, 9, 5, tzinfo=IST_TZ)
    assert MarketScheduleManager.get_session_status(dt_pre_open) == "PRE_OPEN"
    assert MarketScheduleManager.is_market_open(dt_pre_open) is False

    # 09:15 IST -> Exact Market Open
    dt_open_exact = datetime(2026, 9, 2, 9, 15, tzinfo=IST_TZ)
    assert MarketScheduleManager.get_session_status(dt_open_exact) == "OPEN"
    assert MarketScheduleManager.is_market_open(dt_open_exact) is True

    # 13:45 IST -> Active Trading Session
    dt_midday = datetime(2026, 9, 2, 13, 45, tzinfo=IST_TZ)
    assert MarketScheduleManager.get_session_status(dt_midday) == "OPEN"
    assert MarketScheduleManager.is_market_open(dt_midday) is True

    # 15:35 IST -> Post-Market Closing Session
    dt_closing = datetime(2026, 9, 2, 15, 35, tzinfo=IST_TZ)
    assert MarketScheduleManager.get_session_status(dt_closing) == "POST_MARKET_CLOSING"
    assert MarketScheduleManager.is_market_open(dt_closing) is False

    # 17:00 IST -> Post-Market Closed
    dt_post_close = datetime(2026, 9, 2, 17, 0, tzinfo=IST_TZ)
    assert MarketScheduleManager.get_session_status(dt_post_close) == "POST_MARKET_CLOSED"
    assert MarketScheduleManager.is_market_open(dt_post_close) is False


def test_get_last_market_close_calculation():
    # Case 1: Wednesday at 18:00 IST -> Last close was today at 15:30
    wed_evening = datetime(2026, 9, 2, 18, 0, tzinfo=IST_TZ)
    last_close = MarketScheduleManager.get_last_market_close(wed_evening)
    assert last_close == datetime(2026, 9, 2, 15, 30, tzinfo=IST_TZ)

    # Case 2: Thursday at 08:00 IST -> Last close was Wednesday at 15:30
    thu_morning = datetime(2026, 9, 3, 8, 0, tzinfo=IST_TZ)
    last_close = MarketScheduleManager.get_last_market_close(thu_morning)
    assert last_close == datetime(2026, 9, 2, 15, 30, tzinfo=IST_TZ)

    # Case 3: Sunday at 14:00 IST -> Last close was Friday at 15:30
    sun_afternoon = datetime(2026, 9, 6, 14, 0, tzinfo=IST_TZ)
    last_close = MarketScheduleManager.get_last_market_close(sun_afternoon)
    assert last_close == datetime(2026, 9, 4, 15, 30, tzinfo=IST_TZ)


def test_central_ticker_store_freeze_preservation():
    store = CentralTickerStore()
    band = PriceBand(band_percent=10.0, upper_circuit=3300.0, lower_circuit=2700.0)

    snap_close = TickerSnapshot(
        symbol="RELIANCE",
        company_name="Reliance Industries",
        exchange="NSE",
        current_price=3000.0,
        open_price=2980.0,
        high_price=3010.0,
        low_price=2975.0,
        prev_close=2980.0,
        change=20.0,
        change_percent=0.67,
        volume=10000000,
        avg_volume_20d=9800000,
        atr_14=42.0,
        week_52_high=3217.0,
        week_52_low=2220.0,
        price_band=band,
        timestamp=datetime.now(),
    )

    # Update while unfrozen works
    assert store.update_ticker(snap_close) is True
    assert store.get_latest("RELIANCE").current_price == 3000.0
    assert store.is_frozen is False

    # Freeze store at market close
    store.freeze()
    assert store.is_frozen is True

    # Incoming synthetic tick attempts to change price to 3050.0
    snap_drift = snap_close.model_copy(update={"current_price": 3050.0})
    result = store.update_ticker(snap_drift)

    # Update must be rejected to preserve official close
    assert result is False
    assert store.get_latest("RELIANCE").current_price == 3000.0  # Preserved!

    # Forced update works
    store.update_ticker(snap_drift, force=True)
    assert store.get_latest("RELIANCE").current_price == 3050.0

    # Unfreeze restores normal updates
    store.unfreeze()
    assert store.is_frozen is False
    snap_next = snap_close.model_copy(update={"current_price": 3015.0})
    assert store.update_ticker(snap_next) is True
    assert store.get_latest("RELIANCE").current_price == 3015.0

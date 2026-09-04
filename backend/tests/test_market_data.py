import pytest
from datetime import datetime, timedelta
from backend.app.models.ticker import TickerSnapshot, PriceBand
from backend.app.services.market_data.simulator import IndianMarketSimulator
from backend.app.services.market_data.store import CentralTickerStore


def test_ticker_snapshot_circuit_logic():
    """Verify Indian circuit limit calculations and proximity detection"""
    band = PriceBand(band_percent=5.0, upper_circuit=210.0, lower_circuit=190.0)
    snap = TickerSnapshot(
        symbol="TEST",
        company_name="Test Ltd",
        exchange="NSE",
        current_price=209.0,  # ~0.48% from upper circuit of 210
        open_price=200.0,
        high_price=209.0,
        low_price=199.0,
        prev_close=200.0,
        change=9.0,
        change_percent=4.5,
        volume=5000000,
        avg_volume_20d=2000000,  # rvol = 2.5x
        atr_14=6.0,
        week_52_high=215.0,
        week_52_low=120.0,
        price_band=band,
        timestamp=datetime.now(),
    )

    # Assertions
    assert snap.rvol == 2.5
    assert snap.upper_circuit_distance_pct < 1.0
    assert snap.is_near_upper_circuit(threshold_pct=1.0) is True
    assert snap.is_near_lower_circuit(threshold_pct=1.0) is False


def test_indian_market_simulator_seed_data():
    """Verify Indian simulator initializes all core retail stocks correctly"""
    simulator = IndianMarketSimulator()
    tickers = simulator._tickers

    # Check key symbols exist
    assert "ZOMATO" in tickers
    assert "TRENT" in tickers
    assert "RELIANCE" in tickers
    assert "TATAMOTORS" in tickers

    zomato = tickers["ZOMATO"]
    assert zomato.price_band.band_percent == 5.0
    assert zomato.price_band.upper_circuit > zomato.current_price
    assert zomato.price_band.lower_circuit < zomato.current_price
    assert zomato.volume > 0


def test_simulator_circuit_clamping():
    """Verify simulated ticks never breach upper or lower circuit boundaries"""
    simulator = IndianMarketSimulator()
    zomato = simulator._tickers["ZOMATO"]

    # Advance 100 ticks and verify price remains strictly clamped
    for _ in range(100):
        updated = simulator.advance_tick("ZOMATO")
        assert updated.current_price <= zomato.price_band.upper_circuit
        assert updated.current_price >= zomato.price_band.lower_circuit


def test_simulator_deterministic_triggers():
    """Verify test anomaly triggers work reliably for testing alerts"""
    simulator = IndianMarketSimulator()

    # 1. Circuit approach trigger
    trent = simulator.trigger_circuit_approach("TRENT", upper=True)
    assert trent.is_near_upper_circuit(threshold_pct=1.0) is True

    # 2. Volume surge trigger
    zomato = simulator.trigger_volume_surge("ZOMATO", multiplier=3.5)
    assert zomato.rvol >= 3.5

    # 3. 52-week breakout trigger
    rel = simulator.trigger_52w_breakout("RELIANCE")
    assert rel.current_price >= rel.week_52_high


def test_central_ticker_store_history_and_timetravel():
    """Verify central store stores ticks and retrieves snapshot at past timestamps"""
    store = CentralTickerStore()
    now = datetime.now()

    # Create 3 time snapshots for ZOMATO
    t0 = now - timedelta(minutes=10)
    t1 = now - timedelta(minutes=5)
    t2 = now

    band = PriceBand(band_percent=5.0, upper_circuit=270.0, lower_circuit=240.0)

    snap0 = TickerSnapshot(
        symbol="ZOMATO",
        company_name="Zomato Ltd",
        current_price=250.0,
        open_price=250.0,
        high_price=252.0,
        low_price=249.0,
        prev_close=250.0,
        change=0.0,
        change_percent=0.0,
        volume=1000000,
        avg_volume_20d=2000000,
        atr_14=8.0,
        week_52_high=268.0,
        week_52_low=100.0,
        price_band=band,
        timestamp=t0,
    )

    snap1 = snap0.model_copy(update={"current_price": 255.0, "volume": 1500000, "timestamp": t1})
    snap2 = snap1.model_copy(update={"current_price": 260.0, "volume": 2200000, "timestamp": t2})

    store.update_ticker(snap0)
    store.update_ticker(snap1)
    store.update_ticker(snap2)

    # Latest should be snap2 (260.0)
    assert store.get_latest("ZOMATO").current_price == 260.0

    # Query snapshot at 7 minutes ago (between t0 and t1) -> should return snap0 (250.0)
    target = now - timedelta(minutes=7)
    past_snap = store.get_snapshot_at_or_before("ZOMATO", target)
    assert past_snap is not None
    assert past_snap.current_price == 250.0

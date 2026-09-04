import pytest
from datetime import datetime, timedelta
from backend.app.models.ticker import TickerSnapshot, PriceBand, BenchmarkSnapshot
from backend.app.models.signals import SignalCategory
from backend.app.services.analytics.anomaly_detector import AnomalyDetector
from backend.app.services.analytics.diff_engine import CheckpointDiffEngine
from backend.app.services.market_data.store import CentralTickerStore


def create_mock_snapshot(
    symbol: str = "TRENT",
    price: float = 7200.0,
    prev_close: float = 7200.0,
    volume: int = 1000000,
    avg_vol: int = 2000000,
    atr_14: float = 200.0,
    week_52_high: float = 7500.0,
    upper_circuit: float = 7560.0,
    lower_circuit: float = 6840.0,
    timestamp: datetime = None,
) -> TickerSnapshot:
    band = PriceBand(band_percent=5.0, upper_circuit=upper_circuit, lower_circuit=lower_circuit)
    chg = round(price - prev_close, 2)
    chg_pct = round((chg / prev_close) * 100, 2)
    return TickerSnapshot(
        symbol=symbol,
        company_name=f"{symbol} Ltd",
        exchange="NSE",
        current_price=price,
        open_price=prev_close,
        high_price=max(price, prev_close),
        low_price=min(price, prev_close),
        prev_close=prev_close,
        change=chg,
        change_percent=chg_pct,
        volume=volume,
        avg_volume_20d=avg_vol,
        atr_14=atr_14,
        week_52_high=week_52_high,
        week_52_low=week_52_high * 0.5,
        price_band=band,
        timestamp=timestamp or datetime.now(),
    )


def test_noise_suppression_for_calm_stock():
    """Verify standard minor market drift is classified as CALM with low urgency"""
    # Stock moved only ₹10 on ATR of ₹200 (Z_vol = 0.05), volume is 0.5x avg
    snap = create_mock_snapshot(price=7210.0, prev_close=7200.0, volume=1000000, avg_vol=2000000)
    eval_res = AnomalyDetector.evaluate(snap)

    assert eval_res.urgency_score < 40
    assert eval_res.requires_attention is False
    assert any(s.category == SignalCategory.CALM for s in eval_res.signals)


def test_volatility_breakout_detection():
    """Verify price move exceeding 2.0x ATR is flagged as sharp breakout"""
    # Stock moved ₹450 on ATR of ₹200 (Z_vol = 2.25)
    snap = create_mock_snapshot(price=7650.0, prev_close=7200.0, upper_circuit=8000.0, week_52_high=8500.0)
    eval_res = AnomalyDetector.evaluate(snap)

    assert eval_res.urgency_score >= 40
    assert any(s.category == SignalCategory.VOLATILITY_BREAKOUT for s in eval_res.signals)


def test_volume_surge_detection():
    """Verify volume >= 2.5x 20-day average triggers volume surge flag"""
    # Volume is 6M vs avg 2M (RVol = 3.0x)
    snap = create_mock_snapshot(volume=6000000, avg_vol=2000000)
    eval_res = AnomalyDetector.evaluate(snap)

    assert any(s.category == SignalCategory.VOLUME_SURGE for s in eval_res.signals)
    vol_signal = next(s for s in eval_res.signals if s.category == SignalCategory.VOLUME_SURGE)
    assert "3.0x" in vol_signal.headline


def test_circuit_proximity_alert():
    """Verify stock trading within 1% of Upper Circuit triggers CRITICAL alert"""
    # Upper circuit is 7560. Price is 7530 (distance < 0.4%)
    snap = create_mock_snapshot(price=7530.0, upper_circuit=7560.0)
    eval_res = AnomalyDetector.evaluate(snap)

    assert any(s.category == SignalCategory.CIRCUIT_ALERT for s in eval_res.signals)
    circuit_sig = next(s for s in eval_res.signals if s.category == SignalCategory.CIRCUIT_ALERT)
    assert circuit_sig.severity == "CRITICAL"
    assert "Upper Circuit" in circuit_sig.headline


def test_benchmark_decoupling_relative_strength():
    """Verify stock gaining while NIFTY 50 drops is flagged as defying market"""
    snap = create_mock_snapshot(price=7400.0, prev_close=7200.0)  # +2.78%
    benchmark = BenchmarkSnapshot(symbol="NIFTY50", current_value=24500.0, change=-200.0, change_percent=-0.81)

    eval_res = AnomalyDetector.evaluate(snap, benchmark=benchmark)
    assert any(s.category == SignalCategory.BENCHMARK_DECOUPLING for s in eval_res.signals)


def test_diff_engine_deterministic_lookback():
    """Verify CheckpointDiffEngine calculates accurate duration, price deltas, and separates calm vs attention"""
    store = CentralTickerStore()
    now = datetime.now()
    two_hours_ago = now - timedelta(hours=2)

    # 1. ZOMATO: Calm stock (no big change)
    z_past = create_mock_snapshot(symbol="ZOMATO", price=250.0, volume=1000000, timestamp=two_hours_ago)
    z_curr = create_mock_snapshot(symbol="ZOMATO", price=251.0, volume=1200000, timestamp=now)

    # 2. TRENT: Heavy breakout (surged from 7200 to 7500 on 3x vol near upper circuit)
    t_past = create_mock_snapshot(symbol="TRENT", price=7200.0, volume=500000, timestamp=two_hours_ago)
    t_curr = create_mock_snapshot(
        symbol="TRENT",
        price=7540.0,
        upper_circuit=7560.0,
        volume=6000000,
        avg_vol=2000000,
        timestamp=now,
    )

    store.update_ticker(z_past)
    store.update_ticker(z_curr)
    store.update_ticker(t_past)
    store.update_ticker(t_curr)

    engine = CheckpointDiffEngine(store)
    report = engine.compute_diff(last_seen_at=two_hours_ago)

    # Verify duration away
    assert "2h" in report.duration_away_human
    assert report.total_tracked == 2

    # TRENT should be in top_attention due to circuit proximity & 3x volume
    assert len(report.top_attention) >= 1
    trent_delta = next(d for d in report.top_attention if d.symbol == "TRENT")
    assert trent_delta.price_change == 340.0
    assert trent_delta.volume_accumulated_while_away == 5500000
    assert trent_delta.is_meaningful_change is True

    # ZOMATO should be in calm_stocks
    assert any(d.symbol == "ZOMATO" for d in report.calm_stocks)

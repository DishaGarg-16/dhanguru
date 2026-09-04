from typing import Optional
from backend.app.models.ticker import TickerSnapshot, BenchmarkSnapshot
from backend.app.models.signals import (
    AnomalyEvaluation,
    AttentionSignal,
    SignalCategory,
)


class AnomalyDetector:
    """
    Evaluates quantitative market data and transforms anomalies into
    human-translated attention signals and a 0-100 Urgency Score.
    """

    @staticmethod
    def evaluate(
        ticker: TickerSnapshot,
        benchmark: Optional[BenchmarkSnapshot] = None,
    ) -> AnomalyEvaluation:
        signals: list[AttentionSignal] = []

        # 1. ATR Normalized Volatility (Z_vol)
        # Ratio of session price move vs 14-day Average True Range
        abs_change = abs(ticker.change)
        z_vol = abs_change / ticker.atr_14 if ticker.atr_14 > 0 else 0.0

        if z_vol >= 2.0:
            direction = "Breakout" if ticker.change > 0 else "Drop"
            signals.append(
                AttentionSignal(
                    category=SignalCategory.VOLATILITY_BREAKOUT,
                    severity="HIGH" if z_vol < 3.0 else "CRITICAL",
                    headline=f"⚡ Sharp Price {direction} ({z_vol:.1f}x Daily ATR)",
                    technical_detail=f"Price moved ₹{abs_change:.2f} vs 14d ATR of ₹{ticker.atr_14:.2f}",
                    badge_color="green" if ticker.change > 0 else "red",
                )
            )
        elif z_vol >= 1.2:
            direction = "Upward" if ticker.change > 0 else "Downward"
            signals.append(
                AttentionSignal(
                    category=SignalCategory.VOLATILITY_BREAKOUT,
                    severity="MEDIUM",
                    headline=f"📈 Elevated {direction} Momentum",
                    technical_detail=f"Price move is {z_vol:.1f}x 14d ATR",
                    badge_color="green" if ticker.change > 0 else "red",
                )
            )

        # 2. Relative Volume (RVol) vs 20-day Time-of-Day Average
        rvol = ticker.rvol
        if rvol >= 2.5:
            signals.append(
                AttentionSignal(
                    category=SignalCategory.VOLUME_SURGE,
                    severity="HIGH" if rvol < 4.0 else "CRITICAL",
                    headline=f"🔥 {rvol:.1f}x Volume Surge vs 20-Day Average",
                    technical_detail=f"Current volume {ticker.volume:,} vs avg {ticker.avg_volume_20d:,}",
                    badge_color="green" if ticker.change >= 0 else "red",
                )
            )
        elif rvol >= 1.6:
            signals.append(
                AttentionSignal(
                    category=SignalCategory.VOLUME_SURGE,
                    severity="MEDIUM",
                    headline=f"📊 Above Average Liquidity ({rvol:.1f}x)",
                    technical_detail=f"Volume {ticker.volume:,} is 60%+ above 20d baseline",
                    badge_color="neutral",
                )
            )

        # 3. Circuit Band Proximity (<1% to Upper or Lower Circuit)
        if ticker.is_near_upper_circuit(threshold_pct=1.0):
            signals.append(
                AttentionSignal(
                    category=SignalCategory.CIRCUIT_ALERT,
                    severity="CRITICAL",
                    headline=f"🔒 Approaching Upper Circuit (₹{ticker.price_band.upper_circuit:,.2f})",
                    technical_detail=f"Trading within {ticker.upper_circuit_distance_pct:.2f}% of daily upper band",
                    badge_color="circuit",
                )
            )
        elif ticker.is_near_lower_circuit(threshold_pct=1.0):
            signals.append(
                AttentionSignal(
                    category=SignalCategory.CIRCUIT_ALERT,
                    severity="CRITICAL",
                    headline=f"⚠️ Warning: Approaching Lower Circuit (₹{ticker.price_band.lower_circuit:,.2f})",
                    technical_detail=f"Trading within {ticker.lower_circuit_distance_pct:.2f}% of daily lower band",
                    badge_color="circuit",
                )
            )

        # 4. 52-Week High / Low Breakouts
        if ticker.current_price >= ticker.week_52_high or ticker.is_near_52w_high(0.5):
            signals.append(
                AttentionSignal(
                    category=SignalCategory.LEVEL_BREACH,
                    severity="HIGH",
                    headline=f"🚀 52-Week High Breakout (₹{ticker.week_52_high:,.2f})",
                    technical_detail="Stock traded at or within 0.5% of its 52-week peak",
                    badge_color="green",
                )
            )

        # 5. Benchmark Decoupling (Relative Strength vs NIFTY 50)
        rel_strength = 0.0
        if benchmark and benchmark.change_percent != 0:
            # Stock moving positively while benchmark is falling
            if ticker.change_percent > 1.0 and benchmark.change_percent < -0.3:
                rel_strength = ticker.change_percent - benchmark.change_percent
                signals.append(
                    AttentionSignal(
                        category=SignalCategory.BENCHMARK_DECOUPLING,
                        severity="MEDIUM",
                        headline="🛡️ Defying Broad Market Fall",
                        technical_detail=f"Up {ticker.change_percent:+.2f}% while NIFTY 50 is down {benchmark.change_percent:+.2f}%",
                        badge_color="green",
                    )
                )

        # Compute Composite Urgency Score (0 - 100)
        # Weighted across Volatility (35%), Volume (30%), Circuit (25%), Decoupling (10%)
        vol_component = min(35.0, (z_vol / 2.0) * 35.0)
        rvol_component = min(30.0, (rvol / 2.5) * 30.0)
        circuit_component = 25.0 if (ticker.is_near_upper_circuit(1.0) or ticker.is_near_lower_circuit(1.0)) else 0.0
        decouple_component = min(10.0, rel_strength * 3.0) if rel_strength > 0 else 0.0

        raw_score = int(vol_component + rvol_component + circuit_component + decouple_component)
        urgency_score = min(100, max(0, raw_score))

        # Determine primary human driver
        if signals:
            # Pick the highest severity signal as primary driver
            primary_driver = signals[0].headline
        else:
            primary_driver = "Normal market drift (Within daily noise)"
            signals.append(
                AttentionSignal(
                    category=SignalCategory.CALM,
                    severity="LOW",
                    headline="Standard Daily Drift",
                    technical_detail="No abnormal volatility, volume surge, or level breaches",
                    badge_color="neutral",
                )
            )

        return AnomalyEvaluation(
            symbol=ticker.symbol,
            urgency_score=urgency_score,
            signals=signals,
            primary_driver=primary_driver,
            requires_attention=urgency_score >= 60,
        )

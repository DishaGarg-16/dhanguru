from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, computed_field


class PriceBand(BaseModel):
    """Daily circuit band limits on Indian exchanges (NSE/BSE)"""
    band_percent: float = Field(description="Circuit percentage, e.g. 5.0, 10.0, 20.0")
    upper_circuit: float = Field(description="Upper circuit price limit")
    lower_circuit: float = Field(description="Lower circuit price limit")


class TickerSnapshot(BaseModel):
    """Point-in-time market snapshot for an Indian equity ticker"""
    symbol: str
    company_name: str
    exchange: str = "NSE"
    current_price: float
    open_price: float
    high_price: float
    low_price: float
    prev_close: float
    change: float
    change_percent: float
    volume: int
    avg_volume_20d: int
    atr_14: float = Field(description="14-day Average True Range in INR")
    week_52_high: float
    week_52_low: float
    price_band: PriceBand
    timestamp: datetime = Field(default_factory=datetime.now)

    @computed_field
    @property
    def rvol(self) -> float:
        """Relative volume vs 20-day benchmark"""
        if self.avg_volume_20d <= 0:
            return 1.0
        return round(self.volume / self.avg_volume_20d, 2)

    @computed_field
    @property
    def upper_circuit_distance_pct(self) -> float:
        """Percentage distance to upper circuit limit"""
        if self.current_price <= 0:
            return 100.0
        return round(((self.price_band.upper_circuit - self.current_price) / self.current_price) * 100, 2)

    @computed_field
    @property
    def lower_circuit_distance_pct(self) -> float:
        """Percentage distance to lower circuit limit"""
        if self.current_price <= 0:
            return 100.0
        return round(((self.current_price - self.price_band.lower_circuit) / self.current_price) * 100, 2)

    def is_near_upper_circuit(self, threshold_pct: float = 1.0) -> bool:
        """Check if trading within threshold_pct of upper circuit"""
        return 0 <= self.upper_circuit_distance_pct <= threshold_pct

    def is_near_lower_circuit(self, threshold_pct: float = 1.0) -> bool:
        """Check if trading within threshold_pct of lower circuit"""
        return 0 <= self.lower_circuit_distance_pct <= threshold_pct

    def is_near_52w_high(self, threshold_pct: float = 1.0) -> bool:
        """Check if trading within threshold_pct of 52-week high"""
        if self.week_52_high <= 0:
            return False
        dist = ((self.week_52_high - self.current_price) / self.week_52_high) * 100
        return 0 <= dist <= threshold_pct


class BenchmarkSnapshot(BaseModel):
    """Snapshot for market indices like NIFTY 50"""
    symbol: str = "NIFTY50"
    current_value: float
    change: float
    change_percent: float
    timestamp: datetime = Field(default_factory=datetime.now)

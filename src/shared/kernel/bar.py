"""Framework-free OHLCV bar — the boundary type LEAN TradeBars are mapped into."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Bar:
    symbol: str
    end_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    def __post_init__(self) -> None:
        if self.low > self.high:
            raise ValueError(f"{self.symbol}: low {self.low} > high {self.high}")

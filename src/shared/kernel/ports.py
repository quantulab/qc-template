"""Ports (interfaces). Application code depends on these Protocols,
never on QCAlgorithm. LEAN adapters in */lean/ implement them."""
from __future__ import annotations
from datetime import datetime
from typing import Protocol, Sequence

from .bar import Bar


class Clock(Protocol):
    def utc_now(self) -> datetime: ...


class MarketDataReader(Protocol):
    def trailing_bars(self, symbol: str, count: int) -> Sequence[Bar]: ...


class PortfolioReader(Protocol):
    def equity(self) -> float: ...
    def drawdown_from_peak(self) -> float: ...   # 0.0 .. 1.0

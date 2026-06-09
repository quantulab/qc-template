"""Test data builders + fake ports. Fakes implement the kernel Protocols,
so use cases run in tests exactly as they run inside LEAN."""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Sequence

from src.shared.kernel.bar import Bar

EPOCH = datetime(2026, 1, 2, 16, 0)


def bar_series(symbol: str, closes: Sequence[float], start: datetime = EPOCH) -> list[Bar]:
    bars = []
    for i, close in enumerate(closes):
        bars.append(Bar(
            symbol=symbol,
            end_time=start + timedelta(days=i),
            open=close, high=close * 1.01, low=close * 0.99,
            close=close, volume=1_000_000,
        ))
    return bars


def trending_closes(start_price: float, total_return: float, n: int) -> list[float]:
    step = (1 + total_return) ** (1 / (n - 1))
    return [start_price * step ** i for i in range(n)]


class FakeClock:
    def __init__(self, now: datetime = EPOCH) -> None:
        self.now = now

    def utc_now(self) -> datetime:
        return self.now


class FakeMarketData:
    def __init__(self, series: dict[str, list[Bar]]) -> None:
        self._series = series

    def trailing_bars(self, symbol: str, count: int):
        return self._series.get(symbol, [])[-count:]

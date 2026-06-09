"""Pure signal logic. No I/O, no LEAN, no clock — fully unit-testable."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Sequence

from src.shared.kernel.bar import Bar
from src.shared.kernel.signal import Direction, Signal


@dataclass(frozen=True)
class MomentumParams:
    lookback: int = 20            # bars
    entry_threshold: float = 0.02 # 2% absolute return triggers a view
    horizon: timedelta = timedelta(days=5)


class MomentumCalculator:
    def __init__(self, params: MomentumParams) -> None:
        self._p = params

    def evaluate(self, bars: Sequence[Bar], as_of: datetime) -> Signal | None:
        """Return a Signal if momentum exceeds threshold, else None."""
        if len(bars) < self._p.lookback:
            return None  # not warmed up

        window = bars[-self._p.lookback:]
        first, last = window[0].close, window[-1].close
        if first <= 0:
            return None
        ret = (last / first) - 1.0

        if abs(ret) < self._p.entry_threshold:
            return None

        direction = Direction.LONG if ret > 0 else Direction.SHORT
        # confidence scales with strength, capped at 1.0
        confidence = min(abs(ret) / (self._p.entry_threshold * 4), 1.0)
        return Signal(
            symbol=window[-1].symbol,
            direction=direction,
            confidence=confidence,
            generated_at=as_of,
            horizon=self._p.horizon,
        )

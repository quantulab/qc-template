"""Use case: orchestrates ports + domain logic. Still LEAN-free."""
from __future__ import annotations
from typing import Iterable, Sequence

from src.shared.kernel.ports import Clock, MarketDataReader
from src.shared.kernel.signal import Signal
from src.slices.momentum_alpha.domain.momentum import MomentumCalculator, MomentumParams


class GenerateMomentumSignals:
    def __init__(
        self,
        market_data: MarketDataReader,
        clock: Clock,
        params: MomentumParams | None = None,
    ) -> None:
        self._data = market_data
        self._clock = clock
        self._params = params or MomentumParams()
        self._calc = MomentumCalculator(self._params)

    def execute(self, symbols: Iterable[str]) -> Sequence[Signal]:
        now = self._clock.utc_now()
        signals = []
        for symbol in symbols:
            bars = self._data.trailing_bars(symbol, self._params.lookback)
            signal = self._calc.evaluate(bars, as_of=now)
            if signal and signal.is_actionable:
                signals.append(signal)
        return signals

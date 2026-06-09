"""LEAN adapter: thin AlphaModel that delegates to the use case.
Keep this file dumb — logic lives in domain/ and application/."""
from __future__ import annotations

from AlgorithmImports import AlphaModel, Resolution  # type: ignore

from src.shared.lean.mapping import signal_to_insight, trade_bar_to_domain
from src.slices.momentum_alpha.application.generate_signals import GenerateMomentumSignals
from src.slices.momentum_alpha.domain.momentum import MomentumParams


class _LeanClock:
    def __init__(self, algorithm) -> None:
        self._algo = algorithm

    def utc_now(self):
        return self._algo.utc_time


class _LeanMarketData:
    def __init__(self, algorithm) -> None:
        self._algo = algorithm

    def trailing_bars(self, symbol: str, count: int):
        history = self._algo.history([symbol], count, Resolution.DAILY)
        bars = []
        for _, row in history.iterrows():
            bars.append(trade_bar_to_domain(_RowBar(symbol, row)))
        return bars


class _RowBar:
    """Adapts a history DataFrame row to the TradeBar shape mapping expects."""
    def __init__(self, symbol, row):
        self.symbol = symbol
        self.end_time = row.name[-1] if hasattr(row.name, "__len__") else row.name
        self.open, self.high = row["open"], row["high"]
        self.low, self.close = row["low"], row["close"]
        self.volume = row.get("volume", 0)


class MomentumAlphaModel(AlphaModel):
    def __init__(self, params: MomentumParams | None = None) -> None:
        self._params = params or MomentumParams()
        self._symbols: list = []
        self._use_case: GenerateMomentumSignals | None = None

    def update(self, algorithm, data):
        if self._use_case is None:
            self._use_case = GenerateMomentumSignals(
                market_data=_LeanMarketData(algorithm),
                clock=_LeanClock(algorithm),
                params=self._params,
            )
        symbols = [str(s) for s in self._symbols]
        signals = self._use_case.execute(symbols)
        return [signal_to_insight(s) for s in signals]

    def on_securities_changed(self, algorithm, changes):
        for security in changes.added_securities:
            self._symbols.append(security.symbol)
        for security in changes.removed_securities:
            if security.symbol in self._symbols:
                self._symbols.remove(security.symbol)

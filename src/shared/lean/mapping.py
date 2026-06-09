"""Anti-corruption layer: translate between LEAN types and domain types.
This module is the ONLY shared code allowed to import AlgorithmImports."""
from __future__ import annotations

try:
    from AlgorithmImports import (  # type: ignore
        Insight, InsightDirection, PortfolioTarget, TradeBar,
    )
    LEAN_AVAILABLE = True
except ImportError:          # running under pytest, outside LEAN
    LEAN_AVAILABLE = False

from src.shared.kernel.bar import Bar
from src.shared.kernel.signal import Direction, Signal


def trade_bar_to_domain(trade_bar) -> Bar:
    return Bar(
        symbol=str(trade_bar.symbol),
        end_time=trade_bar.end_time,
        open=float(trade_bar.open),
        high=float(trade_bar.high),
        low=float(trade_bar.low),
        close=float(trade_bar.close),
        volume=float(trade_bar.volume),
    )


_DIRECTION_MAP = {
    Direction.LONG: "InsightDirection.Up",
    Direction.SHORT: "InsightDirection.Down",
    Direction.FLAT: "InsightDirection.Flat",
}


def signal_to_insight(signal: Signal):
    if not LEAN_AVAILABLE:
        raise RuntimeError("LEAN runtime not available")
    lean_direction = {
        Direction.LONG: InsightDirection.Up,
        Direction.SHORT: InsightDirection.Down,
        Direction.FLAT: InsightDirection.Flat,
    }[signal.direction]
    return Insight.price(
        signal.symbol, signal.horizon, lean_direction, confidence=signal.confidence
    )

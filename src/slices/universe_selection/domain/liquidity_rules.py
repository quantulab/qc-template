"""Pure filtering rules over framework-free candidate records."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class Candidate:
    symbol: str
    price: float
    dollar_volume: float


@dataclass(frozen=True)
class LiquidityParams:
    min_price: float = 5.0
    top_n: int = 20


def select_liquid(candidates: Sequence[Candidate], params: LiquidityParams) -> list[str]:
    eligible = [c for c in candidates if c.price >= params.min_price]
    ranked = sorted(eligible, key=lambda c: c.dollar_volume, reverse=True)
    return [c.symbol for c in ranked[: params.top_n]]

"""Pure risk policy: scale or kill exposure as drawdown deepens."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence

from src.shared.kernel.target import WeightTarget


@dataclass(frozen=True)
class DrawdownParams:
    soft_limit: float = 0.05   # start de-risking at 5% drawdown
    hard_limit: float = 0.10   # fully flat at 10% drawdown


class DrawdownPolicy:
    def __init__(self, params: DrawdownParams) -> None:
        if params.hard_limit <= params.soft_limit:
            raise ValueError("hard_limit must exceed soft_limit")
        self._p = params

    def apply(
        self, targets: Sequence[WeightTarget], current_drawdown: float
    ) -> list[WeightTarget]:
        if current_drawdown >= self._p.hard_limit:
            return [t.scaled(0.0) for t in targets]
        if current_drawdown <= self._p.soft_limit:
            return list(targets)
        # linear de-risking between soft and hard limits
        span = self._p.hard_limit - self._p.soft_limit
        factor = 1.0 - (current_drawdown - self._p.soft_limit) / span
        return [t.scaled(factor) for t in targets]

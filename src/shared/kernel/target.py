"""Portfolio target value object — domain analogue of LEAN PortfolioTarget."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class WeightTarget:
    symbol: str
    weight: float  # signed fraction of portfolio equity, e.g. -0.05 = 5% short

    def scaled(self, factor: float) -> "WeightTarget":
        return WeightTarget(self.symbol, self.weight * factor)

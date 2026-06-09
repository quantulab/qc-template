"""Pure sizing math: confidence-weighted, volatility-capped weights."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence

from src.shared.kernel.signal import Direction, Signal
from src.shared.kernel.target import WeightTarget


@dataclass(frozen=True)
class SizingParams:
    max_gross_exposure: float = 1.0   # 100% of equity
    max_single_weight: float = 0.10   # 10% per name


class ConfidenceWeightedSizer:
    def __init__(self, params: SizingParams) -> None:
        self._p = params

    def build_targets(self, signals: Sequence[Signal]) -> list[WeightTarget]:
        actionable = [s for s in signals if s.is_actionable]
        if not actionable:
            return []

        total_confidence = sum(s.confidence for s in actionable)
        targets = []
        for s in actionable:
            raw = (s.confidence / total_confidence) * self._p.max_gross_exposure
            weight = min(raw, self._p.max_single_weight)
            if s.direction is Direction.SHORT:
                weight = -weight
            targets.append(WeightTarget(symbol=s.symbol, weight=weight))
        return targets

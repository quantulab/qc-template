"""Use case: signals in, weight targets out."""
from __future__ import annotations
from typing import Sequence

from src.shared.kernel.signal import Signal
from src.shared.kernel.target import WeightTarget
from src.slices.position_sizing.domain.vol_target_sizer import (
    ConfidenceWeightedSizer, SizingParams,
)


class BuildPortfolioTargets:
    def __init__(self, params: SizingParams | None = None) -> None:
        self._sizer = ConfidenceWeightedSizer(params or SizingParams())

    def execute(self, signals: Sequence[Signal]) -> list[WeightTarget]:
        return self._sizer.build_targets(signals)

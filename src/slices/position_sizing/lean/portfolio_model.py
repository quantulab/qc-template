"""LEAN adapter: PortfolioConstructionModel delegating to the sizing use case."""
from __future__ import annotations

from AlgorithmImports import (  # type: ignore
    PortfolioConstructionModel, PortfolioTarget,
)

from src.shared.kernel.signal import Direction, Signal
from src.slices.position_sizing.application.build_targets import BuildPortfolioTargets
from src.slices.position_sizing.domain.vol_target_sizer import SizingParams


def _to_direction(lean_direction) -> Direction:
    """Map a LEAN InsightDirection to a domain Direction by its integer value.

    InsightDirection is Up=1, Flat=0, Down=-1. We compare on the int value
    rather than referencing the enum members so nothing touches the LEAN enum
    at module-import time (pythonnet cannot resolve .NET enum members before
    the runtime is fully initialized, which raises "error return without
    exception set" during import).
    """
    value = int(lean_direction)
    if value > 0:
        return Direction.LONG
    if value < 0:
        return Direction.SHORT
    return Direction.FLAT


class ConfidenceWeightedPortfolioModel(PortfolioConstructionModel):
    def __init__(self, params: SizingParams | None = None) -> None:
        super().__init__()
        self._use_case = BuildPortfolioTargets(params)

    def create_targets(self, algorithm, insights):
        signals = [
            Signal(
                symbol=str(i.symbol),
                direction=_to_direction(i.direction),
                confidence=float(i.confidence or 0.0),
                generated_at=algorithm.utc_time,
                horizon=i.period,
            )
            for i in insights
        ]
        targets = self._use_case.execute(signals)
        # PortfolioTarget.percent returns None when the weight can't be realized
        # (e.g. the security has no price yet). The framework dereferences each
        # target's Symbol, so leaving a None in this list NREs in Framework.cs.
        created = (
            PortfolioTarget.percent(algorithm, t.symbol, t.weight) for t in targets
        )
        return [target for target in created if target is not None]

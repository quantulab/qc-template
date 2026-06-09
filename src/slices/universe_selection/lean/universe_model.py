"""LEAN adapter: coarse-fundamental universe delegating to pure rules."""
from __future__ import annotations

from AlgorithmImports import FundamentalUniverseSelectionModel  # type: ignore

from src.slices.universe_selection.domain.liquidity_rules import (
    Candidate, LiquidityParams, select_liquid,
)


class LiquidUniverseModel(FundamentalUniverseSelectionModel):
    def __init__(self, params: LiquidityParams | None = None) -> None:
        super().__init__()
        self._params = params or LiquidityParams()

    def select(self, algorithm, fundamental):
        candidates = [
            Candidate(
                symbol=str(f.symbol),
                price=float(f.price),
                dollar_volume=float(f.dollar_volume),
            )
            for f in fundamental
            if f.has_fundamental_data
        ]
        selected = set(select_liquid(candidates, self._params))
        return [f.symbol for f in fundamental if str(f.symbol) in selected]

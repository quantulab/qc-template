"""LEAN adapter: immediate execution. When you add TWAP/VWAP or
slippage-aware logic, introduce domain/ and application/ layers here
exactly as in the other slices."""
from __future__ import annotations

from AlgorithmImports import ImmediateExecutionModel  # type: ignore


class DefaultExecutionModel(ImmediateExecutionModel):
    pass

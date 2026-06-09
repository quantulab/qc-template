"""Framework-free trading primitives. NEVER import AlgorithmImports here."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum


class Direction(Enum):
    LONG = 1
    FLAT = 0
    SHORT = -1


@dataclass(frozen=True)
class Signal:
    """A directional view on a symbol — the domain analogue of a LEAN Insight."""
    symbol: str
    direction: Direction
    confidence: float          # 0.0 .. 1.0
    generated_at: datetime
    horizon: timedelta

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0, 1], got {self.confidence}")

    @property
    def is_actionable(self) -> bool:
        return self.direction is not Direction.FLAT and self.confidence > 0.0

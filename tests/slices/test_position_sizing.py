from datetime import timedelta

import pytest

from src.shared.kernel.signal import Direction, Signal
from src.slices.position_sizing.domain.vol_target_sizer import (
    ConfidenceWeightedSizer, SizingParams,
)
from tests.fakes.builders import EPOCH


def make_signal(symbol: str, direction: Direction, confidence: float) -> Signal:
    return Signal(symbol, direction, confidence, EPOCH, timedelta(days=5))


def test_weights_proportional_to_confidence_and_capped():
    sizer = ConfidenceWeightedSizer(SizingParams(max_gross_exposure=1.0, max_single_weight=0.10))
    targets = sizer.build_targets([
        make_signal("AAPL", Direction.LONG, 0.9),
        make_signal("MSFT", Direction.LONG, 0.3),
    ])
    weights = {t.symbol: t.weight for t in targets}
    assert weights["AAPL"] == pytest.approx(0.10)  # raw 0.75, capped at 10%
    assert weights["MSFT"] == pytest.approx(0.10)  # raw 0.25, also capped


def test_uncapped_weights_are_confidence_proportional():
    sizer = ConfidenceWeightedSizer(SizingParams(max_gross_exposure=1.0, max_single_weight=1.0))
    targets = sizer.build_targets([
        make_signal("AAPL", Direction.LONG, 0.9),
        make_signal("MSFT", Direction.LONG, 0.3),
    ])
    weights = {t.symbol: t.weight for t in targets}
    assert weights["AAPL"] == pytest.approx(0.75)
    assert weights["MSFT"] == pytest.approx(0.25)


def test_short_signals_produce_negative_weights():
    sizer = ConfidenceWeightedSizer(SizingParams())
    targets = sizer.build_targets([make_signal("TSLA", Direction.SHORT, 0.5)])
    assert targets[0].weight < 0


def test_no_actionable_signals_means_no_targets():
    sizer = ConfidenceWeightedSizer(SizingParams())
    assert sizer.build_targets([make_signal("SPY", Direction.FLAT, 0.0)]) == []

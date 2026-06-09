"""Domain tests: pure math, no fakes needed beyond data builders."""
from datetime import timedelta

import pytest

from src.shared.kernel.signal import Direction
from src.slices.momentum_alpha.domain.momentum import MomentumCalculator, MomentumParams
from tests.fakes.builders import EPOCH, bar_series, trending_closes

PARAMS = MomentumParams(lookback=20, entry_threshold=0.02, horizon=timedelta(days=5))


def make_calc() -> MomentumCalculator:
    return MomentumCalculator(PARAMS)


def test_returns_none_when_not_warmed_up():
    bars = bar_series("SPY", trending_closes(100, 0.10, 10))  # only 10 of 20 bars
    assert make_calc().evaluate(bars, as_of=EPOCH) is None


def test_uptrend_above_threshold_emits_long():
    bars = bar_series("SPY", trending_closes(100, 0.08, 20))
    signal = make_calc().evaluate(bars, as_of=EPOCH)
    assert signal is not None
    assert signal.direction is Direction.LONG
    assert signal.symbol == "SPY"


def test_downtrend_emits_short():
    bars = bar_series("SPY", trending_closes(100, -0.08, 20))
    signal = make_calc().evaluate(bars, as_of=EPOCH)
    assert signal.direction is Direction.SHORT


def test_flat_market_emits_nothing():
    bars = bar_series("SPY", trending_closes(100, 0.005, 20))  # 0.5% < 2% threshold
    assert make_calc().evaluate(bars, as_of=EPOCH) is None


def test_confidence_is_bounded():
    bars = bar_series("SPY", trending_closes(100, 0.90, 20))  # huge move
    signal = make_calc().evaluate(bars, as_of=EPOCH)
    assert signal.confidence == pytest.approx(1.0)

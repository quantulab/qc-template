import pytest

from src.shared.kernel.target import WeightTarget
from src.slices.risk_management.domain.drawdown_policy import DrawdownParams, DrawdownPolicy

POLICY = DrawdownPolicy(DrawdownParams(soft_limit=0.05, hard_limit=0.10))
TARGETS = [WeightTarget("AAPL", 0.10), WeightTarget("TSLA", -0.05)]


def test_below_soft_limit_passes_through():
    assert POLICY.apply(TARGETS, current_drawdown=0.03) == TARGETS


def test_at_hard_limit_goes_flat():
    adjusted = POLICY.apply(TARGETS, current_drawdown=0.10)
    assert all(t.weight == 0.0 for t in adjusted)


def test_between_limits_scales_linearly():
    adjusted = POLICY.apply(TARGETS, current_drawdown=0.075)  # midpoint -> 50%
    assert adjusted[0].weight == pytest.approx(0.05)
    assert adjusted[1].weight == pytest.approx(-0.025)


def test_invalid_params_rejected():
    with pytest.raises(ValueError):
        DrawdownPolicy(DrawdownParams(soft_limit=0.10, hard_limit=0.10))

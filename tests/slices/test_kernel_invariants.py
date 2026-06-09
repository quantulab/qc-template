from datetime import timedelta

import pytest

from src.shared.kernel.bar import Bar
from src.shared.kernel.signal import Direction, Signal
from tests.fakes.builders import EPOCH


def test_signal_rejects_out_of_range_confidence():
    with pytest.raises(ValueError):
        Signal("SPY", Direction.LONG, 1.5, EPOCH, timedelta(days=1))


def test_bar_rejects_inverted_range():
    with pytest.raises(ValueError):
        Bar("SPY", EPOCH, 100, 99, 101, 100, 1)


def test_domain_has_no_lean_dependency():
    """Architecture test: the kernel and slice domains must import cleanly
    in an environment where AlgorithmImports does not exist."""
    import src.shared.kernel.signal
    import src.slices.momentum_alpha.domain.momentum
    import src.slices.position_sizing.domain.vol_target_sizer
    import src.slices.risk_management.domain.drawdown_policy
    import src.slices.universe_selection.domain.liquidity_rules  # noqa: F401

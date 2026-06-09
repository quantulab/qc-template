"""Application tests: use case wired with fake ports — proves the slice
works end-to-end without LEAN."""
from src.shared.kernel.signal import Direction
from src.slices.momentum_alpha.application.generate_signals import GenerateMomentumSignals
from src.slices.momentum_alpha.domain.momentum import MomentumParams
from tests.fakes.builders import FakeClock, FakeMarketData, bar_series, trending_closes


def test_emits_signals_only_for_trending_symbols():
    data = FakeMarketData({
        "AAPL": bar_series("AAPL", trending_closes(150, 0.10, 20)),
        "KO": bar_series("KO", trending_closes(60, 0.001, 20)),
        "TSLA": bar_series("TSLA", trending_closes(250, -0.12, 20)),
    })
    use_case = GenerateMomentumSignals(data, FakeClock(), MomentumParams(lookback=20))

    signals = use_case.execute(["AAPL", "KO", "TSLA"])

    by_symbol = {s.symbol: s for s in signals}
    assert set(by_symbol) == {"AAPL", "TSLA"}
    assert by_symbol["AAPL"].direction is Direction.LONG
    assert by_symbol["TSLA"].direction is Direction.SHORT


def test_unknown_symbol_is_skipped_silently():
    use_case = GenerateMomentumSignals(FakeMarketData({}), FakeClock(), MomentumParams())
    assert use_case.execute(["MISSING"]) == []

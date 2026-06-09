from src.slices.universe_selection.domain.liquidity_rules import (
    Candidate, LiquidityParams, select_liquid,
)


def test_filters_penny_stocks_and_ranks_by_dollar_volume():
    candidates = [
        Candidate("PENNY", price=2.0, dollar_volume=9e9),
        Candidate("AAPL", price=180.0, dollar_volume=8e9),
        Candidate("MSFT", price=400.0, dollar_volume=7e9),
        Candidate("XYZ", price=50.0, dollar_volume=1e6),
    ]
    selected = select_liquid(candidates, LiquidityParams(min_price=5.0, top_n=2))
    assert selected == ["AAPL", "MSFT"]

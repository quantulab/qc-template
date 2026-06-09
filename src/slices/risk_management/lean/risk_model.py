"""LEAN adapter: RiskManagementModel wrapping the drawdown policy."""
from __future__ import annotations

from AlgorithmImports import PortfolioTarget, RiskManagementModel  # type: ignore

from src.shared.kernel.target import WeightTarget
from src.slices.risk_management.domain.drawdown_policy import DrawdownParams, DrawdownPolicy


class DrawdownRiskModel(RiskManagementModel):
    def __init__(self, params: DrawdownParams | None = None) -> None:
        super().__init__()
        self._policy = DrawdownPolicy(params or DrawdownParams())
        self._peak_equity = 0.0

    def manage_risk(self, algorithm, targets):
        equity = float(algorithm.portfolio.total_portfolio_value)
        self._peak_equity = max(self._peak_equity, equity)
        drawdown = 0.0 if self._peak_equity == 0 else 1.0 - equity / self._peak_equity

        domain_targets = [
            WeightTarget(str(t.symbol), float(t.quantity)) for t in targets
        ]
        adjusted = self._policy.apply(domain_targets, drawdown)
        return [PortfolioTarget(t.symbol, t.weight) for t in adjusted]

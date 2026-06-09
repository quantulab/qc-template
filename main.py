"""Composition root — the ONLY file LEAN needs to know about.
Wires slices into the Algorithm Framework. No business logic lives here.
Docs: https://www.quantconnect.com/docs/v2/writing-algorithms
"""
from AlgorithmImports import QCAlgorithm, Resolution, UniverseSettings  # type: ignore

from src.slices.execution.lean.execution_model import DefaultExecutionModel
from src.slices.momentum_alpha.domain.momentum import MomentumParams
from src.slices.momentum_alpha.lean.alpha_model import MomentumAlphaModel
from src.slices.position_sizing.domain.vol_target_sizer import SizingParams
from src.slices.position_sizing.lean.portfolio_model import ConfidenceWeightedPortfolioModel
from src.slices.risk_management.domain.drawdown_policy import DrawdownParams
from src.slices.risk_management.lean.risk_model import DrawdownRiskModel
from src.slices.universe_selection.domain.liquidity_rules import LiquidityParams
from src.slices.universe_selection.lean.universe_model import LiquidUniverseModel


class CleanArchitectureStrategy(QCAlgorithm):
    def initialize(self) -> None:
        self.set_start_date(2023, 1, 1)
        self.set_end_date(2026, 12, 31)
        self.set_cash(100_000)
        self.universe_settings.resolution = Resolution.DAILY

        # One line per slice. Tune behavior via params, not by editing adapters.
        self.add_universe_selection(LiquidUniverseModel(LiquidityParams(top_n=20)))
        self.add_alpha(MomentumAlphaModel(MomentumParams(lookback=20, entry_threshold=0.02)))
        self.set_portfolio_construction(
            ConfidenceWeightedPortfolioModel(SizingParams(max_single_weight=0.10))
        )
        self.add_risk_management(DrawdownRiskModel(DrawdownParams(0.05, 0.10)))
        self.set_execution(DefaultExecutionModel())

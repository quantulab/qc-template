# Anatomy of a QuantConnect Strategy — Clean Architecture, Vertically Sliced, TDD

A production-shaped LEAN algorithm skeleton. Every behavior is a **vertical slice**
mapped 1:1 onto a QuantConnect Algorithm Framework module, with all trading logic
kept framework-free and fully unit-tested.

```
qc-clean-strategy/
├── main.py                        ← composition root (only file LEAN wires up)
├── pytest.ini
├── src/
│   ├── shared/
│   │   ├── kernel/                ← pure domain primitives + ports (Protocols)
│   │   │   ├── signal.py            Signal, Direction (≈ Insight, framework-free)
│   │   │   ├── bar.py               Bar (≈ TradeBar, framework-free)
│   │   │   ├── target.py            WeightTarget (≈ PortfolioTarget)
│   │   │   └── ports.py             Clock, MarketDataReader, PortfolioReader
│   │   └── lean/
│   │       └── mapping.py         ← anti-corruption layer (QC ⇄ domain)
│   └── slices/                    ← one slice per Framework module
│       ├── universe_selection/      domain/ + lean/   → UniverseSelectionModel
│       ├── momentum_alpha/          domain/ + application/ + lean/ → AlphaModel
│       ├── position_sizing/         domain/ + application/ + lean/ → PortfolioConstructionModel
│       ├── risk_management/         domain/ + lean/   → RiskManagementModel
│       └── execution/               lean/             → ExecutionModel
└── tests/
    ├── fakes/builders.py          ← fake ports + test-data builders
    └── slices/                    ← one test module per slice + architecture test
```

## The three layers inside each slice

| Layer          | Contains                                  | May import                   |
|----------------|-------------------------------------------|------------------------------|
| `domain/`      | pure decision logic (math, rules)          | shared kernel only           |
| `application/` | use cases orchestrating ports + domain     | kernel ports + own domain    |
| `lean/`        | thin QC adapters (AlphaModel, etc.)        | AlgorithmImports + use cases |

**The dependency rule:** imports point inward. `lean/` knows about `application/`;
`application/` knows about `domain/`; `domain/` knows about nothing but the kernel.
`AlgorithmImports` appears ONLY in `*/lean/` and `shared/lean/mapping.py`.
`test_kernel_invariants.py::test_domain_has_no_lean_dependency` enforces this in CI.

## Why slices instead of layers-first

Layer-first repos (`/indicators`, `/models`, `/utils`) smear one feature across the
tree. Here, changing how momentum works touches exactly one folder. Adding a new
alpha = add `slices/mean_reversion/`, write its tests, add one line in `main.py`.
Nothing else moves. Slices share code only through `shared/kernel` — never sideways.

## TDD workflow

1. **Red** — write a domain test (`tests/slices/test_*.py`) describing the rule.
2. **Green** — implement in `slices/<name>/domain/` until it passes.
3. **Use case** — test orchestration against `FakeClock` / `FakeMarketData`.
4. **Adapter last** — wrap in a thin LEAN model; it contains no logic worth testing
   in isolation, so it is validated by backtest, not unit tests.

```bash
pip install pytest
pytest -q          # 19 passed — no LEAN runtime required
```

## Running on QuantConnect

Upload the project (or `lean cloud push` with the CLI). LEAN finds
`CleanArchitectureStrategy` in `main.py`; everything under `src/` ships alongside it.
Tune behavior via the frozen `*Params` dataclasses in `main.py` — adapters never change.

## Extending

- **New alpha:** new slice with `domain → application → lean`, register via `add_alpha`.
- **Smarter execution:** add `domain/` to the execution slice (e.g., TWAP scheduling
  math), test it pure, wrap it in an `ExecutionModel`.
- **Regime filters / HMM:** model as a domain service in a `regime_detection` slice;
  inject its output into alpha use cases through a port.

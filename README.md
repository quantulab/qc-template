# Anatomy of a QuantConnect Strategy

### Clean Architecture · Vertically Sliced · Test-Driven

A production-shaped [QuantConnect LEAN](https://www.quantconnect.com/docs/v2/writing-algorithms)
algorithm skeleton that treats a trading strategy like real software, not a notebook.
Every behavior is a **vertical slice** mapped 1:1 onto a QuantConnect Algorithm Framework
module. All trading logic is kept **framework-free** and **fully unit-tested** — LEAN only
ever touches thin adapters at the edges.

```
LEAN runtime ──▶ thin adapters ──▶ use cases ──▶ pure domain logic
   (edge)         src/**/lean/    application/      domain/ + kernel
                  ↑ the only place AlgorithmImports is allowed
```

The payoff: **19 tests run in milliseconds with no LEAN runtime, no data subscription,
and no cloud round-trip.** You design and prove a strategy's logic on your laptop, then
ship the same objects into LEAN unchanged.

---

## Table of contents

- [Why this exists](#why-this-exists)
- [The core idea: vertical slices over layer-first](#the-core-idea-vertical-slices-over-layer-first)
- [The dependency rule (enforced in CI)](#the-dependency-rule-enforced-in-ci)
- [Repository layout](#repository-layout)
- [The shared kernel](#the-shared-kernel)
- [The anti-corruption layer](#the-anti-corruption-layer)
- [Anatomy of a slice](#anatomy-of-a-slice)
- [The five slices in detail](#the-five-slices-in-detail)
- [End-to-end data flow](#end-to-end-data-flow)
- [Testing strategy](#testing-strategy)
- [Running it](#running-it)
- [Tuning behavior](#tuning-behavior)
- [Adding a new slice (the TDD loop)](#adding-a-new-slice-the-tdd-loop)
- [LEAN gotchas this repo already solved](#lean-gotchas-this-repo-already-solved)
- [Conventions](#conventions)
- [FAQ](#faq)

---

## Why this exists

A typical QuantConnect algorithm is one giant `QCAlgorithm` subclass where indicator math,
position sizing, risk rules, and order plumbing are all braided together and reachable only
through the LEAN engine. That code is hard to reason about and nearly impossible to unit test:
to check a single sizing rule you have to spin up the whole backtest.

This project applies **Clean Architecture** to fix that. The trading *decisions* — the parts
that actually make or lose money — live in plain Python with zero LEAN imports. They depend
only on small interfaces (`Protocol`s). LEAN-specific code is pushed to the outermost ring,
where it does nothing but translate between LEAN's types and ours and forward calls inward.

Because the decision logic never imports `AlgorithmImports`, you can:

- run the full test suite **anywhere** Python runs (CI, pre-commit, a plane),
- substitute fake market data and a fake clock to test edge cases deterministically,
- refactor a rule with a fast red/green/refactor loop instead of a multi-minute backtest,
- read one folder to understand one feature, end to end.

---

## The core idea: vertical slices over layer-first

Most repos organize **by technical layer**: `/indicators`, `/models`, `/risk`, `/utils`.
A single feature ("how momentum works") is then smeared across every one of those folders,
and any change forces you to touch all of them.

This repo organizes **by feature (vertical slice)**. Each slice is a self-contained folder
that owns one capability from pure math up to its LEAN adapter:

```
slices/momentum_alpha/
├── domain/        ← the momentum math
├── application/   ← the use case that orchestrates it
└── lean/          ← the AlphaModel adapter
```

Each slice maps to exactly one Algorithm Framework responsibility:

| Slice                | Framework module                  | Responsibility                        |
|----------------------|-----------------------------------|---------------------------------------|
| `universe_selection` | `UniverseSelectionModel`          | Which symbols are tradeable           |
| `momentum_alpha`     | `AlphaModel`                      | Directional views (Insights/Signals)  |
| `position_sizing`    | `PortfolioConstructionModel`      | Views → target weights                |
| `risk_management`    | `RiskManagementModel`             | Veto/scale targets under drawdown     |
| `execution`          | `ExecutionModel`                  | Targets → orders                      |

**Changing how momentum works touches exactly one folder.** Adding a new alpha means adding
`slices/mean_reversion/`, writing its tests, and adding one line to `main.py`. Nothing else
moves. Slices never import each other; they communicate only through shared kernel types.

---

## The dependency rule (enforced in CI)

Imports point **inward only**. An outer ring may know about an inner ring; never the reverse.

```
   ┌──────────────────────────────────────────────┐
   │  lean/        thin QC adapters                │   ← AlgorithmImports lives ONLY here
   │  ┌────────────────────────────────────────┐  │
   │  │  application/   use cases (orchestrate) │  │
   │  │  ┌──────────────────────────────────┐  │  │
   │  │  │  domain/    pure decision logic   │  │  │
   │  │  │  ┌────────────────────────────┐  │  │  │
   │  │  │  │  shared/kernel  primitives  │  │  │  │   ← depends on nothing
   │  │  │  │  + ports (Protocols)        │  │  │  │
   │  │  │  └────────────────────────────┘  │  │  │
   │  │  └──────────────────────────────────┘  │  │
   │  └────────────────────────────────────────┘  │
   └──────────────────────────────────────────────┘

   lean/  →  application/  →  domain/  →  shared/kernel
```

| Layer          | Contains                                   | May import                       |
|----------------|--------------------------------------------|----------------------------------|
| `shared/kernel`| domain primitives + ports (`Protocol`s)    | nothing (stdlib only)            |
| `domain/`      | pure decision logic (math, rules)          | the kernel only                  |
| `application/` | use cases orchestrating ports + domain     | kernel ports + its own domain    |
| `lean/`        | thin QC adapters (`AlphaModel`, etc.)      | `AlgorithmImports` + use cases   |

**`AlgorithmImports` may appear ONLY in `src/**/lean/` files and `src/shared/lean/mapping.py`.
Nowhere else.** This is not a guideline — it is a test:

```python
# tests/slices/test_kernel_invariants.py
def test_domain_has_no_lean_dependency():
    """The kernel and every slice domain must import cleanly in an
    environment where AlgorithmImports does not exist."""
    import src.shared.kernel.signal
    import src.slices.momentum_alpha.domain.momentum
    import src.slices.position_sizing.domain.vol_target_sizer
    import src.slices.risk_management.domain.drawdown_policy
    import src.slices.universe_selection.domain.liquidity_rules
```

If a domain module ever grows a LEAN import, this test fails the build. **When you add a
slice, add its domain module to that test's import list.**

---

## Repository layout

```
QC-Anatomy/
├── main.py                       ← composition root (the ONLY file LEAN wires up)
├── config.json                   ← QC cloud project binding (do NOT hand-edit IDs)
├── pytest.ini                    ← testpaths + pythonpath
├── research.ipynb                ← scratch research notebook
├── CLAUDE.md                     ← repo guidance for AI agents
├── README.md                     ← you are here
│
├── src/
│   ├── shared/
│   │   ├── kernel/               ← pure primitives + ports (imports nothing)
│   │   │   ├── signal.py           Signal, Direction      (≈ LEAN Insight)
│   │   │   ├── bar.py              Bar                    (≈ LEAN TradeBar)
│   │   │   ├── target.py           WeightTarget           (≈ LEAN PortfolioTarget)
│   │   │   └── ports.py            Clock, MarketDataReader, PortfolioReader
│   │   └── lean/
│   │       └── mapping.py        ← anti-corruption layer (QC ⇄ domain)
│   │
│   └── slices/                   ← one slice per Framework module
│       ├── universe_selection/     domain/ + lean/                  → UniverseSelectionModel
│       ├── momentum_alpha/         domain/ + application/ + lean/   → AlphaModel
│       ├── position_sizing/        domain/ + application/ + lean/   → PortfolioConstructionModel
│       ├── risk_management/        domain/ + lean/                  → RiskManagementModel
│       └── execution/              lean/                            → ExecutionModel
│
└── tests/
    ├── fakes/builders.py         ← fake ports + test-data builders
    └── slices/                   ← one test module per slice + the architecture test
        ├── test_kernel_invariants.py
        ├── test_momentum_domain.py
        ├── test_momentum_use_case.py
        ├── test_position_sizing.py
        ├── test_drawdown_policy.py
        └── test_universe_rules.py
```

Note that not every slice needs all three layers. `execution` is currently a one-line LEAN
adapter (immediate execution has no decision logic worth testing), and `universe_selection`
and `risk_management` are pure-`domain` + `lean` with no separate use case. **You add a layer
only when there is logic that warrants it** — the architecture scales down as gracefully as
it scales up.

---

## The shared kernel

The kernel is the stable core every slice agrees on. It has no dependencies beyond the
standard library, and it is where domain primitives and ports live.

### Primitives (value objects)

```python
# signal.py — the domain analogue of a LEAN Insight
class Direction(Enum):
    LONG = 1; FLAT = 0; SHORT = -1

@dataclass(frozen=True)
class Signal:
    symbol: str
    direction: Direction
    confidence: float          # validated to [0.0, 1.0] in __post_init__
    generated_at: datetime
    horizon: timedelta

    @property
    def is_actionable(self) -> bool:
        return self.direction is not Direction.FLAT and self.confidence > 0.0
```

```python
# bar.py — the boundary type LEAN TradeBars are mapped into
@dataclass(frozen=True)
class Bar:
    symbol: str; end_time: datetime
    open: float; high: float; low: float; close: float; volume: float
    # __post_init__ rejects low > high
```

```python
# target.py — the domain analogue of a LEAN PortfolioTarget
@dataclass(frozen=True)
class WeightTarget:
    symbol: str
    weight: float              # signed fraction of equity; -0.05 = 5% short
    def scaled(self, factor: float) -> "WeightTarget": ...
```

All three are **frozen** (immutable) and **self-validating** — invalid states (`confidence`
outside `[0,1]`, an inverted bar) are rejected at construction, so downstream code never has
to defend against them.

### Ports (interfaces)

Ports are `Protocol`s — structural interfaces the application layer depends on instead of
depending on `QCAlgorithm`:

```python
# ports.py
class Clock(Protocol):
    def utc_now(self) -> datetime: ...

class MarketDataReader(Protocol):
    def trailing_bars(self, symbol: str, count: int) -> Sequence[Bar]: ...

class PortfolioReader(Protocol):
    def equity(self) -> float: ...
    def drawdown_from_peak(self) -> float: ...   # 0.0 .. 1.0
```

Because these are `Protocol`s, **anything with the right shape satisfies them** — no
inheritance required. In LEAN, an adapter wraps `QCAlgorithm`. In tests, a fake wraps a
dictionary. The use case cannot tell the difference, which is exactly the point.

---

## The anti-corruption layer

`src/shared/lean/mapping.py` is the **only shared module allowed to import
`AlgorithmImports`**. It translates between LEAN types and domain types, in both directions,
and it is carefully written to import cleanly even when LEAN is absent:

```python
try:
    from AlgorithmImports import Insight, InsightDirection, PortfolioTarget, TradeBar
    LEAN_AVAILABLE = True
except ImportError:          # running under pytest, outside LEAN
    LEAN_AVAILABLE = False

def trade_bar_to_domain(trade_bar) -> Bar: ...      # LEAN TradeBar → kernel Bar
def signal_to_insight(signal: Signal): ...          # kernel Signal → LEAN Insight
```

The `LEAN_AVAILABLE` guard is what lets the test suite import this module without the LEAN
runtime. **If you add a converter here, preserve that pattern** — guard any code path that
actually touches a LEAN type so the module stays importable under pytest.

---

## Anatomy of a slice

A fully-developed slice has three files that mirror the three rings:

```
slices/momentum_alpha/
├── domain/momentum.py                  ← MomentumCalculator + MomentumParams (pure)
├── application/generate_signals.py     ← GenerateMomentumSignals (use case)
└── lean/alpha_model.py                 ← MomentumAlphaModel (LEAN AlphaModel adapter)
```

**`domain/`** — the rule, as pure math. Takes plain `Bar`s, returns a plain `Signal | None`.
No clock, no I/O, no LEAN. Trivially testable.

**`application/`** — the use case. Holds the ports (`MarketDataReader`, `Clock`), pulls the
data each port provides, hands it to the domain object, and collects the results. Still
LEAN-free; tested against fakes.

**`lean/`** — the adapter. Subclasses the LEAN base class (`AlphaModel`), defines tiny inline
port implementations backed by `QCAlgorithm` (`_LeanClock`, `_LeanMarketData`), lazily builds
the use case on first call, and converts results back to LEAN types via `mapping.py`.
**It contains no logic worth unit-testing in isolation** — it is validated by backtest.

This separation means the interesting code (`domain` + `application`) is 100% covered by
fast tests, and the un-testable-without-LEAN code (`lean`) is as thin as physically possible.

---

## The five slices in detail

### 1. `universe_selection` → `UniverseSelectionModel`

Decides which symbols are tradeable. The domain is a pure function over framework-free
candidate records:

```python
def select_liquid(candidates, params) -> list[str]:
    eligible = [c for c in candidates if c.price >= params.min_price]   # drop penny stocks
    ranked   = sorted(eligible, key=lambda c: c.dollar_volume, reverse=True)
    return [c.symbol for c in ranked[:params.top_n]]                    # keep the top N
```

The adapter (`LiquidUniverseModel`) maps LEAN `Fundamental` rows into `Candidate`s, calls
`select_liquid`, and maps the survivors back to LEAN symbols.
**Params:** `LiquidityParams(min_price=5.0, top_n=20)`.

### 2. `momentum_alpha` → `AlphaModel`

Generates directional views. The domain computes trailing return over a lookback window and
emits a `Signal` only when the move clears a threshold; confidence scales with the size of
the move and is capped at 1.0:

```python
ret = (window[-1].close / window[0].close) - 1.0
if abs(ret) < threshold: return None
direction  = Direction.LONG if ret > 0 else Direction.SHORT
confidence = min(abs(ret) / (threshold * 4), 1.0)
```

The use case (`GenerateMomentumSignals`) loops symbols, asks the `MarketDataReader` for
trailing bars, runs the calculator, and keeps only actionable signals. The adapter
(`MomentumAlphaModel`) tracks the active symbol set via `on_securities_changed`, builds the
use case lazily, and converts each `Signal` to a LEAN `Insight`.
**Params:** `MomentumParams(lookback=20, entry_threshold=0.02, horizon=5d)`.

### 3. `position_sizing` → `PortfolioConstructionModel`

Turns views into target weights. The domain allocates gross exposure across actionable
signals in proportion to confidence, caps any single name, and signs the weight by direction:

```python
raw    = (s.confidence / total_confidence) * max_gross_exposure
weight = min(raw, max_single_weight)
if s.direction is Direction.SHORT: weight = -weight
```

The adapter (`ConfidenceWeightedPortfolioModel`) maps incoming LEAN `Insight`s back into
domain `Signal`s, runs the use case, and emits `PortfolioTarget`s.
**Params:** `SizingParams(max_gross_exposure=1.0, max_single_weight=0.10)`.

### 4. `risk_management` → `RiskManagementModel`

Scales or kills exposure as drawdown deepens — a pure policy over weight targets:

```python
if current_drawdown >= hard_limit: return [t.scaled(0.0) for t in targets]   # flat
if current_drawdown <= soft_limit: return list(targets)                       # untouched
factor = 1.0 - (current_drawdown - soft_limit) / (hard_limit - soft_limit)    # linear
return [t.scaled(factor) for t in targets]
```

The adapter (`DrawdownRiskModel`) tracks peak equity, computes current drawdown from
`algorithm.portfolio`, and applies the policy.
**Params:** `DrawdownParams(soft_limit=0.05, hard_limit=0.10)` — the policy rejects
`hard ≤ soft` at construction.

### 5. `execution` → `ExecutionModel`

Currently a one-line subclass of LEAN's `ImmediateExecutionModel`. There is no decision logic
yet, so there is no `domain/` or `application/` layer. When you want TWAP/VWAP scheduling or
slippage-aware order slicing, you introduce `domain/` and `application/` here exactly as in
the other slices — the adapter stays thin.

---

## End-to-end data flow

A single bar of the backtest flows inward and back out:

```
LEAN engine
   │  on each slice of data, calls the framework modules in order:
   ▼
UniverseSelectionModel.select(fundamental)
   └─▶ Fundamental rows ──map──▶ Candidate[] ──select_liquid()──▶ chosen symbols
   ▼
AlphaModel.update(algorithm, data)
   └─▶ _LeanMarketData.trailing_bars() ──▶ Bar[] ──MomentumCalculator──▶ Signal[]
                                                          │
                                                signal_to_insight()
                                                          ▼
                                                   LEAN Insight[]
   ▼
PortfolioConstructionModel.create_targets(insights)
   └─▶ Insight[] ──map──▶ Signal[] ──ConfidenceWeightedSizer──▶ WeightTarget[]
                                                          │
                                              PortfolioTarget.percent()
                                                          ▼
                                                  LEAN PortfolioTarget[]
   ▼
RiskManagementModel.manage_risk(targets)
   └─▶ PortfolioTarget[] ──map──▶ WeightTarget[] ──DrawdownPolicy──▶ scaled WeightTarget[]
                                                          ▼
                                                  LEAN PortfolioTarget[]
   ▼
ExecutionModel.execute(targets)  →  orders to the market
```

Every `──map──` step happens in a `lean/` adapter or `mapping.py`. Everything between the maps
is pure, framework-free Python you can test in isolation.

---

## Testing strategy

There are **19 tests** and they need no LEAN runtime, no data subscription, and no network.

| Test file                      | Covers                          | Style                          |
|--------------------------------|---------------------------------|--------------------------------|
| `test_kernel_invariants.py`    | validation + the no-LEAN rule   | architecture / invariant       |
| `test_momentum_domain.py`      | momentum math                   | pure domain                    |
| `test_momentum_use_case.py`    | signal generation orchestration | use case + fake ports          |
| `test_position_sizing.py`      | confidence weighting + caps     | pure domain                    |
| `test_drawdown_policy.py`      | drawdown scaling                | pure domain                    |
| `test_universe_rules.py`       | liquidity filter + ranking      | pure domain                    |

**Fakes implement the kernel `Protocol`s**, so a use case runs in a test exactly as it runs
inside LEAN:

```python
# tests/fakes/builders.py
class FakeClock:
    def utc_now(self) -> datetime: return self.now

class FakeMarketData:
    def trailing_bars(self, symbol, count): return self._series.get(symbol, [])[-count:]
```

Plus data builders for deterministic price paths:

```python
bar_series("SPY", trending_closes(100, 0.08, 20))   # 20 bars trending +8%
```

A use-case test reads like a sentence:

```python
def test_emits_signals_only_for_trending_symbols():
    data = FakeMarketData({
        "AAPL": bar_series("AAPL", trending_closes(150, 0.10, 20)),   # +10% → LONG
        "KO":   bar_series("KO",   trending_closes(60, 0.001, 20)),   # flat → nothing
        "TSLA": bar_series("TSLA", trending_closes(250, -0.12, 20)),  # -12% → SHORT
    })
    signals = GenerateMomentumSignals(data, FakeClock(), MomentumParams(lookback=20)) \
                  .execute(["AAPL", "KO", "TSLA"])
    by_symbol = {s.symbol: s for s in signals}
    assert set(by_symbol) == {"AAPL", "TSLA"}
```

---

## Running it

### Tests (locally, anywhere)

```bash
pip install pytest          # there is no venv; pytest isn't on the default Python
pytest -q                   # 19 passed — no LEAN runtime required

pytest tests/slices/test_momentum_domain.py                 # one file
pytest tests/slices/test_momentum_domain.py::test_downtrend_emits_short   # one test
```

`pytest.ini` sets `pythonpath = .` so imports resolve from the repo root.

### Backtest (on QuantConnect)

Upload the project, or with the LEAN CLI:

```bash
lean cloud push            # sync local files to the bound cloud project
```

LEAN auto-discovers `CleanArchitectureStrategy` in `main.py`; everything under `src/` ships
alongside it. The cloud binding (`cloud-id`, `organization-id`, …) lives in `config.json` —
**do not hand-edit those IDs.**

The composition root is the whole strategy definition:

```python
# main.py
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
            ConfidenceWeightedPortfolioModel(SizingParams(max_single_weight=0.10)))
        self.add_risk_management(DrawdownRiskModel(DrawdownParams(0.05, 0.10)))
        self.set_execution(DefaultExecutionModel())
```

---

## Tuning behavior

**All tuning lives in frozen `*Params` dataclasses passed in from `main.py`.** To change how
the strategy behaves, edit the params — never the adapters or the domain.

| Param object      | Knobs                                          | Slice              |
|-------------------|------------------------------------------------|--------------------|
| `LiquidityParams` | `min_price`, `top_n`                           | universe_selection |
| `MomentumParams`  | `lookback`, `entry_threshold`, `horizon`       | momentum_alpha     |
| `SizingParams`    | `max_gross_exposure`, `max_single_weight`      | position_sizing    |
| `DrawdownParams`  | `soft_limit`, `hard_limit`                     | risk_management    |

Because the params are frozen dataclasses with defaults, they double as living documentation
of every tunable in the system.

---

## Adding a new slice (the TDD loop)

Say you want a mean-reversion alpha. Follow the rings outward:

1. **Red.** Write a domain test in `tests/slices/test_mean_reversion_domain.py` describing
   the rule with `bar_series` / `trending_closes`.
2. **Green.** Implement `slices/mean_reversion/domain/mean_reversion.py` (with a
   `MeanReversionParams` dataclass) until the test passes.
3. **Use case.** Add `slices/mean_reversion/application/...`, tested against `FakeClock` /
   `FakeMarketData`.
4. **Adapter.** Wrap it in a thin `slices/mean_reversion/lean/...` `AlphaModel`. No unit test —
   it is validated by backtest.
5. **Wire it.** Add one line in `main.py`'s `initialize` (`self.add_alpha(...)`).
6. **Guard it.** Add the new domain module to
   `test_kernel_invariants.py::test_domain_has_no_lean_dependency`'s import list.

Nothing outside the new folder + those two one-line edits changes.

---

## LEAN gotchas this repo already solved

These are real pythonnet / Framework quirks the adapters work around — preserve the
workarounds if you touch that code.

**1. Don't reference .NET enum members at import time.**
`InsightDirection.Up` etc. can raise `"error return without exception set"` during import,
because pythonnet can't resolve .NET enum members before the runtime is fully initialized.
The portfolio adapter maps on the *integer value* instead:

```python
def _to_direction(lean_direction) -> Direction:
    value = int(lean_direction)            # Up=1, Flat=0, Down=-1
    if value > 0: return Direction.LONG
    if value < 0: return Direction.SHORT
    return Direction.FLAT
```

**2. Filter out `None` portfolio targets.**
`PortfolioTarget.percent(...)` returns `None` when a weight can't be realized (e.g. the
security has no price yet). LEAN's `Framework.cs` dereferences each target's `Symbol`, so a
stray `None` causes a `NullReferenceException`. The adapter drops them:

```python
created = (PortfolioTarget.percent(algorithm, t.symbol, t.weight) for t in targets)
return [target for target in created if target is not None]
```

**3. `mapping.py` must import without LEAN.** The `LEAN_AVAILABLE` try/except guard is what
lets pytest import the anti-corruption layer. Keep any LEAN-touching path behind that guard.

---

## Conventions

- **LEAN's Python API is snake_case here** (`initialize`, `set_start_date`, `add_alpha`,
  `manage_risk`, `on_securities_changed`). Match it in adapters; use normal Python style in
  `domain/` and `application/`.
- **Value objects are frozen and self-validating.** Construct-time validation means downstream
  code never defends against impossible states.
- **Slices never import each other.** Shared code flows only through `shared/kernel`.
- **One slice = one Framework module.** If you're tempted to make a slice do two framework
  jobs, it's two slices.
- **Adapters stay dumb.** If you're writing an `if` with real consequences inside a `lean/`
  file, it probably belongs in `domain/` or `application/` where it can be tested.

---

## FAQ

**Why `Protocol`s instead of abstract base classes?**
Structural typing means a fake (or a LEAN adapter) satisfies a port just by having the right
methods — no inheritance, no registration. Tests stay lightweight and the kernel stays
dependency-free.

**Why is `execution` only one line?**
Immediate execution has no decision logic worth testing. The architecture lets a slice be as
thin as its responsibility demands; you grow it into `domain/` + `application/` only when you
add real logic (TWAP, slippage modeling, order slicing).

**Where do regime filters / HMMs / ML models go?**
Model them as a domain service in their own slice (e.g. `regime_detection`), expose their
output through a new port, and inject it into the alpha use case. The decision logic stays
pure and testable; only the data source is a LEAN adapter.

**Can I really develop a whole strategy without running LEAN?**
You can develop and prove all the *logic* — every signal, weight, and risk decision — with
fast unit tests. You still run a backtest to validate the thin adapters, data plumbing, and
realized performance. The split just means most of your iteration happens in milliseconds.
</content>
</invoke>

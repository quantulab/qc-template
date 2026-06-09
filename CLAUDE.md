# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A QuantConnect LEAN algorithm built as a **vertically-sliced clean architecture**. All trading logic is kept framework-free and unit-tested; LEAN only ever touches thin adapters. See `README.md` for the full rationale.

## Commands

```bash
pytest -q                                  # run all tests (19) — no LEAN runtime needed
pytest tests/slices/test_momentum_domain.py            # single test file
pytest tests/slices/test_momentum_domain.py::test_name # single test
```

There is no local venv and `pytest` is not on the default Python; install it first (`pip install pytest`) if the command is missing. Tests import nothing from LEAN, so they run anywhere.

To run on QuantConnect, upload the project or `lean cloud push`. LEAN auto-discovers `CleanArchitectureStrategy` in `main.py`. `config.json` holds the cloud project binding; do not hand-edit its IDs.

## The dependency rule (enforced)

Imports point **inward** only:

```
lean/  →  application/  →  domain/  →  shared/kernel
```

- `domain/` — pure decision logic (math, rules). Imports the kernel only. No I/O, no clock, no LEAN.
- `application/` — use cases orchestrating ports + domain. Imports kernel ports + its own domain.
- `lean/` — thin QC adapters (AlphaModel, etc.). Imports `AlgorithmImports` + its use cases.

**`AlgorithmImports` may appear ONLY in `*/lean/` files and `src/shared/lean/mapping.py`.** Nowhere else. `tests/slices/test_kernel_invariants.py::test_domain_has_no_lean_dependency` fails the build if a domain module gains a LEAN import — when you add a slice, add its domain module to that test's import list.

## How a slice is wired

Each slice maps 1:1 to one Algorithm Framework module. A request flows: LEAN calls the adapter (e.g. `MomentumAlphaModel.update`) → the adapter lazily builds the use case, injecting LEAN-backed port implementations (`_LeanClock`, `_LeanMarketData` defined inline in the adapter) → the use case calls pure domain logic → results convert back to LEAN types via `shared/lean/mapping.py` (`signal_to_insight`, `trade_bar_to_domain`).

The kernel defines domain primitives (`Signal`, `Bar`, `WeightTarget`) and ports as `Protocol`s (`Clock`, `MarketDataReader`, `PortfolioReader`). Tests substitute fakes (`tests/fakes/builders.py`: `FakeClock`, `FakeMarketData`) that implement the same Protocols, so use cases run identically in tests and in LEAN.

## Conventions

- **LEAN's Python API is snake_case here** (`initialize`, `set_start_date`, `add_alpha`, `manage_risk`). Match it in adapters; use normal Python style in domain/application.
- **All tuning lives in frozen `*Params` dataclasses** (`MomentumParams`, `SizingParams`, `DrawdownParams`, `LiquidityParams`) passed into models from `main.py`. Change behavior by editing params in `main.py`, never by editing adapters.
- `mapping.py` guards on `LEAN_AVAILABLE` so the module imports cleanly under pytest; preserve that pattern if you add converters.

## Adding a slice (TDD)

1. Write a domain test in `tests/slices/`, implement under `slices/<name>/domain/` until green.
2. Add an `application/` use case tested against the fake ports.
3. Wrap it in a thin `lean/` adapter (validated by backtest, not unit test).
4. Register it with one line in `main.py`'s `initialize`, and add the domain module to `test_kernel_invariants.py`.

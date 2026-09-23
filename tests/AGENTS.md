<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# Testing Navigate

Four pytest suites, two make targets that smoke-run committed decks, shared
helpers in `tests/helpers/`, and each simulating suite's decks under its own
`simulations/`. The layout encodes which suite answers which question.

## Where a check belongs

- Exact behaviour of a function or class, with an expected value derivable
  independently of the implementation → `tests/unit` (conventions:
  `tests/unit/README.md`).
- Coverage of the DSL attribute/command surface → `tests/attribute` (no
  README; conventions: the module docstrings of `test_attribute_coverage.py`,
  `test_report_properties.py`, `test_reference_manual_coverage.py` and
  `test_report_property_docs.py`). The third of these maps a node type to its
  manual page, so a new page under `docs/reference_manual/` that describes no
  node is listed in `tests/helpers/reference_manual.py`; the fourth reads the
  report-property appendix of `report.md`, which carries no headings, from the
  sentence that leads each table in.
- "Did simulation results change when they shouldn't have?" →
  `tests/regression` (golden baselines; conventions:
  `tests/regression/README.md`).
- "Shipped decks still parse and run" → `make test-tutorials` /
  `make test-examples` (exit-code smoke over the committed tutorial and
  example decks; never add assertions there).

## Rules for every test change

- Expected values come from an independent oracle or from domain reasoning,
  never from current output. A value read off today's output is a regression
  pin, and pinning is the regression suite's job.
- Every deck whose results are asserted pins the solver through its suite's
  `simulations/0_includes/options.inc` and pins scenario inputs as explicit
  constants; assumption defaults are imported only where the calibrated
  values are themselves the tested mechanism. The attribute coverage deck,
  whose results are not asserted, leaves `Solver = AUTOMATIC`.
- Full simulations go through `helpers.simulation.run_simulation` and call
  `check_invariants` from the same module before their own assertions, never
  the `navigate` CLI: its `--solver` flag overrides the deck's pin.
- Numeric tolerances are module-level constants with the rationale in a
  comment on the constant.
- A change to a file under a suite's `simulations/0_includes/` re-sizes every
  deck including it, and every guardrail or baseline built on those decks.

## Running

- `pyproject.toml` puts `-x` in `addopts`, so a bare `pytest` stops at the
  first failure; the guardrail and regression targets pass `--maxfail=0` so
  one failure cannot mask the rest. Use the make targets.
- `--regen-baselines` is registered by `tests/regression/conftest.py`, so it
  exists only when `tests/regression/` is on the pytest command line;
  `make regen-regression` is the way.
- CI runs the suites against the built wheel, not the checkout: a test that
  depends on a file absent from the wheel passes locally and fails only in CI.
- Wall clock: `test-unit`, `test-attribute` and `test-regression` take a few
  seconds each, `test-guardrails` about 10 s, `test-tutorials` about 15 s and
  `test-examples` about a minute, longer with HiGHS than with Gurobi.

## What a test change touches

- A new DSL attribute or command goes into the attribute coverage deck under
  `tests/attribute/simulations/attribute_coverage/includes/`: the include for
  its node group, that include's "Attributes covered" or "Commands covered"
  header, and for a `SECTION_BOTH` attribute or command also the `EVENTS`
  include `ft_events.inc`. Nothing checks the deck against the registry, so
  an omission is never noticed (issue #168 is one such omission).
- A property added to the shared regression report follows the header
  comment of `tests/regression/simulations/0_includes/report.inc`.
  `tests/attribute/test_report_properties.py` checks that it resolves to a
  profile getter; nothing checks that a committed deck activates it, and an
  all-NaN column compares equal to its baseline and carries no signal.
- A new regression deck: exact comparison at first, activation guards, and
  the baseline in a commit of its own; `tests/regression/README.md`.

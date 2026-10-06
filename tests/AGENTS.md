<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# Testing Navigate

Four pytest suites, two make targets that smoke-run committed decks, shared
helpers in `tests/helpers/`, and each simulating suite's decks under its own
`simulations/`. The layout encodes which suite answers which question.
`README.md` in this folder is the short version for a first test.

## What earns a test

A test earns its place when its failure points to a decision Navigate made
that a plausible change could silently break. In practice:

- parser input becomes the right node state, or the right error;
- a node's control flow: eligibility, caps, allocation, ordering;
- a non-trivial algorithm, at the narrowest module that owns it;
- a unit, sign or time-step convention, once, where the convention lives;
- a user-facing DSL error message, once per rule;
- the direction in which the model responds to an input.

What does not earn a test, and is deleted when found:

- a guarantee of a library Navigate uses: numpy indexing and interpolation,
  scipy, argparse, `deepcopy`, dict lookups;
- a test that restates the formula it checks, or a corollary of a formula
  another test already pins;
- a happy path or an identity: construction, field assignment, "the accepted
  value is returned", "the valid deck parses";
- one rule re-tested per caller, per type or per permutation;
- mock choreography that mirrors the implementation's call sequence, and
  screens of setup for a one-line assertion;
- a pin for a bug whose code path no longer exists.

The suite's value is the precision of its signal, not its size. When a
behaviour-preserving refactor forces test rewrites beyond import paths, the
tests sit at the wrong altitude: move them up to the surviving surface.

## Where a check belongs

- Exact behaviour of a function, class or node, with an expected value
  derivable independently of the implementation → `tests/unit`
  (conventions: `tests/unit/README.md`).
- A convention `CODESTYLE.md` states, checked by reflection over the code
  instead of by an expected value → `tests/unit`. The rule lives in
  `CODESTYLE.md` and the test only checks conformance to it:
  `tests/unit/core/test_profile_getters.py` and
  `tests/unit/core/test_expectation_getters.py`.
- Coverage of the DSL attribute and command surface → `tests/attribute`.
  The coverage deck under `simulations/attribute_coverage/` sets every
  attribute and command once, and `test_attribute_coverage.py` checks the
  deck against the parser registries, so a new attribute that the deck does
  not use fails the suite. `test_reference_manual_coverage.py` and
  `test_report_property_docs.py` check the hand-written manual against the
  registries and the profile getters; a new page under
  `docs/reference_manual/` that describes no node is listed in
  `tests/helpers/reference_manual.py`.
- "Does the model still respond the right way?" → `tests/behaviour`: pairs
  of decks that differ by one input, asserting only the direction of the
  response (conventions: `tests/behaviour/README.md`).
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
  constants. The attribute coverage deck, whose results are not asserted,
  leaves `Solver = AUTOMATIC`.
- Full simulations go through `helpers.simulation.run_simulation` and call
  `check_invariants` from the same module before their own assertions, never
  the `navigate` CLI: its `--solver` flag overrides the deck's pin.
- Numeric tolerances are module-level constants with the rationale in a
  comment on the constant.
- A change to a file under a suite's `simulations/0_includes/` re-sizes every
  deck including it, and every baseline or direction built on those decks.

## Running

- `pyproject.toml` puts `-x` in `addopts`, so a bare `pytest` stops at the
  first failure; the behaviour and regression targets pass `--maxfail=0` so
  one failure cannot mask the rest. Use the make targets.
- `--regen-baselines` is registered by `tests/regression/conftest.py`, so it
  exists only when `tests/regression/` is on the pytest command line;
  `make regen-regression` is the way.
- CI runs the suites against the built wheel, not the checkout: a test that
  depends on a file absent from the wheel passes locally and fails only in CI.
- Wall clock: `test-unit`, `test-attribute` and `test-regression` take a few
  seconds each, `test-behaviour` about 10 s, `test-tutorials` about 15 s and
  `test-examples` about a minute, longer with HiGHS than with Gurobi.

## What a test change touches

- A new DSL attribute or command goes into the attribute coverage deck under
  `tests/attribute/simulations/attribute_coverage/includes/`: the include for
  its node group and that include's "Attributes covered" or "Commands
  covered" header. The registry check fails until it is there. For a
  `SECTION_BOTH` attribute, also assign it in the `EVENTS` include
  `ft_events.inc` when its EVENTS path differs from its DEFINE path.
- A property added to the shared regression report follows the header
  comment of `tests/regression/simulations/0_includes/report.inc`.
  `tests/attribute/test_report_properties.py` checks that it resolves to a
  profile getter; nothing checks that a committed deck activates it, and an
  all-NaN column compares equal to its baseline and carries no signal.
- A new regression deck: exact comparison at first, activation guards, and
  the baseline in a commit of its own; `tests/regression/README.md`.
- A new behaviour pair: a base deck, a perturbed deck that adds one
  `Include`, an activation guard, and a direction argued from the domain;
  `tests/behaviour/README.md`.

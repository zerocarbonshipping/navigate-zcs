<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# Testing Navigate

Two pytest suites, `unit/` and `end_to_end/`, with shared helpers in `helpers/`
and the end-to-end decks under `end_to_end/simulations/`. There is also a smoke
run of the example decks, and a result comparison that maintenance pull requests
must pass.

## Agents propose tests, they do not write them

A coding agent never writes, edits or deletes a test unless the user explicitly
asks for that test. This covers test modules, helpers, fixtures and the decks
under `end_to_end/simulations/`. When a change makes a test critical or
sensible by the criteria below, the agent proposes it in its reply or in the
pull request's Limitations:

- the decision the test pins, in one sentence;
- the suite and module it belongs in;
- how the expected value is derived without running the code: by hand, from
  the reference manual, or from domain reasoning.

A human decides whether it gets written. When an existing test fails, the
agent first checks whether the code under test is wrong, and reports the
failure; it does not change the test to make it pass. Suggest sparingly: a
proposal that fails the criteria below is noise.

## What earns a test

A test earns its place when its failure points to a decision Navigate made that
a plausible change could silently break. In practice:

- parser input becomes the right node state, or the right error;
- a non-trivial calculation, at the narrowest module that owns it;
- a unit, sign or time-step convention, once, where the convention lives;
- a user-facing DSL error message, once per rule;
- the direction in which the model responds to an input, or a proportionality
  or invariance the model must keep.

What does not earn a test, and is deleted when found:

- a guarantee of a library Navigate uses: numpy, scipy, argparse, `deepcopy`;
- a test that restates the formula it checks, or a corollary of a formula
  another test already pins;
- a happy path or an identity: construction, field assignment, "the accepted
  value is returned", "the valid deck parses";
- one rule re-tested per caller, per type or per permutation;
- mock choreography that mirrors the implementation's call sequence;
- a pin for a bug whose code path no longer exists.

The suite's value is the precision of its signal, not its size. When a
behaviour-preserving refactor forces test rewrites beyond import paths, the
tests sit at the wrong altitude.

## Where a check belongs

- **`unit/parser`** — DSL input becomes the right node state or error.
- **`unit/calculators`** — the calculators: expressions, tables,
  interpolation, extrapolation, transforms.
- **`unit/docs`** — the hand-written reference manual against the parser
  registries and the profile getters, both ways. A new page under
  `docs/reference_manual/` that describes no node is listed in
  `helpers/reference_manual.py`.
- **`end_to_end/test_attribute_coverage.py`** — the coverage deck under
  `end_to_end/simulations/attribute_coverage/` sets every registered attribute
  and command once, and the test checks it against the registries.
- **`end_to_end/test_*_combinations.py`, `test_fuel_price_response.py`,
  `test_calibration_direction.py`** — the direction of a model response: runs
  that differ by one input, asserting only which way the output moves.
- **`end_to_end/test_scaling.py`** — proportionality: scaling one input scales
  an output by the same factor.
- **`end_to_end/test_determinism.py`** — the same deck gives identical results,
  within one process and across processes with different hash seeds.
- **`make test-examples`** — the example decks still parse and run. It checks
  the exit code only; never add assertions there.
- **`make compare-results BASE=<ref>`, and the Compare results check on pull
  requests labelled `maintenance`** — a change meant to leave results alone
  leaves them alone. Every profile getter of a fixed set of decks is compared
  between the checkout and the base (`compare_results.py`,
  `helpers/snapshot.py`).

Results are never pinned to committed numbers: there are no golden baselines.

## Combination decks

The end-to-end decks are assembled by `helpers/combinations.py`. A deck family
holds a committed base in its `0_includes/` and template includes beside it;
each `%name%` value in a template is filled in per run. The `run_combination`
fixture in `end_to_end/conftest.py` writes a deck into a temporary directory,
runs it, checks the universal invariants and caches the run per module, so a
test can read another combination as its reference without running it twice.

## Rules for every test change

- Expected values come from an independent oracle or from domain reasoning,
  never from current output.
- Every deck whose results are asserted pins the solver and pins its scenario
  inputs as explicit constants. The attribute coverage deck, whose results are
  not asserted, leaves `Solver = AUTOMATIC`.
- Full simulations go through `helpers.simulation.run_simulation` and call
  `check_invariants` from the same module before their own assertions, never
  the `navigate` CLI: its `--solver` flag overrides the deck's pin.
- Numeric tolerances are module-level constants, with the rationale in a
  comment on the constant.
- A change to a file under a family's `0_includes/` re-sizes every deck built
  on it, and every direction argued from those inputs.

## Running

- `pyproject.toml` puts `-x` in `addopts`, so a bare `pytest` stops at the
  first failure. `make test-e2e` passes `--maxfail=0` so that one failure
  cannot mask the rest. Use the make targets.
- CI runs the suites against the built wheel, not the checkout: a test that
  depends on a file absent from the wheel passes locally and fails only in CI.
- Wall clock: `test-unit` takes a few seconds, `test-e2e` about half a minute
  and `test-examples` about a minute.

## Next candidates

Proposals only; nobody has agreed to write them yet:

- IntraFuelSensitivity direction: needs a second technology variant of one
  fuel in the combination fleet.
- FuelDemandSensitivity direction: needs a second production pathway in the
  supply deck.

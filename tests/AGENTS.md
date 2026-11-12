<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# Testing Navigate

## Agents propose tests; they do not write them

A coding agent does not write, edit or delete a test, helper, fixture or test
deck unless the user asks for that test. The suite is the owners' independent
check on work done by agents, and a test written or adjusted by the agent
whose change it checks no longer checks it independently.

Two edits are exceptions, because they keep the suite running against the
code as it now is without changing what it checks:

- carrying a rename or a signature change of something the tests use, a
  function, class, module or DSL name, into the existing tests that use it;
- keeping the attribute-coverage deck,
  `tests/end_to_end/simulations/attribute_coverage/`, in step with the DSL
  surface the node classes declare: using an attribute, command or ID value
  that was added, and renaming or removing one that was renamed or removed.

Neither edit changes what an assertion checks or any expected value. A renamed
name inside an assertion is carried like any other use of it.

## When a test fails

A test is never changed to make it pass. The two exceptions are not such
changes: after either, the tests check what they checked before.

- It fails because something it uses was renamed or its signature changed:
  carry the change into the test.
- The attribute-coverage test fails because the deck misses or misnames part
  of the DSL surface: bring the deck in step.
- Any other failure, an assertion or expected value included: look for the
  cause in the code under test first. If the code is wrong, fix it. If the
  test fails because the task changes the behaviour it pins, leave the test as
  it is and report the failure, and why the behaviour moved, in the pull
  request; the owners decide what the test should now assert.

## Proposing a test

Where a change makes a test worthwhile by the scope below, propose it in the
pull request, under Limitations, where the owners review it: the decision it
pins, the module it belongs in, and how its expected value is derived
independently of the implementation. A human decides.

## Scope

The suite is deliberately small. A test earns its place only when a plausible
change could silently break the decision it pins.

**`unit/`**

- `calculators/` — expressions, tables, interpolation, extrapolation,
  transforms.
- `parser/` — DSL input becomes the right node state, or the right error.
- `docs/` — the reference manual matches the deck surface and the results,
  both ways.

**`end_to_end/`**

- Attribute coverage — one deck sets every attribute and command the node
  classes declare, and every ID value, once.
- Behaviour — runs that differ by one input, asserting only the direction
  the output moves; for example, raising a fleet or producer calibration
  parameter moves its response up. Kept to about ten, low-hanging fruit first.
- Combinations — every combination of one node's options runs, and the
  effect each option must have on the results is asserted.
- Linearity and invariance — scaling one input scales an output by the same
  factor. Kept to about five.
- Determinism — one deck gives identical results on every run.

**Not tested:** basic maths, the bunker constraint, guarantees of the
libraries Navigate uses, happy paths and identities, a test that restates the
formula it checks, one rule repeated per caller or type, and mock
choreography.

Expected values come from an independent oracle or domain reasoning, never
from current output. There are no golden baselines.

## What a proposal can build on

- `unit/conftest.py` — `write_deck` and `read_deck` write a small deck from
  its DEFINE and EVENTS text and parse it.
- `helpers/parser_decks.py` — deck snippets and a default-library builder for
  parser tests that run without the shipped assumptions.
- `end_to_end/conftest.py` — `run_combination` runs a combination deck (a
  base in `end_to_end/simulations/combinations/0_includes/` plus template
  includes, `helpers/combinations.py`) and caches its results per module.
- `helpers/simulation.py` — `run_simulation` runs a deck in-process and
  `check_invariants` checks what every run must satisfy.
- `helpers/deck_surface.py` and `helpers/reference_manual.py` — the deck
  surface read off the node classes, and readers of the manual's pages.

## Running

`make test-unit`, `make test-e2e`, `make test-examples`, `make test-all`;
`make check` runs lint and the unit suite. Each runs the checkout's own code
and `assumptions/`; a git worktree needs its own `make pip-setup` first.
`make test-unit` stops at the first failure, `make test-e2e` runs on through
all of them. To run one file outside make, set the assumptions too, since the
helpers read `ASSUMPTIONS_DATA_DIR` before the checkout's own folder:
`ASSUMPTIONS_DATA_DIR=$PWD/assumptions .venv/bin/python -m pytest <file>`.
`make compare-results BASE=<ref>` checks that a change meant to leave results
alone leaves them alone; it is not a test suite.

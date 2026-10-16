<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# Testing Navigate

## Agents propose tests, they do not write them

A coding agent never writes, edits or deletes a test, helper, fixture or test
deck unless the user explicitly asks for that test. Where a change makes a test
worthwhile, the agent proposes it: the decision it pins, the module it belongs
in, and how the expected value is derived without running the code. A human
decides. When a test fails, the agent checks the code under test first and
reports the failure; it never changes the test to make it pass.

## Scope

The suite is deliberately small. A test earns its place only when a plausible
change could silently break the decision it pins.

**`unit/`**

- `calculators/` — expressions, tables, interpolation, extrapolation,
  transforms.
- `parser/` — DSL input becomes the right node state, or the right error.
- `docs/` — the reference manual matches the parser registries and the
  profile getters, both ways.

**`end_to_end/`**

- Attribute coverage — one deck sets every registered attribute and command
  once.
- Behaviour — runs that differ by one input, asserting only the direction
  the output moves; for example, raising a fleet or producer calibration
  parameter moves its response up. Kept to about ten, low-hanging fruit first.
- Linearity and invariance — scaling one input scales an output by the same
  factor. Kept to about five.

**Not tested:** basic maths, the bunker constraint, guarantees of the
libraries Navigate uses, happy paths and identities, a test that restates the
formula it checks, one rule repeated per caller or type, and mock
choreography.

Expected values come from an independent oracle or domain reasoning, never
from current output. There are no golden baselines.

## Running

`make test-unit`, `make test-e2e`, `make test-examples`, `make test-all`.
`make compare-results BASE=<ref>` checks that a change meant to leave results
alone leaves them alone; it is not a test suite.

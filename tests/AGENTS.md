<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# Testing Navigate

## Agents propose tests; they do not write them

A coding agent does not write, edit or delete a test, helper, fixture or test
deck unless the user asks for that test. The suite is the owners' independent
check on work done by agents, and a test written or adjusted by the agent whose
change it checks no longer checks it independently. Three edits are exceptions,
because they keep the suite running against the code as it now is:

- carrying a rename or a signature change of something the tests use, a
  function, class, module or DSL name, into the existing tests that use it;
- keeping the attribute-coverage deck in step with the DSL surface the node
  classes declare: using an attribute, command or ID value that was added, and
  renaming or removing one that was renamed or removed;
- assigning a newly required attribute, one marked `required=True`, in the
  existing test decks that build its node and in `BASE` of
  `tests/unit/parser/test_required.py`, adding a node of its type to `BASE`,
  reachable from a root, where the type had no required attribute before; the
  pull request names the values assigned.

None of these edits changes what an assertion checks or any expected value. A
renamed name inside an assertion is carried like any other use of it.

A test is never changed to make it pass. For a failure no exception covers,
look for the cause in the code under test first. If the code is wrong, fix it.
If the task changes the behaviour the test pins, leave the test as it is and
ask the owner before opening the pull request, saying which test fails, why
the behaviour moved and what you propose it should assert; the owner decides,
and may ask you to make the edit.

## Proposing a test

Where a change makes a test worthwhile by the scope below, propose it under
Limitations in the pull request: the decision it pins, its module, and how its
expected value is derived independently of the implementation. A human decides.

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

## Running

To run one file outside make, set `ASSUMPTIONS_DATA_DIR`, which the helpers
read before the checkout's own folder:
`ASSUMPTIONS_DATA_DIR=$PWD/assumptions .venv/bin/python -m pytest <file>`.
`make compare-results BASE=<ref>` is a results comparison, not a test suite.

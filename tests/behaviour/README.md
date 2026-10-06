<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# Directional behaviour tests

Pairs of small decks that differ by one input. Each test runs both and
asserts the direction in which the model responds: raising the price of a
fuel lowers its uptake, removing a levy raises emissions. The suite answers
"does the model still respond the right way?" when a change is meant to move
results, where `tests/regression` can only say that they moved.

## Rules

- **Direction only.** Assert the sign of the response, never its size or an
  absolute bound. The direction comes from domain reasoning, stated in the
  test's docstring; a bound read off today's output belongs in a regression
  baseline, not here.
- **Horizon totals, with a margin.** Compare sums over the whole horizon, and
  require them to move by more than `MARGIN_REL` of the base value. The
  bunker LPs have non-unique optima, so a per-step value can flip sign on a
  tie that the total does not notice. The margin is one constant, with its
  rationale, for the whole suite; it is never widened per test.
- **Activation guard first.** Each test first asserts that the base deck
  exercises the mechanism (the levy collects, the threshold binds), so a
  direction cannot pass because both runs are inert.
- **A direction that fails is a finding.** Report it; do not weaken or drop
  the assertion to make the suite green. Tune the deck, not the assertion.

## Layout

```
tests/behaviour/
├── test_response_direction.py        # one test per pair
└── simulations/
    ├── 0_includes/*.inc              # solver pin and the shared scenario content
    └── <deck_name>/
        ├── <deck_name>.nav
        └── includes/*.inc            # the perturbation, for a perturbed deck
```

Every scenario input is pinned as an explicit constant in `0_includes/`, and
`0_includes/options.inc` pins the solver. A deck runs in a second or two.

## Adding a pair

1. Write the base deck from `0_includes/` files, or reuse an existing deck
   as the base.
2. Write the perturbed deck as the base deck plus exactly one `Include`, which
   changes one input.
3. Add a test that runs both through the `run` fixture, asserts the
   activation guard on the base, then calls `assert_rises` or
   `assert_falls` on each horizon total. Its docstring states why the domain
   demands that direction.
4. Size the perturbation so the response is clearly larger than the margin,
   and run the test a few times before committing it.

To inspect a deck by eye, run it without `-s`; every deck loads the default
and debug plots:

```
navigate tests/behaviour/simulations/<deck_name>/<deck_name>.nav -d ./assumptions
```

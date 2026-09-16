<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# Golden-baseline regression tests

Small committed decks whose report CSV output is compared cell-for-cell
against committed baselines. They answer "did results change when they
shouldn't?" — complementary to `tests/guardrails`, which answers "are results
still sane?" when a change is supposed to move them. A should-be-neutral
change (refactor, cleanup, typing) must leave this suite green; an intentional
result change must surface as a reviewable git diff of the baselines, never
as silent drift.

## Layout

```
tests/regression/
├── test_<deck_name>.py               # invariants, activation guards, golden compare
├── baselines/<deck_name>/*.csv       # the committed goldens
└── simulations/
    ├── 0_includes/                   # solver pin and the shared wide report
    └── <deck_name>/
        ├── <deck_name>.nav           # deck entry point
        ├── includes/*.inc            # deck-specific includes, constants pinned
        └── output/                   # run output (gitignored)
```

Each deck activates one mechanism, so a failing golden names the mechanism
that changed. Unlike guardrails there is no `BEHAVIOR.md` — the baseline is
the contract; the test module's docstring states the mechanism and why the
activation guards prove it fired.

## Comparison policy

Comparison defaults to exact (`rtol = atol = 0`), and a new deck starts
there. Both committed decks opt into the shared runner-noise floor
(`RUNNER_NOISE_RTOL`/`RUNNER_NOISE_ATOL` in `tests/helpers/baseline.py`, where
the evidence for the values lives): pinning the solver fixes neither its
thread count nor the CPU dispatch in its float kernels, so an LP with
non-unique optima can resolve ties differently from one machine to the next.
As of 2026-09-16 that is observed, not theoretical — one GitHub runner
diverged on a commit whose rerun, with the same image and pinned packages,
matched: nonzero cells at relative deviations up to 5.5e-14, exact-zero cells
up to 4.8e-11 as degenerate ties moved between adjacent year bins.

A tolerance or column exclusion (exact header tokens, no wildcards) is opted
into per deck and carries recorded evidence where its values are defined —
never a comparison default, and never widened to make a change pass. Failures
are structured: the report names files, columns, dates, and per-cell
deviations sorted by magnitude.

## Regenerating baselines

`make regen-regression` is the only sanctioned way. It reruns the decks, the
universal invariants, and each deck's activation guards before replacing
anything — a deck whose mechanism stopped firing cannot regenerate. Commit a
baseline update as its own commit: its git diff is the review material for
what the change did to results.

Triage of a red suite:

- Unintended change → fix the code, not the baseline.
- Intended change → regenerate, review the diff, and use the guardrails to
  argue "different and correct" rather than "different and broken".
- Structural failure (missing file or column) → the report writer logs
  swallowed per-sheet errors at ERROR level in the deck `.log`; the wide
  report's no-match lines for absent node types log at WARNING and are
  expected. A renamed node shows up as a missing plus an extra column.
- A column-reorder-only git diff after regeneration is benign; comparison
  matches columns by name.
- Regeneration ignores the tolerance, so a regenerated diff can still show a
  cell flipping between zero and ~1e-13 in an adjacent year bin: that is the
  runner noise the floor absorbs, not a result change.

## Deck rules

Guardrail conventions apply (`tests/guardrails/README.md`): pin the solver
(`0_includes/options.inc`), pin scenario inputs as explicit constants, size
the scenario by tuning deck inputs. In addition:

- Every deck has activation guards: assertions that its mechanism actually
  fired, plus wiring guards for inputs whose defaults would silently make the
  baseline insensitive (a zero discount rate, an unset `include_vessel`).
- Reports come from the shared `0_includes/report.inc`; deck-specific
  properties re-open `Report "regression"` in a deck-local include. Its
  header comment carries the property rules (no timing tokens, one call per
  line, no duplicates with the wildcards).
- Regeneration goes through pytest, never the `navigate` CLI: the CLI
  `--solver` flag overrides the deck's solver pin.

<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# Behavior guardrails

Small committed simulation decks that each isolate one desired model behavior
and enforce it with executable property assertions paired with prose intent.
They answer "are results still sane?" when a change is *supposed* to move
results — complementary to golden-baseline regression tests, which answer
"did results change when they shouldn't?". When an intentional change makes a
regression baseline fail by design, the guardrails are what distinguish
"different and correct" from "different and broken".

## Three tiers

1. **Universal invariants** — hold in every simulation:
   `helpers.simulation.check_invariants`, applied by every suite
   that runs full simulations (attribute coverage, guardrails). Candidates
   that cannot yet be honestly asserted (e.g. mass/energy balance, which is
   enforced as a hard LP constraint inside the bunker solve and cannot be
   independently re-derived by a test) stay out until they can. Note: the
   universal development-vs-constraint invariant normalizes by each step's
   actual length, but the per-deck pinned-to-constraint property tests use
   `EPS_DEVELOPMENT_REL`, which assumes yearly time steps; a deck with
   non-yearly steps needs a rate-normalized comparison there instead of a
   wider tolerance.
2. **Scenario properties** — per-deck executable assertions paired with
   intent prose. The core of this suite.
3. **Qualitative expectations** — behaviors not yet formalizable (trajectory
   shape), recorded as prose in the deck's `BEHAVIOR.md`, judged by humans or
   an AI in a reviewing role. Keep this tier small; migrate items to tier 2
   as they get formalized.

## Layout: one deck, one behavior

```
tests/guardrails/
├── test_<deck_name>.py               # the assertions
└── simulations/
    ├── 0_includes/*.inc              # includes shared between decks
    └── <deck_name>/
        ├── <deck_name>.nav           # deck entry point (pins the solver)
        ├── BEHAVIOR.md               # the intent prose (contract)
        └── includes/*.inc            # deck-specific includes
```

When one deck is a controlled variation of another (as
`supply_then_demand_constrained` is of `supply_constrained`), both include
the same `0_includes/` files and the variation is a small deck-local
override include — the "differs by exactly one constant" intent is then
enforced by construction instead of by comment.

Each deck isolates exactly one mechanism. Decks run in seconds — they are
meant to sit inside an edit–test loop. Run with:

```
make test-guardrails                  # all decks
pytest tests/guardrails/test_<deck_name>.py -v    # one deck
```

Tests use `helpers.simulation.run_simulation` (in-process
`SimulationManager`, no CLI) and call `check_invariants` before the
deck-specific assertions, with plot generation suppressed. To inspect a
deck's behavior visually, run it manually without `-s` — every deck loads
`DefaultPlot` and `DebugPlot`:

```
navigate tests/guardrails/simulations/<deck_name>/<deck_name>.nav -d ./assumptions
```

## The rules that keep guardrails honest

- **Properties derive from domain reasoning, never from current output.** A
  threshold read off what the model does today turns the guardrail into a
  regression test in disguise and will wrongly condemn legitimate new
  methods.
- **The prose contract exists independently of the assertions.** A failing
  guardrail is triaged against `BEHAVIOR.md`: either the implementation is
  wrong, or the property needs renegotiating with the domain owner.
  Editing assertions until they pass is never a fix.
- **Tuning sizes the scenario, not the property.** When building or adjusting
  a deck, tune deck inputs (constraints, capacities, regulation levels) until
  the scenario has the intended shape — never loosen an ε or window because
  a badly-sized deck fails.
- **Pin scenario inputs as explicit constants.** Fuel prices, WTT emissions,
  production economics, and plant sizing are hard-coded in the deck (port
  price/WTT overwrites, literal setter values), not imported from assumption
  defaults: a guardrail is a controlled experiment, and upstream assumption
  drift must not silently re-size it. Import defaults only where the
  calibrated values are themselves part of the tested mechanism (e.g. vessel
  CAPEX/OPEX in `no_incentive`).
- **Pin the solver.** Every deck sets `BunkerOptions { Solver = HIGHS }`:
  LPs with non-unique optima return solver-dependent solutions, so a fixed
  solver is a prerequisite for asserting on LP output at all (it also keeps
  the suite independent of a Gurobi license).
- **An honest failure is signal.** If a correctly-specified deck fails
  against current model behavior, report it — that is the suite doing its
  job, not a blocker to absorb.

## BEHAVIOR.md template

BEHAVIOR.md is the domain contract, not documentation of the test: it states
each expected property exactly once, and says nothing derivable from the test
module (which assertions exist, what they measure, tolerances). ε values and
their rationale live as comments on the constants in the test module.

```markdown
# BEHAVIOR: <deck_name>

## Mechanism isolated
One or two sentences: which model mechanism this deck exercises in isolation,
and what the deck does to isolate it.

## Why this behavior is right
Why the expected outcome is correct in the real world — economic/domain
reasoning, not model mechanics — stating each expected property once; its
numbers appear here and nowhere else in the file.

## Known limitations
What the deck deliberately does not test or excludes (e.g. an assertion
window that excludes a known-degenerate tail), so exclusions are not read as
endorsements.

## Qualitative expectations (tier 3, prose only)
Trajectory-shape expectations not yet formalizable as assertions.
```

<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# BEHAVIOR: supply_constrained

## Mechanism isolated

The demand signal propagating from the bunker algorithm to producer plant
development (`navigate/fuel/producer/producer_evolution.py` /
`producer_planning.py`). A GHG-intensity regulation with a shrinking threshold
and a remedial cost far above the e-ammonia abatement cost imposes
alternative-fuel demand on a single oil/ammonia fleet; the Producer's
`MaximumDevelopment = 1` plant/year is sized so low that supply can never
catch up with that demand. The fleet starts with a 30% ammonia-capable share
so the demand exists at scale from the first step — the deck tests demand
propagation, not fleet turnover speed.

## Why this behavior is right

When demand permanently exceeds what the Producer is allowed to build, a
correctly propagating demand signal leaves the Producer no reason to ever
build less than its constraint: plant development must sit at
`MaximumDevelopment` every year of the assertable window. Development below
the constraint while unmet demand exists means the demand signal is lost or
distorted somewhere between the bunker algorithm and producer planning.

## Assertions ↔ prose mapping

| Assertion (test_supply_constrained.py) | Property it checks | ε and why |
|---|---|---|
| `test_development_pinned_to_constraint` | development == MaximumDevelopment for every step in `[1, n − LeadTime)` | `EPS_DEV_REL = 0.0025`: development is recorded per calendar year against a nominal per-year constraint, so leap years deviate by up to 366/365.25 − 1 ≈ 0.21% |
| `test_demand_remains_unmet` | deck validity: remedial units stay positive, i.e. the scenario stays supply-constrained | none needed (strict positivity) |

## Diagnostics if this fails

In order:

1. The demand signal from the bunker algorithm no longer reaches producer
   planning (check the expected-demand path in
   `navigate/fuel/producer/producer_evolution.py::calculate_evolution_expectation`
   and the bunker demand expectations feeding it).
2. The development constraint is applied somewhere it should not be, or a
   utilization/ramp mechanism suppresses development despite unmet demand
   (check `calculate_constrained_uptakes` in
   `navigate/fuel/producer/producer_planning.py`, `MaximumRampUp`,
   `JumpStartFraction`).
3. The deck stopped being supply-constrained — e.g. plant `Capacity` grew or
   fleet demand shrank so supply catches up (then `test_demand_remains_unmet`
   fails too; re-size the deck inputs, not the property).
4. The property needs renegotiating with the domain owner — never edit the
   assertions or thresholds to make a change pass.

## Known limitations

- **The final `LeadTime` (5) years are excluded and their behavior is
  explicitly not desired**: buildout drops off at
  `end of simulation − lead time` because fuel from later plants would not
  come onstream within the model horizon. This is technically wrong behavior
  — it touches output that is effectively unused and has no impact on used
  output — and the exclusion of the tail from the assertion window must not
  be read as an endorsement of it.
- The first time step is excluded: it initializes the expectation process
  and takes no development decision.
- The deck pins `Solver = HIGHS` so results do not depend on a Gurobi
  license.

## Threshold ownership / provenance

The property (development pinned to the constraint while demand is unmet)
and the tail-exclusion framing are the domain owner's specification, 2026-08
(recorded in `ai-dev/notes/navigate-behavior-guardrails.md`). `EPS_DEV_REL`
derives from calendar-year accounting, not from a domain decision. Deck
sizing inputs (`MaximumDevelopment = 1`, remedial cost 1000 USD/t, threshold
trajectory, 30% initial ammonia share) were tuned 2026-08 to keep the
scenario permanently supply-constrained; they carry no domain meaning.

## Qualitative expectations (tier 3, prose only)

Cumulative supply should grow essentially linearly through the assertable
window (constant development rate × roughly constant plant capacity), with
consumption tracking supply — everything produced is bought while the
constraint binds.

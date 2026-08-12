<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# BEHAVIOR: supply_then_demand_constrained

## Mechanism isolated

The continuity of supply ramp-up relative to the demand signal. The deck is
identical to `supply_constrained` by construction — both include the same
`../0_includes/` files — except for one constant:
`includes/maximum_development.inc` overrides `MaximumDevelopment` to 3
(instead of 1), sized so supply catches up with the regulation-imposed
e-ammonia demand roughly halfway through the simulation (step 12 of 24 in
the tuning run). Before catch-up the Producer must sit at
its development constraint; after catch-up it must leave the constraint and
reduce capacity growth to track demand with a slight surplus, settling into
equilibrium rather than oscillating between over- and under-supply per time
step.

## Why this behavior is right

While demand exceeds what may be built, any rational buildout saturates the
constraint (as in `supply_constrained`). Once supply has caught up, continued
maximal buildout would produce runaway overcapacity, and dropping to zero
would create shortage in the next step: correct behavior is a continuous
transition into demand tracking. The slight surplus exists so demand jumps
within one time step (newbuilds and fuel conversions; the fleet replenishes
at roughly 4%/year) can be absorbed without a short-term squeeze. The surplus
is intended as a roughly constant absolute energy headroom — which is why the
assertion normalizes it by total fleet fuel demand rather than by
alternative-fuel demand, whose small early values would inflate the ratio.

## Assertions ↔ prose mapping

| Assertion (test_supply_then_demand_constrained.py) | Property it checks | ε and why |
|---|---|---|
| `test_supply_limited_before_catchup` | development == MaximumDevelopment for steps `[1, CATCHUP_STEP)` | `EPS_DEV_REL = 0.0025`, leap-year accounting (see supply_constrained) |
| `test_leaves_constraint_after_catchup` | development strictly below the constraint for `[CATCHUP_STEP, n − LeadTime)` | same ε, used as a strict margin |
| `test_no_supply_squeeze` | production ≥ consumption every post-catch-up step | 1e-6 relative, float noise |
| `test_surplus_band` | (nameplate capacity − consumption) / total fleet fuel demand within `[0.02, 0.12]` for `(CATCHUP_STEP, n − LeadTime)` | band pending domain-owner sign-off, see below |

`CATCHUP_STEP = 12` is a fixed configured index from the tuning run
(2026-08), not auto-detected: crossing detection on LP output would need its
own tolerance and could silently drift as unrelated model changes shift the
crossover by a step.

## Diagnostics if this fails

In order:

1. Ramp-down discontinuity: development oscillates (pinned/zero/pinned) after
   catch-up instead of tracking demand — check the demand-gap projection in
   `navigate/fuel/producer/producer_evolution.py` (the gap is evaluated at
   `t + LeadTime`) and `calculate_constrained_uptakes` in
   `producer_planning.py`.
2. The crossover moved because deck inputs' meaning changed (plant
   `Capacity`, `Uptime`, regulation trajectory): re-derive `CATCHUP_STEP`
   with a tuning run and update the constant with a provenance comment —
   this is deck re-sizing, not threshold softening.
3. Surplus out of band: the producer over- or under-provisions capacity
   relative to demand — check the capacity-vs-demand equilibrium logic in
   producer planning before touching the band.
4. The property (band, measurement) needs renegotiating with the domain
   owner — never edit the assertions or thresholds to make a change pass.

## Known limitations

- Same tail exclusion as `supply_constrained`: the final `LeadTime` (5) years
  are excluded because the foresight window runs past the simulation end —
  explicitly not-desired behavior, and the exclusion is not an endorsement.
- The first step is excluded (expectation initialization), and the catch-up
  step itself is excluded from the surplus band (the surplus builds up from
  zero during the transition).
- The deck pins `Solver = HIGHS`.

## Threshold ownership / provenance

**The surplus measurement and band need domain-owner confirmation.** In the
tuning run (2026-08) the producer holds *nameplate* capacity at ≈ 1.095–1.11×
consumption after catch-up — which is almost exactly `1 / Uptime`
(`uptime_plant_electro = 0.913`). That is: the model plans *usable* output
(capacity × uptime) ≈ demand with only a ~0–2% usable margin, and the
"~10% oversupply" the assertion currently observes on nameplate capacity is
largely the uptime factor, not a deliberate demand buffer. If the domain
intent is ~10% *usable* headroom above demand (room to absorb one
time-step's demand creation), current model behavior does not provide it and
this guardrail should be tightened to usable capacity — at which point it is
expected to fail until the producer planning is changed. Band `[0.02, 0.12]`
of total fleet fuel demand: proposed 2026-08 from the ~4%/year replenishment
reasoning, applied to nameplate capacity; not yet signed off.

Deck sizing inputs (`MaximumDevelopment = 3`, `CATCHUP_STEP = 12`, and the
regulation/fleet inputs shared with `supply_constrained`) were tuned 2026-08
and carry no domain meaning.

## Qualitative expectations (tier 3, prose only)

Development after catch-up should decline smoothly toward the fleet's demand
growth rate — a single continuous hand-off from constraint-driven to
demand-driven buildout, with no alternating over/under-build pattern.

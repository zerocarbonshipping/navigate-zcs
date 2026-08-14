<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# BEHAVIOR: supply_then_demand_constrained

## Mechanism isolated

The continuity of supply ramp-up relative to the demand signal:

- The deck is identical to `supply_constrained` by construction — both
  include the same `../0_includes/` files — except for one constant:
  `includes/maximum_development.inc` overrides `MaximumDevelopment` to 8
  (instead of 1).
- The override is sized so supply catches up with the regulation-imposed
  e-ammonia demand roughly halfway through the simulation (step 11 of 24;
  the sizing carries no domain meaning).
- Before catch-up the Producer must sit at its development constraint;
  after catch-up it must leave the constraint and reduce capacity growth to
  track demand with a slight surplus, settling into equilibrium rather than
  oscillating between over- and under-supply per time step.

## Why this behavior is right

- While demand exceeds supply, the Producer should build at its limit (as
  in `supply_constrained`).
- Once supply catches up, buildout must hand over continuously to demand
  tracking: staying maximal creates runaway overcapacity, stopping creates
  shortage the next step.
- A slight surplus must be kept so one-step demand jumps (the fleet
  replenishes at ~4%/year) cannot cause shortage and regulatory
  non-compliance: 2–12% of total fleet fuel demand, on *deliverable* supply
  (capacity × uptime) — a nameplate margin is no real buffer. Not yet
  signed off (2026-08-12).
- Post-catch-up the regulation must record no remedial units: remedial is
  priced far above the abatement cost, so buying any means demand was not
  met.

Both properties are known to fail against current model behavior
(2026-08-13) — open findings for the model, not thresholds to tune away:

- the producer plans deliverable output ≈ consumption with only a ~0–1%
  margin (surplus band);
- remedial units stay positive at most post-catch-up steps (zero-remedial).

A related anomaly — remedial units bought at steps where deliverable supply
still has slack — is root-caused to calibrated fuel-switching inertia (the
port bunkering-inertia floor and minimum-pilot-fuel saturation leave the
idle supply physically unusable to the fleet), not a bunker-LP defect;
whether the zero-remedial property should tolerate the fuel-switching rate
limit, or the deck should neutralize the inertia calibration, is an open
question (2026-08-14).

## Known limitations

- Same tail exclusion as `supply_constrained`: the final `LeadTime` (5) years
  are excluded because the foresight window runs past the simulation end —
  explicitly not-desired behavior, and the exclusion is not an endorsement.
- The first step is excluded (expectation initialization), and the catch-up
  step itself is excluded from the surplus band (the surplus builds up from
  zero during the transition).

## Qualitative expectations (tier 3, prose only)

- Development after catch-up should decline smoothly toward the fleet's
  demand growth rate — a single continuous hand-off from constraint-driven
  to demand-driven buildout, with no alternating over/under-build pattern.
- Observed (2026-08-12): the post-catch-up build rate oscillates noticeably
  (roughly 0.7–7.6 plants/year around a ~5/year trend) — a candidate for
  formalizing into a tier-2 smoothness assertion once the intended tolerance
  is decided.

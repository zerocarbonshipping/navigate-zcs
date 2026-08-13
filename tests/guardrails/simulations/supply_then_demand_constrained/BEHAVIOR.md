<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# BEHAVIOR: supply_then_demand_constrained

## Mechanism isolated

The continuity of supply ramp-up relative to the demand signal. The deck is
identical to `supply_constrained` by construction — both include the same
`../0_includes/` files — except for one constant:
`includes/maximum_development.inc` overrides `MaximumDevelopment` to 8
(instead of 1), sized so supply catches up with the regulation-imposed
e-ammonia demand roughly halfway through the simulation (step 11 of 24 in
the tuning run, 2026-08-12; the sizing carries no domain meaning). Before
catch-up the Producer must sit at its development constraint; after catch-up
it must leave the constraint and reduce capacity growth to track demand with
a slight surplus, settling into equilibrium rather than oscillating between
over- and under-supply per time step.

## Why this behavior is right

While demand exceeds what may be built, any rational buildout saturates the
constraint (as in `supply_constrained`). Once supply has caught up, continued
maximal buildout would produce runaway overcapacity, and dropping to zero
would create shortage in the next step: correct behavior is a continuous
transition into demand tracking. The slight surplus exists so demand jumps
within one time step (newbuilds and fuel conversions; the fleet replenishes
at roughly 4%/year) can be absorbed without accidental short-term
demand-exceeds-supply episodes, which trigger issues such as regulatory
non-compliance. It is therefore measured on *deliverable* supply
(capacity × uptime) — a nameplate margin that merely reflects the uptime
factor provides no such buffer (measurement settled by the domain owner,
2026-08-13: deliverable, explicitly not nameplate). The surplus is intended as
a roughly constant absolute energy headroom — which is why it is normalized
by total fleet fuel demand rather than by alternative-fuel demand, whose
small early values would inflate the ratio.

The surplus band is 2–12% of total fleet fuel demand — proposed 2026-08-12
from the ~4%/year replenishment reasoning, not yet signed off by the domain
owner. Known to fail against current model behavior (2026-08-13): the tuning
run shows the producer plans deliverable output ≈ consumption with only a
~0–1% margin, so the floor fails — an open finding for the model, not a
threshold to tune away (recorded in
`ai-dev/notes/navigate-behavior-guardrails.md`).

## Known limitations

- Same tail exclusion as `supply_constrained`: the final `LeadTime` (5) years
  are excluded because the foresight window runs past the simulation end —
  explicitly not-desired behavior, and the exclusion is not an endorsement.
- The first step is excluded (expectation initialization), and the catch-up
  step itself is excluded from the surplus band (the surplus builds up from
  zero during the transition).

## Qualitative expectations (tier 3, prose only)

Development after catch-up should decline smoothly toward the fleet's demand
growth rate — a single continuous hand-off from constraint-driven to
demand-driven buildout, with no alternating over/under-build pattern.
Observed in the tuning run (2026-08-12): the post-catch-up build rate
oscillates noticeably (roughly 0.7–7.6 plants/year around a ~5/year trend)
even though delivered supply never drops below demand — a candidate for
formalizing into a tier-2 smoothness assertion once the intended tolerance
is decided.

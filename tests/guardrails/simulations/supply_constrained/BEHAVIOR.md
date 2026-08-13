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
propagation, not fleet turnover speed. The sizing inputs (development limit,
remedial cost, threshold trajectory, initial ammonia share, the pinned
economics in `../0_includes/`) were tuned 2026-08-12 to keep the scenario
permanently supply-constrained; they carry no domain meaning.

## Why this behavior is right

When demand permanently exceeds what the Producer is allowed to build, a
correctly propagating demand signal leaves the Producer no reason to ever
build less than its constraint: plant development must sit at
`MaximumDevelopment` every year of the assertable window. Development below
the constraint while unmet demand exists means the demand signal is lost or
distorted somewhere between the bunker algorithm and producer planning.

The property and the tail-exclusion framing (Known limitations) are the
domain owner's specification, 2026-08-12 (recorded in
`ai-dev/notes/navigate-behavior-guardrails.md`).

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

## Qualitative expectations (tier 3, prose only)

Cumulative supply should grow essentially linearly through the assertable
window (constant development rate × roughly constant plant capacity), with
consumption tracking supply — everything produced is bought while the
constraint binds.

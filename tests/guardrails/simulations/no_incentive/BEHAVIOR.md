<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# BEHAVIOR: no_incentive

## Mechanism isolated

The newbuild discrete choice model (nested logit over vessel LCOT,
`navigate/vessel/fleet/fleet_evolution.py`) in the complete absence of GHG
pricing: no `Regulation`, no `Levy`. Vessel choice is driven purely by the
domain-calibrated CAPEX/OPEX differentials of the four fuel variants of the
default `container_15000_teu` fleet. Fuel supply is deliberately ample
(high `MaximumDevelopment`, no feed constraints) so supply can never be the
reason a fuel gets a small share.

## Why this behavior is right

Absent any GHG pricing mechanism, oil and LNG are the cheapest fuels, so the
model should primarily build oil and methane vessels. A methanol dual-fuel
vessel is not much more expensive than an oil vessel, but in this scenario it
would operate fully on oil — and the model has no future GHG pricing in its
expectation — so there is no incentive to pay the premium: methanol should
stay a marginal choice (~2–3% market share at most). An ammonia vessel is a
significantly more expensive vessel that would likewise run on oil here, so
its share should be even smaller (~1%).

These numbers are the domain owner's expectations from economic reasoning;
they were explicitly not derived by running the model and reading off values.

## Assertions ↔ prose mapping

| Assertion (test_no_incentive.py) | Property it checks | ε and why |
|---|---|---|
| `test_methanol_share_marginal` | methanol market share ≤ ~3% at the final step | `EPS_SHARE = 0.005`: lumpy vessel counts + logit numerical noise |
| `test_ammonia_share_marginal` | ammonia market share ≤ ~1% at the final step | same |
| `test_oil_and_methane_dominate` | oil + methane ≥ 96% at the final step | same; floor derived from the two caps |

Shares are measured on `fleet.profile.get_existing_vessels()` at the final
time step (the domain claim is about long-run dominance, not any transient).

## Diagnostics if this fails

In order:

1. Dual-fuel vessel CAPEX/OPEX assumptions too low, flattening the vessel
   cost differences the choice is supposed to respond to (check the
   `container_15000_teu_*` CAPEX/OPEX forecasts and the vessels' fuel
   supply-system (PowerSystem) CAPEX in `assumptions/defaults/installation/`
   — the vessel side deliberately stays on these defaults; fuel-side
   economics are pinned in the deck, see Known limitations).
2. Sensitivity parameters of the discrete choice model too insensitive,
   producing a too-uniform allocation across near-equal-cost options (check
   `InterFuelSensitivity`/`IntraFuelSensitivity` in
   `assumptions/modules/installation/default_calibration.inc` and
   `calculate_asset_shares` in `navigate/investment/decision.py`).
3. The modeling approach itself needs changing to reflect this behavior
   (a small-but-real cost penalty with zero upside should map to a
   near-zero share, which a logit with calibrated odds ratios may be
   structurally unable to produce).
4. The property needs renegotiating with the domain owner — never edit the
   assertions or thresholds to make a change pass.

## Known limitations

- One fleet segment (15,000 TEU containers) stands in for the whole market;
  the claim is about the choice mechanism, not about segment coverage.
- All fuel-side economics (bunker prices, WTT emissions, production process
  costs, plant sizing) are pinned as explicit constants in the deck, so
  upstream assumption changes cannot silently move the cost differentials.
  Vessel CAPEX/OPEX deliberately stays on the calibrated installation
  defaults — those differentials are part of what this deck tests
  (diagnostic 1).
- The deck pins `Solver = HIGHS` so results do not depend on a Gurobi
  license.

## Threshold ownership / provenance

Methanol ≤ 2–3%, ammonia ≤ ~1%, measured as vessel-count market shares —
domain owner specification, 2026-08 (recorded in
`ai-dev/notes/navigate-behavior-guardrails.md`). Not revisited since.

## Qualitative expectations (tier 3, prose only)

Oil's share should erode slowly, if at all, over the horizon; there is no
mechanism that should produce a sharp mid-horizon transition in this deck.

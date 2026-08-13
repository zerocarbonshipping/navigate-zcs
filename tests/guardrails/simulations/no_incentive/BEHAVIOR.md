<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# BEHAVIOR: no_incentive

## Mechanism isolated

The fleet's investment decisions (`navigate/vessel/fleet/`) in the complete
absence of GHG pricing: no `Regulation`, no `Levy`. Two decision models are
exercised:

- the newbuild discrete choice model (nested logit over vessel LCOT,
  `fleet_evolution.py`), driven purely by the domain-calibrated CAPEX/OPEX
  differentials of the four fuel variants of the default
  `container_15000_teu` fleet;
- the efficiency levers: uptake of the fleet's energy-saving technologies
  (`fleet_technology.py`), operational speed (`navigate/route/speed.py`),
  and the global energy savings they produce.

Fuel supply is deliberately ample (high `MaximumDevelopment`, no feed
constraints) so supply can never be the reason a fuel gets a small share.

## Why this behavior is right

Absent any GHG pricing mechanism, oil and LNG are the cheapest fuels, so the
model should primarily build oil and methane vessels. A methanol dual-fuel
vessel is not much more expensive than an oil vessel, but in this scenario it
would operate fully on oil — and the model has no future GHG pricing in its
expectation — so there is no incentive to pay the premium: methanol should
stay a marginal choice (~2–3% market share at most). An ammonia vessel is a
significantly more expensive vessel that would likewise run on oil here, so
its share should be even smaller (~1%).

The same reasoning applies to the efficiency levers: with no GHG pricing,
nothing new incentivizes energy-saving effort over the horizon, so the
fleet-wide uptake of each efficiency technology, the operational speed, and
every series of the global_energy_saving plot (propulsion / electrical /
heat / technology / operational / total saving) must stay approximately at
their initial values.

These numbers are the domain owner's expectations from economic reasoning;
they were explicitly not derived by running the model and reading off values.

## Assertions ↔ prose mapping

| Assertion (test_no_incentive.py) | Property it checks | ε and why |
|---|---|---|
| `test_methanol_share_marginal` | methanol market share ≤ ~3% at the final step | `EPS_SHARE = 0.005`: lumpy vessel counts + logit numerical noise |
| `test_ammonia_share_marginal` | ammonia market share ≤ ~1% at the final step | same |
| `test_oil_and_methane_dominate` | oil + methane ≥ 96% at the final step | same; floor derived from the two caps |
| `test_global_savings_stable` | each global_energy_saving series stays within ±5 percentage points of its initial value, every step | `MAX_SAVING_DRIFT = 0.05`: absolute (pp) because operational saving starts at exactly 0, where a relative band is undefined |
| `test_technology_uptake_stable` | fleet-wide uptake of each technology stays within ±10 pp of its initial value, every step | `MAX_UPTAKE_DRIFT = 0.10`: absolute (pp), robust to lumpy vessel counts |
| `test_speed_stable` | fleet average speed stays within ±10% of its first computed value, every step | `MAX_SPEED_DRIFT_REL = 0.10`: relative — speed has a physical unit, no natural absolute scale |

Shares are measured on `fleet.profile.get_existing_vessels()` at the final
time step (the domain claim is about long-run dominance, not any transient).
Uptake is measured per technology with
`fleet.profile.get_fleet_technology_uptake()` — the existing-vessel-weighted
average that draws the "Fleet" line of the technology_uptake plot;
the saving series are those of the global_energy_saving plot; speed is
`fleet.profile.get_actual_speed()`, whose first step is NaN (no realized
speed yet), so the speed baseline is the first computed step.

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
3. For the efficiency drifts: technology cost/saving assumptions that make
   the packages strongly NPV-positive on pure fuel-cost savings (check the
   fleet's `Technology`/`TechnologyPackage` defaults in
   `assumptions/defaults/installation/` and the NPV construction in
   `navigate/vessel/fleet/fleet_technology.py`), and the choice calibration
   (`TechnologySensitivity` in `default_calibration.inc`, the deck-pinned
   `TechnologyCostOfCapital`).
4. For a speed drift: the speed-management inputs
   (`AllowSpeedManagement`, `MaximumSpeedChange`, `SpeedAlignment`) and the
   freight-rate signal the optimal-speed calculation responds to.
5. The modeling approach itself needs changing to reflect this behavior
   (a small-but-real cost penalty with zero upside should map to a
   near-zero share, which a logit with calibrated odds ratios may be
   structurally unable to produce).
6. The property needs renegotiating with the domain owner — never edit the
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
- Technology cost/saving data stays on the calibrated installation defaults
  (like vessel CAPEX/OPEX, it is part of the tested mechanism); only the
  technology-investment discount rate is pinned in the deck
  (`TechnologyCostOfCapital = 0.08`), because the installation defaults
  leave it unset and the model's fallback to vessel cost of capital warns
  that it inflates uptake.

## Threshold ownership / provenance

Methanol ≤ 2–3%, ammonia ≤ ~1%, measured as vessel-count market shares —
domain owner specification, 2026-08 (recorded in
`ai-dev/notes/navigate-behavior-guardrails.md`). Not revisited since.

Efficiency-lever drift bands — domain owner specification, 2026-08-13:
global savings ±5 pp, technology uptake ±10 pp, speed ±10% relative, each
against the series' initial value. Percentage-point (absolute)
interpretation for savings and uptake confirmed by the domain owner
(relative is undefined for operational saving, which starts at 0).
`TechnologyCostOfCapital = 0.08` (reference-manual example value) pinned in
the deck per domain-owner decision, same date; diagnostically the drift
barely responds to it (a 20% hurdle rate still ends air lubrication at 0.62
vs 0.69), so the choice is not load-bearing for the observed failure.

## Qualitative expectations (tier 3, prose only)

Oil's share should erode slowly, if at all, over the horizon; there is no
mechanism that should produce a sharp mid-horizon transition in this deck.

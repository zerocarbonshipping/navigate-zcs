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
model must primarily build oil and methane vessels. A methanol dual-fuel
vessel is not much more expensive than an oil vessel, but in this scenario it
would operate fully on oil — and the model has no future GHG pricing in its
expectation — so there is no incentive to pay the premium: methanol stays a
marginal choice, at most ~2–3% of the fleet, and ammonia (a significantly
more expensive vessel that would likewise run on oil here) at most ~1% —
both as vessel-count market shares at the final step, since the claim is
about long-run dominance, not any transient.

The same reasoning applies to the efficiency levers: with no GHG pricing,
nothing new incentivizes energy-saving effort over the horizon, so each
global energy-saving series must stay within ±5 percentage points of its
initial value, fleet-wide uptake of each technology within ±10 pp, and
operational speed within ±10% relative — every step. The saving and uptake
bands are percentage points (absolute) because operational saving starts at
exactly 0, where a relative band is undefined; speed has a physical unit and
no natural absolute scale, hence relative.

All numbers are the domain owner's specification from economic reasoning —
explicitly not derived by running the model and reading off values. Shares:
2026-08-12; drift bands and their pp interpretation: 2026-08-13; not
revisited since.

## Known limitations

- One fleet segment (15,000 TEU containers) stands in for the whole market;
  the claim is about the choice mechanism, not about segment coverage.
- All fuel-side economics (bunker prices, WTT emissions, production process
  costs, plant sizing) are pinned as explicit constants in the deck, so
  upstream assumption changes cannot silently move the cost differentials.
  Vessel CAPEX/OPEX deliberately stays on the calibrated installation
  defaults — those differentials are part of what this deck tests.
- Technology cost/saving data stays on the calibrated installation defaults
  (like vessel CAPEX/OPEX, it is part of the tested mechanism); only the
  technology-investment discount rate is pinned in the deck
  (`TechnologyCostOfCapital = 0.08`, the reference manual's example value;
  domain-owner decision 2026-08-13),
  because the installation defaults leave it unset and the model's fallback
  to vessel cost of capital warns that it inflates uptake.

## Qualitative expectations (tier 3, prose only)

Oil's share should erode slowly, if at all, over the horizon; there is no
mechanism that should produce a sharp mid-horizon transition in this deck.

<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# BEHAVIOR: no_incentive

## Mechanism isolated

The fleet's investment decisions (`navigate/fleet/`) in the complete
absence of GHG pricing: no `Regulation`, no `Levy`. Two decision models are
exercised:

- the newbuild discrete choice model (nested logit over vessel LCOT,
  `evolution.py`), driven purely by the domain-calibrated CAPEX/OPEX
  differentials of the four fuel variants of the default
  `container_15000_teu` fleet;
- the efficiency levers: uptake of the fleet's energy-saving technologies
  (`technology_adoption.py`), operational speed (`speed.py`),
  and the global energy savings they produce.

Fuel supply is deliberately ample (high `MaximumDevelopment`, no feed
constraints) so supply can never be the reason a fuel gets a small share.

## Why this behavior is right

Absent any GHG pricing mechanism — current or in the model's expectation —
the following is expected, as vessel-count market shares at every time step
(a short-term over-uptake would already threaten model stability):

- Oil and LNG are the cheapest fuels, so every vessel operates on them and
  oil and methane vessels dominate the fleet.
- A methanol dual-fuel vessel costs only marginally more than an oil vessel,
  but here it would operate fully on oil, so nothing repays the premium:
  at most 10% of the fleet.
- An ammonia vessel costs significantly more and would likewise run on oil:
  at most 5% of the fleet.

The same reasoning bounds the efficiency levers — nothing new incentivizes
energy-saving effort over the horizon, so at every step:

- each global energy-saving series stays within ±5 percentage points of its
  initial value;
- fleet-wide uptake of each technology stays within ±10 pp of its initial
  value;
- operational speed stays within ±10% (relative) of its initial value.

The saving and uptake bands are percentage points (absolute) because
operational saving starts at exactly 0, where a relative band is undefined;
speed has a physical unit and no natural absolute scale, hence relative.

The share ceilings and the saving and uptake drift bands are known to fail
against current model behavior (2026-08-14) — open findings for the model,
not thresholds to tune away.

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
  (`TechnologyCostOfCapital = 0.08`, the reference manual's example value),
  because the installation defaults leave it unset and the model's fallback
  to vessel cost of capital warns that it inflates uptake.

## Qualitative expectations (tier 3, prose only)

Oil's share should erode slowly, if at all, over the horizon; there is no
mechanism that should produce a sharp mid-horizon transition in this deck.

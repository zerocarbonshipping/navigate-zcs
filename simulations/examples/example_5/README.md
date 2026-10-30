<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Example 5: Caribbean regional shipping and global and EU policy

This example asks how the Caribbean's own fleet is affected by a global fuel
standard (the IMO Net-Zero Framework), the EU ETS and FuelEU. It does not ask
what each policy does to the ships it covers.

> **Note on calibration.** The regional fleet is deliberately not calibrated to
> the region. In 2026 it burns 419 kt of fuel and emits 1.59 Mt CO2e
> well-to-wake; the IMO CARES study puts these ships at 309 kt and about
> 1.0 Mt CO2e, so the model is about 36 % too high on fuel. Each library ship
> class is a world average, and Caribbean ships are smaller (most CARES tugs are
> 250 - 300 GT). Read the results as differences between the decks, not as the
> region's real totals.

## The case

- **Regional fleet (`reg_*`):** 330 domestic and intra-Caribbean ships. Nearly
  all are under 5,000 GT, so none of the three policies covers them today.
  - 144 tugs and 47 ferries;
  - 139 other ships, split here into 85 general cargo ships and 54 small tankers.
- **International fleet (`intl_*`):** 40 container feeders of about 1,500 TEU on
  a Miami - Jamaica - Trinidad - Martinique loop. All three policies cover them.
- **Ports:**
  - Jamaica, for Kingston;
  - Trinidad, for Port of Spain and Point Lisas;
  - Martinique, for Fort-de-France. It is an EU outermost region, so it is the
    EU's jurisdiction in this example;
  - Miami.
- **New fuels:**
  - Blue ammonia, e-ammonia and e-methanol, made in Trinidad or on the US Gulf
    Coast and shipped in;
  - e-ammonia and e-methanol from Chile's Magallanes region: cheaper wind, but
    4,700 - 5,250 nm away through the Panama Canal;
  - bio-methanol from the US Gulf Coast.

  All four can be bunkered at the three Caribbean ports. Fossil fuel oil can be
  bunkered everywhere, and LNG only at Jamaica and Miami.

## The three decks

| Deck | Policies | Who they cover |
|---|---|---|
| `example_5_no_policy.nav` | none | nobody |
| `example_5_current_rules.nav` | global fuel standard (two tiers), EU ETS, FuelEU | international ships only, as today |
| `example_5_extended.nav` | the same | the regional ships too |

The extended deck stands for a region adopting the standard for its own ships,
or for the EU ETS review (COM(2026) 616), which brings ships of 400 - 5,000 GT
in.

To run one deck: `python -m navigate simulations/examples/example_5/example_5_current_rules.nav -d ./assumptions -s`

To run all three and compare them (about 5 minutes):
`python simulations/examples/example_5/compare.py`

To explore them, open `explore.ipynb`. It runs the three decks and has a
switches cell for the levers. Among them is the global fuel standard, which
can be rewritten there:
- who it covers;
- when it starts;
- both targets, by year, including points after 2035;
- both tier prices.

Its defaults are the MEPC 83 draft.

The map at the top of the notebook is drawn by `figures/make_case_map.py`, with
the workshop's map helpers. It writes `figures/case_map.svg` and `.png` and puts
the PNG in the notebook's first cell, so it shows on Colab without running
anything. Run it again after any change to the ports, routes or production sites.

## Results (23 October 2026, with Gulf Coast and Chilean supply)

**Regional fleet**

| Deck | Oil share 2050 | WTW 2050 (Mt CO2e) | Cumulative WTW 2026-2050 (Mt) | Fuel and policy cost 2026-2050 (bn USD) |
|---|---|---|---|---|
| No policy | 80 % | 2.12 | 48.0 | 6.0 |
| Current rules | 80 % | 2.12 | 48.0 | 6.0 |
| Extended | 62 % | 1.48 | 40.1 | 12.8 |

**International feeders**

| Deck | Oil share 2050 | WTW 2050 (Mt CO2e) | Cumulative WTW 2026-2050 (Mt) | Fuel and policy cost 2026-2050 (bn USD) |
|---|---|---|---|---|
| No policy | 73 % | 1.12 | 22.0 | 2.7 |
| Current rules | 55 % | 0.66 | 15.1 | 4.7 |
| Extended | 40 % | 0.53 | 14.5 | 4.4 |

What the runs show:
- **Today's rules leave the regional fleet exactly where it was without policy.**
  This is the main finding, but it is also a limit of the model:
  - Navigate prices a new fuel at its production and delivery cost. Demand from
    the feeders does not raise its price, so nothing reaches the regional ships
    through the fuel market.
  - The real spill-overs are not modelled: higher freight rates, bunker
    suppliers' margins, and port infrastructure that the feeders' demand pays
    for.
- **Extending the rules cuts the regional fleet's cumulative emissions by 16 %,
  and its 2050 emissions by 29 %. It also more than doubles its fuel and policy
  bill.** Much of the extra cost is remedial payments: at 380 USD/t, paying is
  cheaper than switching for many ships.
- **Extending the rules also helps the international ships.** Producers build
  more plants for the larger demand: blue ammonia in 2050 is 6.5 PJ rather than
  2.2 PJ. The feeders' ammonia share in 2050 rises from 24 % to 42 %.

### Fuel from far away but cheap: Chile

Extended deck, e-ammonia delivered to the three ports, average 2040 - 2050:

| Production sites | e-ammonia delivered (USD/t) | Regional WTW 2026-2050 (Mt) | Regional bill (bn USD) |
|---|---|---|---|
| Trinidad and Gulf Coast | about 860 | 40.3 | 12.8 |
| all three | about 840 | 40.1 | 12.8 |
| Chile only | about 785 | 40.6 | 13.1 |

- **Chile's e-ammonia is the cheapest delivered.** Its cheaper wind saves more
  than the roughly 100 USD/t it costs to ship 5,000 nm at the invented rate.
- **It changes little with all three sites on.** Each port sells a fuel at the
  supply-weighted average of the plants serving it, and Chile builds no more
  than the others (the planning bug below).
- **"Chile only" is not better overall.** It removes blue ammonia and
  bio-methanol, which only Trinidad and the Gulf Coast make.

## Sources

| Input | Value | Source |
|---|---|---|
| Regional fleet | 330 ships over 100 GT: 144 tugs, 47 ferries | IMO CARES (2024, released Feb 2025), *Report on Decarbonization of Domestic Shipping: Insights from Africa and the Caribbean*, p.19 |
| Regional fuel use (check, not input) | 309 kt/yr, 1.0 Mt CO2e/yr | IMO CARES, §5.2 p.33 |
| No alternative fuels in the fleet today | 0 of 649 African and Caribbean domestic ships | IMO CARES |
| Size of domestic ships | mostly under 100 m and under 5,000 GT | IMO CARES |
| Feeder sizes | 500 - 2,500 TEU | MundoMaritimo, 2025-26 (Caribbean Feeder Services, Seaboard) |
| Port weights for tugs | Kingston 2.66 M, Port of Spain + Point Lisas 0.57 M, Fort-de-France 0.19 M TEU (2025) | R.J. Sánchez, PortEconomics, 2 Oct 2026 |
| Fossil fuel price | library global price, 485 USD/t | Balboa VLSFO 2025 average 511 USD/t, about Singapore's level (Ship & Bunker) |
| LNG at Jamaica | regasification terminal, 0.4 Bcf/d | US EIA |
| Trinidad grid | 62 USD/MWh, 0.682 t CO2e/MWh | GlobalPetrolPrices (Jun 2025); Ember via Our World in Data (2024) |
| Trinidad industry | about 5 Mt/yr ammonia and 6 Mt/yr methanol capacity, grey | The Energy Year (2024) |
| Global fuel standard | reference 93.3 gCO2e/MJ; direct compliance target -17 / -21 / -43 % (2028 / 2030 / 2035) at 100 USD/t; base target -4 / -8 / -30 % at 380 USD/t | IMO Net-Zero Framework, approved in draft at MEPC 83 (April 2025); [King & Spalding summary](https://www.kslaw.com/insights/articles/imos-net-zero-framework-and-the-global-carbon-price-on-shipping) |
| Scope of the standard | ships of 5,000 GT and above, international voyages | IMO Net-Zero Framework FAQ |
| EU ETS and FuelEU | the library's own regulations, Martinique as the EU port | `assumptions/`; outermost-region rules from the EU ETS FAQ and Lloyd's Register |
| Ship designs, costs, ages, trade growth, engine availability dates | library values for each class | `assumptions/` |

## Invented values

Each one is marked `INVENTED` in its file.

- **Regional fleet split:** the 139 "other" ships as 85 general cargo ships and
  54 small tankers. The CARES chart could not be read.
- **Feeder fleet:** 40 ships.
- **Distances:** great-circle plus 10 %. Miami - Kingston is set at 700 nm.
- **Tug work:** spread over the ports by container throughput.
- **Ferry work:** split half Trinidad, half Martinique.
- **Speeds:** 10.5 knots for the tankers and 13 knots for the feeders, the
  middle of the library's range for each.
- **Tanker loading:** full out of Trinidad, half after Martinique.
- **Caribbean renewable electricity:** the library's Americas cost as a proxy.
  The only Caribbean figure found, Jamaica's solar at about 85 USD/MWh, dates
  from 2016-17.
- **Trinidad grid:** price and intensity held flat to 2050.
- **Fuel supply:**
  - Trinidad's gas at the library's global price;
  - the second production site on the US Gulf Coast, with its distances to
    the ports (1,300 - 2,100 nm);
  - Chile's wind priced at the library's Americas low case (49 USD/MWh in
    2026, 33 by 2050), as a proxy: the library has no Chile-specific cost;
  - all three sites drawing on the same share of plant-building capacity.
- **LNG bunkering:** only at Jamaica and Miami.
- **Miami:** sells fossil fuels only.
- **Delivery cost:** 0.02 USD per ton per nautical mile.
- **Region's share of plant building:** 2 % of shipping's.
- **Region's share of feedstock:** 0.2 % of shipping's.
- **Global fuel standard:**
  - prices held flat after 2030, and targets held flat after 2035;
  - surplus units pool freely;
  - the standard starts in 2028, although it is not adopted.

## Known limits

- **Where a fuel is made is not decided by cost.** Navigate sizes each site on
  the whole gap for that fuel, so every site builds about the same amount of
  each fuel, Chile's cheaper power included. This is the producer-planning bug recorded
  in `simulations/user/producer_planning_bugs/`. Imports versus local production
  can be compared only by switching sites off (`FUEL_SITES` in the notebook).
  Distances from Chile are measured along a sea route through Panama; canal
  tolls are not counted.

- **Calibration:** not calibrated, on purpose; see the note at the top.
- **Outermost-region exemptions:** the extended deck covers the regional ships
  at once. It ignores these exemptions, which run until 2030 for the EU ETS
  and 2029 for FuelEU.
- **Shore power:** left out. On `main` its limits do not constrain the result.
- **Status of the standard:** not adopted. The IMO's extraordinary session
  resumes on 4 December 2026.

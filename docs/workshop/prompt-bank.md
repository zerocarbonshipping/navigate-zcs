<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Prompt bank

Each entry is a full prompt for one kind of study, tested by handing it to an AI
assistant with no other instructions and checking the deck it built. Pick the
entry closest to your case, change what differs, and give it to your assistant.
The rules every deck shares are in [Building a deck with an AI
assistant](building-a-deck.md); the prompts here only describe their case.

[Session 5](05-build-your-own-case.ipynb) has four more: one trade between two
ports, two fleets in one market, the world fleet cut down, and the cost of
delaying a global fuel standard.

## What "it works" means here

A deck that runs is not yet a deck that answers the question. An entry is marked
as tested only when a cold build passed all of these:

- **It runs**: exit code 0, no errors, and only the warnings
  `building-a-deck.md` lists as coming with the library.
- **Every number is traceable**: it comes from `assumptions/` by name, or it is
  marked INVENTED where it appears and listed in the `.nav` header.
- **The first year is plausible**: an oil fleet's well-to-wake intensity is close
  to 92 gCO2e/MJ, and the energy consumed matches the size of the fleet.
- **The answer moves the right way**: where the case compares runs, the one with
  the stronger push away from fossil fuels does not burn more of them.
- **The question is one Navigate can answer**: see the limits below.

## What the library does not cover

Cases outside these limits can still be built, but their numbers are INVENTED
and the entry says so up front:

- **Vessels**: only seagoing classes. There is no inland vessel and no
  battery-electric or hydrogen fuel-cell power system.
- **Fuels**: no HVO. Biodiesel (FAME) and e-diesel stand in for drop-in fuels.
- **Policy**: EU ETS, FuelEU Maritime and CII only. National measures are built
  as a `Levy` with INVENTED values.
- **Geography**: no distances, port handling costs or bunker transport costs.

## Entries

### Inland waterways in Germany: what a national CO2 price does

**The study.** Dry-cargo motor vessels on the Rhine between Duisburg and
Mannheim, 2026 to 2050, run twice: without policy, and with a CO2 price on the
fossil fuel they burn, standing for Germany's national CO2 price. The price is a
copy of the library's EU ETS regulation moved to the two German ports, so only
its price path is invented. The question
is whether that price moves the owners to drop-in fuels (biodiesel, e-diesel) in
the ships they have, or to new engines.

**What comes from the library.** The engines, tanks and fuel options of the
library's general cargo ships, the fuels and their prices, and the European fuel
production.

**What is INVENTED.** The library has no inland vessel, so the ship is a library
general cargo ship resized for the Rhine: its capacity, power, propulsion curve,
price and lifetime are placeholders. The route, fleet size, bunker logistics and
the CO2 price path are invented too. Replace the placeholders with sourced data
before quoting any result.

**Limits.** Navigate has no river current, locks or low-water periods, and no
battery-electric ship, which is one of the options German inland operators are
actually weighing.

**Tested:** 2026-10-16. The final prompt passed every check above on the first
attempt, built cold and also through Session 5's start-up prompt from a different
inland case (container barges from Duisburg to Frankfurt). Three earlier rounds
found the traps now written in `building-a-deck.md`. Both builds found that at 65
to 150 USD/t the owners pay the price rather than switch fuel, and order a few
more LNG ships; the drop-in fuels need roughly 440 USD/t (biodiesel) to 800-1,100
USD/t (e-diesel). Treat that as a property of the placeholders, not of the Rhine.

````text
You are helping me build a simulation study for Navigate, the shipping
decarbonisation model in this repository. Write the files yourself; do not only
describe them.

Before writing anything, read docs/workshop/building-a-deck.md and follow it. It
says how Navigate works, how to run a deck and read its results, and the rules
every deck follows. This prompt gives the case.

THE DECKS
A new folder, simulations/user/rhine_inland/, holding two decks that differ in
one Include line only:
- reference.nav: no policy at all
- co2_price.nav: the same, plus includes/co2_price.inc

THE CASE
Inland dry-cargo shipping on the Rhine within Germany, 2026 to 2050, yearly steps.
- Fleet: large Rhine motor cargo vessels, all on fuel oil at the start. The
  owners can keep their ships, burn a drop-in fuel in them, or order ships with
  LNG or methanol engines. No ammonia ships: they are not realistic on inland
  waterways.
- Trade: Duisburg to Mannheim, laden upstream, back in ballast.
- Fuels: fuel oil and LNG at their library prices, biodiesel (FAME) and e-diesel,
  which burn in the oil engines, and e-methanol, all made in Europe.
- Policy: none in reference.nav. EU ETS and FuelEU Maritime do not cover inland
  waterways, so do not load DefaultRegulation in either deck. co2_price.nav adds
  Germany's national CO2 price as a copy of the library's EU ETS regulation:
  Copy Regulation "eu_ets" to "co2_price_germany", with its Jurisdiction set to
  the two ports and its RemedialCost set to the CO2 price below. Keep the rest of
  it: it already counts biofuels and e-fuels as zero CO2. It names fuels this case
  does not use (bio-methanol, bio-methane, e-methane, blue and e-ammonia), so
  import those too, in both decks, or it will not parse. building-a-deck.md says
  why this is a Regulation and not a Levy.

HOW TO BUILD IT
The library has no inland vessel. Build the ships from the library's general
cargo vessels (general_cargo_ice_oil, _ice_methane, _ice_methanol) with Copy
Vessel, and resize them for the Rhine with the placeholder values below. A
vessel's engine power sits in its Converter nodes, which its PowerSystem names,
so give each copied vessel its own copies of those, with the new power. Keep the
library's tanks, fuel options and machinery costs, and say in the .nav header
that the fuel-system and tank costs are a seagoing ship's. Ships cannot be
converted to another fuel: leave the library's set_fuel_conversion_cost out. Set
AllowSpeedManagement = FALSE: on a river the waterway sets the speed, and with it
on the ships drift faster than the speeds below.

Build the rest as building-a-deck.md describes for a deck on named ports: the
Fleet node, a ROUND_TRIP route between your own ports duisburg and mannheim, the
bunker logistics, the European production region and the producers. For the
producers, use the library's plants for FAME, e-diesel and e-methanol in Europe,
with the shares of the library's feedstock ceilings given below.

NUMBERS
Everything not listed here comes from the library, by name. These are
placeholders, INVENTED for this case: mark each one where it appears, list them
all in both .nav headers, and keep them in one file, includes/placeholders.inc,
as Variables, Curves and Forecasts, so a user can replace them in one place. The
route distance and the bunker logistics take plain numbers only: write those in
their own files, marked INVENTED, and list them in placeholders.inc as comments.
- Fleet: 300 ships in 2026, aged evenly from 0 to 39 years, so about one in
  forty retires each year
- Ship: 3,000 t capacity, 40-year lifetime, 6 M USD newbuild price for the hull,
  1.5 MW propulsion power
- Propulsion power at speed, MW: 4 kn 0.25, 6 kn 0.6, 8 kn 1.1, 9 kn 1.45
- Auxiliary power: 0.1 MW at sea and 0.05 MW in port, with 0.2 MW generators
  (the library's are a seagoing ship's)
- Route: 190 nm each way; 7 kn laden upstream, 8 kn in ballast downstream (speed
  through the water; Navigate has no river current); one day in port per call
- Feedstock: this fleet's share of the library's shipping share, 0.02 of the
  used cooking oil and 0.02 of the biogenic CO2
- Bunker logistics: 400 nm from the European plants to each port, 0.03 USD per
  ton per nm
- CO2 price: 65 USD per t CO2 in 2026, rising linearly to 150 USD in 2050

BEFORE YOU TELL ME IT WORKS
Run both decks one after the other and report on each as building-a-deck.md
says. Then, from the two reports, give me side by side:
- the share of energy by fuel in 2026, 2035 and 2050;
- the fleet's well-to-wake emissions in 2026 and 2050, and summed over 2026-2050;
- the ships of each kind in 2050, and what the CO2 price cost the owners
  (RegulationExpenses).
Say plainly what the CO2 price changed: more drop-in fuel in the same ships, new
engines, both, or nothing. If the drop-in fuels never compete, work out from the
bunker prices roughly what CO2 price they would need. Remind me which inputs are
placeholders.
````

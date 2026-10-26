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
Every entry models a market segment owned by many companies, in hundreds of
ships or a share of a library class, never one company's fleet or a single ship.

[Session 5](05-build-your-own-case.ipynb) shows new users five examples, with
their prompts: Sessions 1 and 2 rebuilt, one trade between two ports, inland
shipping on the Rhine (its test notes are below) and two fleets in one market.
This bank is the larger set, not displayed on the site: it holds every tested
prompt, so that assistants can start from the closest one and the prompts can
be improved as more people build decks. The start-up prompt of Session 5 reads
the index below.

## Index

One line per prompt, Session 5's included. A new entry adds its line here.

| Entry | The question it answers | Scale | Ships | Policy | What the case changes | Tested |
|---|---|---|---|---|---|---|
| Session 5, example A: Rebuild Session 1's case | Which fuels do owners choose on one long trade under EU policy? | One long trade: Chile to Rotterdam | 300 Panamax bulk carriers | EU ETS and FuelEU on half the voyage | One run: the fuel choice under policy | 2026-10-19 |
| Session 5, example B: Rebuild Session 2's reference scenario | What does the world fleet burn to 2050 under a global fuel standard? | The world | The library's whole fleet | EU ETS, FuelEU, global fuel standard | One run: no comparison | 2026-10-19 |
| Session 5, example C: One trade, two ports | What does the model do on one trade when nothing pushes it? | One trade: Saudi Arabia to China | 200 Suezmax tankers | None | Nothing: the fuel choice on cost alone | 2026-10-26, through the start-up prompt |
| Inland waterways in Germany: what a national CO2 price does (prompt: Session 5, example D) | Does a national CO2 price move owners to drop-in fuels or new engines? | One river trade in Germany | 300 Rhine cargo vessels | National CO2 price (a copied EU ETS Regulation) | A price: with and without it | 2026-10-16 |
| Session 5, example E: Two fleets, one market | How much do the owners' efficiency choices matter on the same trade? | One trade of your choice | Two fleets of one class | Your choice | Technology: with and without it | ran first time; criteria not checked |
| EU short-sea feeders: what EU ETS and FuelEU make the owners do | How do owners comply with EU ETS and FuelEU, and at what cost? | One trade, both ports in the EU: Rotterdam to Gothenburg | 1,500 TEU feeders | EU ETS and FuelEU on the whole voyage | A policy: with and without it | 2026-10-19 |
| Green finance: do cheaper loans bring zero-emission ships forward? | Do cheaper loans bring zero-emission ships forward? | One trade: Tubarão to Rotterdam | Panamax ore carriers | EU ETS and FuelEU on half the voyage, in both runs | Finance: cheaper cost of capital for ammonia and methanol ships | 2026-10-19 |
| A global study: the cost of waiting | What does starting a global fuel standard late cost? | The world | The library's whole fleet | Global fuel standard, EU ETS, FuelEU | Timing: the standard on time vs delayed | 2026-10-26 |
| The world fleet, simplified: the global picture at a size you can iterate on | What does a cut-down world fleet do under EU policy? | The world, two or three classes | Library fleets | EU ETS and FuelEU | One run: no comparison | ran first time; criteria not checked |
| Coastal shipping in Norway: two ship classes under a national CO2 tax | Does a national CO2 tax move owners to biofuels or to new ships? | One coastal trade: Bergen to Tromsø | 100 general cargo ships and 50 ferries | National CO2 tax (a copied EU ETS Regulation) | A price: with and without it; two classes on one trade | 2026-10-26 |
| LNG carriers from Qatar to Japan: which fuel wins on cost alone | Which fuel wins on cost alone on a gas-carrier trade? | One trade: Ras Laffan to Futtsu | 100 gas carriers | None | Nothing: the fuel choice on cost alone | 2026-10-26 |

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
  with INVENTED values; a carbon price as a copy of the library's `eu_ets`
  Regulation (building-a-deck.md says why not a `Levy`).
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
2026-10-26, as the model a start-up prompt chose for a different case (Norwegian coastal cargo ships and ferries under Norway's CO2 tax): the chain built and ran cold with no warnings, and found the same: biofuels need roughly 440 USD/t, and the owners pay the tax, order a few more LNG ships and slow down.

**The prompt** is Session 5's example D, "Inland waterways in Germany", in
`docs/workshop/05-build-your-own-case.ipynb`.

### EU short-sea feeders: what EU ETS and FuelEU make the owners do

**The study.** Container feeder ships between Rotterdam and Gothenburg, 2026 to
2050, run twice: without policy, and under EU ETS and FuelEU Maritime at their
library settings. Both ports are in the EU, so both instruments cover the whole
voyage. The question is how the owners comply (which fuels, which ships) and
what compliance costs them.

**What comes from the library.** The ships (the 1,500 TEU class, with its age
profile, fuel designs, retrofit costs and operating profile), both regulations,
the fuels, their prices and the European fuel production.

**What is INVENTED.** The fleet size, the sea distance, the bunker logistics and
this trade's share of the library's feedstock ceilings.

**Limits.** FuelEU pooling between companies and the ETS's free allowances are
not in Navigate.

**Tested:** 2026-10-19. The final prompt passed every check above on the first
attempt, built cold and also through Session 5's start-up prompt from a different
case (Antwerp to Helsinki). One earlier round showed that a larger feedstock share
lets a small fleet live on Europe's biomass. Both builds found the owners mostly
pay until the mid-2030s, then comply through new methanol and ammonia ships:
well-to-wake emissions over 2026-2050 fall by 34 to 41 %, and e-fuels supply about
half the energy by 2050. Treat that as a property of the placeholders.

````text
You are helping me build a simulation study for Navigate, the shipping
decarbonisation model. Write the files yourself; do not only
describe them.

Before writing anything, find the Navigate repository on my machine (a folder
usually named navigate-zcs; ask me where it is if you cannot find it), then read
docs/workshop/building-a-deck.md in it and follow it. It
says how Navigate works, how to run a deck and read its results, and the rules
every deck follows. This prompt gives the case.

THE DECKS
A new folder, simulations/user/eu_feeder/, holding two decks that differ in one
Include line only:
- no_policy.nav: no regulation at all
- eu_policy.nav: the same, plus includes/eu_policy.inc

THE CASE
Container feeder ships on one route between Rotterdam (the Netherlands) and
Gothenburg (Sweden), 2026 to 2050, yearly steps.
- Fleet: the library's 1,500 TEU container class, with its own split of ship
  designs, age profile and fuel-conversion costs, built with Copy Vessel as
  building-a-deck.md describes. All four designs (oil, LNG, methanol, ammonia)
  can be ordered.
- Fuels: fuel oil and LNG at their library prices; biodiesel (FAME),
  bio-methanol, e-methanol and e-ammonia, all made in Europe.
- Policy: none in no_policy.nav. eu_policy.inc imports the library's EU ETS and
  FuelEU Maritime regulations (Import Regulation "eu_ets" and "fuel_eu"; do not
  copy example_4's own versions) and sets the Jurisdiction of both to the two
  ports. Both ports are in the EU, so both cover the whole voyage. Do not load
  DefaultRegulation: it also brings CII, which is not part of this study.

HOW TO BUILD IT
Build the rest as building-a-deck.md describes for a deck on named ports: a
ROUND_TRIP route between your own ports rotterdam and gothenburg with speeds and
time in port from the class's operational profile, the ports, the bunker
logistics, the European production region, the plants and the producers, with
the shares of the library's feedstock ceilings given below. Leave out the
library's orderbook for this class: it is sized for the world fleet.

NUMBERS
Everything not listed here comes from the library, by name. These are
placeholders, INVENTED for this case: mark each one where it appears, list them
all in both .nav headers, and keep them in includes/placeholders.inc (the plain
numbers in their own files, listed there as comments).
- Fleet: 80 ships in 2026, a segment owned by many companies
- Route: 520 nm each way
- Bunker logistics: 300 nm from the European plants to each port, 0.03 USD per
  ton per nm
- Feedstock: this trade's share of the library's shipping share, 0.001 of the
  used cooking oil, the biomass and the biogenic CO2 (about this fleet's share of
  world shipping's energy, as building-a-deck.md explains)

BEFORE YOU TELL ME IT WORKS
Run both decks one after the other and report on each as building-a-deck.md
says. Then, from the two reports, give me side by side:
- the share of energy by fuel in 2026, 2030, 2040 and 2050;
- the fleet's well-to-wake emissions in 2026 and 2050, and summed over 2026-2050;
- the ships of each design in 2050, and the fuel conversions over the period;
- what EU ETS and FuelEU cost the owners each (RegulationExpenses per
  regulation), in 2030 and 2050.
Say plainly how the owners comply: by switching fuel in the ships they have, by
new or converted ships, or mostly by paying. Remind me which inputs are
placeholders.
````

### Green finance: do cheaper loans bring zero-emission ships forward?

**The study.** Panamax bulk carriers carrying iron ore from Tubarão (Brazil) to
Rotterdam, 2026 to 2050, under EU ETS and FuelEU Maritime as the library sets
them. The voyage leaves the EU, so both cover half of it. Two runs: the library's
cost of capital, and a green-finance case where ammonia and methanol ships borrow
two percentage points cheaper. The question is whether cheaper finance alone
changes when, and how many, such ships are ordered.

**What comes from the library.** The ships (the 80,000 DWT class, with its age
profile, designs, retrofit costs and operating profile), both regulations, the
fuels and their prices, the cost of capital, and the fuel production in the
Americas.

**What is INVENTED.** The size of the green-finance discount, the fleet size,
the sea distance, the bunker logistics and this trade's share of the feedstock
ceilings.

**Limits.** Navigate prices finance through the cost of capital only: no
guarantees, grants or loan terms.

**Tested:** 2026-10-19. The final prompt passed every check above on the first
attempt, built cold and also through Session 5's start-up prompt from a different
case (US Gulf grain to Rotterdam, 1.5 points). Both builds found that cheaper
loans add a few ammonia and methanol ships (about 6 to 10 by 2050) but bring
nothing forward, and cut emissions by 1 to 2 %: the gap is the fuel's cost, not
the ship's finance. Treat that as a property of the placeholders.
2026-10-26, as the model a start-up prompt chose for a different case (Tubarão to Qingdao, no regulation): the chain built and ran cold with no warnings. Cheaper finance brought about 7 more ammonia and 7 more methanol ships by 2050, all burning pilot oil: without a policy, finance alone moves the orders, not the fuel.

````text
You are helping me build a simulation study for Navigate, the shipping
decarbonisation model. Write the files yourself; do not only
describe them.

Before writing anything, find the Navigate repository on my machine (a folder
usually named navigate-zcs; ask me where it is if you cannot find it), then read
docs/workshop/building-a-deck.md in it and follow it. It
says how Navigate works, how to run a deck and read its results, and the rules
every deck follows. This prompt gives the case.

THE DECKS
A new folder, simulations/user/green_finance/, holding two decks that differ in
one Include line only:
- reference.nav: the library's cost of capital for every ship
- green_finance.nav: the same, plus includes/green_finance.inc

THE CASE
Panamax bulk carriers (~80,000 DWT) carrying iron ore from Tubarão (Brazil) to
Rotterdam, laden out and back in ballast, 2026 to 2050, yearly steps.
- Fleet: the library's 80,000 DWT bulk carrier class, with its own split of ship
  designs, age profile and fuel-conversion costs, built with Copy Vessel as
  building-a-deck.md describes. All four designs (oil, LNG, methanol, ammonia)
  can be ordered.
- Fuels: fuel oil and LNG at their library prices; e-ammonia and e-methanol
  made in the Americas (the library's "americas" region).
- Policy, in both decks: the library's EU ETS and FuelEU Maritime (Import
  Regulation "eu_ets" and "fuel_eu"; do not copy example_4's own versions), with
  the Jurisdiction of both set to rotterdam only. The voyage leaves the EU, so
  each covers half of it. Do not load DefaultRegulation: it also brings CII,
  which is not part of this study.
- Green finance: green_finance.inc sets the CostOfCapital of the ammonia and
  methanol ships to their library value minus the discount below, as an
  expression of the library's Forecast or Variable and a placeholder Variable.
  Nothing else differs between the decks. Set the Fleet's
  TechnologyCostOfCapital = Variable("cost_of_capital_vessel") in both decks:
  without it, efficiency technology is financed at each ship's own rate, and the
  discount would reach it too.

HOW TO BUILD IT
Build the rest as building-a-deck.md describes for a deck on named ports: a
ROUND_TRIP route between your own ports tubarao and rotterdam with speeds and
time in port from the class's operational profile, the ports, the bunker
logistics, the americas production region, the plants and the producers, with
the shares of the library's feedstock ceilings given below. Leave out the
library's orderbook for this class: it is sized for the world fleet.

NUMBERS
Everything not listed here comes from the library, by name. These are
placeholders, INVENTED for this case: mark each one where it appears, list them
all in both .nav headers, and keep them in includes/placeholders.inc (the plain
numbers in their own files, listed there as comments).
- Green-finance discount: 0.02 (two percentage points) off the cost of capital
  of ammonia and methanol ships
- Fleet: 150 ships in 2026, a segment owned by many companies
- Route: 5,000 nm each way
- Bunker logistics: 500 nm from the plants to tubarao and 5,000 nm to rotterdam,
  0.02 USD per ton per nm
- Feedstock: this trade's share of the library's shipping share of biogenic CO2,
  0.002 (about this fleet's share of world shipping's energy, as
  building-a-deck.md explains)

BEFORE YOU TELL ME IT WORKS
Run both decks one after the other and report on each as building-a-deck.md
says. Then, from the two reports, give me side by side:
- the newbuilds of each design per year, and the ships of each design in 2035
  and 2050;
- the share of energy by fuel in 2026, 2035 and 2050;
- the fleet's well-to-wake emissions summed over 2026-2050;
- the investment freight rate of each design in 2030 and 2045.
Say plainly what the cheaper finance changed: earlier or more zero-emission
ships, a different fuel burnt, or nothing; and whether those ships actually
burn the fuel they were built for. Remind me which inputs are placeholders.
````

### A global study: the cost of waiting

**The study.** The mid-regulation reference scenario includes a global fuel standard (`gfs`): a well-to-wake intensity limit that every ship is held to worldwide, tightening from 2028 to 2050. What if it started five years late, but kept the same 2050 target? No deck to build from scratch here: the scenario is run twice, as it is and with every date before 2050 moved later, on the coarse time grid of [Session 2](https://colab.research.google.com/github/zerocarbonshipping/navigate-zcs/blob/workshop-colab/docs/workshop/02-run-a-global-case.ipynb) so each run takes a few minutes. The answer is one number worth remembering: the extra megatonnes of CO2e a delay costs, and whether the delayed run catches up by 2050. The change goes in a copy of the regulation file, so the reference scenario itself stays untouched.

**How it differs from the scenarios in the repository.** The four reference scenarios in `simulations/scenarios/` differ in *how strict* the regulation is: none at all, EU ETS and FuelEU only (business as usual), or those plus a global fuel standard that is moderate (mid) or strict (strong). Both standards start in 2028. This case keeps the mid scenario exactly as it is and changes only *when* its standard starts, which none of them explores. It also runs on the coarse grid, so compare its two runs with each other, not with the yearly results of Session 2.

![The global fuel standard's well-to-wake intensity limit from 2025 to 2050: the reference has its penalty from 2028, the delayed start from 2033, and both reach 28.0 gCO2eq/MJ in 2050](../_figures/gfs_delay_chart.png)

*The global fuel standard of the mid-regulation scenario (grey) and the same standard started five years later, with the same 2050 target (blue).*

**What comes from the library.** Everything: the decks are the Center's
mid-regulation reference scenario on the coarse grid of
`simulations/scenarios/workshop_whatif/`, one of them run as it is.

**What is INVENTED.** Nothing but the delay itself.

**Limits.** The coarse grid: compare the two runs with each other, not with
the yearly reference scenarios of Session 2.

**Tested:** 2026-10-06, as what was then Session 5's fourth example: built cold, it ran
without errors on the first attempt. 2026-10-26, built cold again with a five-year
delay and checked against the criteria above: both decks ran with only the
library's expected warnings, and the delay added about 1,560 Mt CO2e over
2026-2050 (+6 %), still 20 Mt a year more in 2050. The two decks share one
`plots/` folder, so compare them from their reports.

````text
You are helping me run a global study with Navigate, the shipping
decarbonisation model. Write the files yourself; do not only
describe them.

Before writing anything, find the Navigate repository on my machine (a folder
usually named navigate-zcs; ask me where it is if you cannot find it), then read
docs/workshop/building-a-deck.md in it and follow it. It
says how Navigate works, how to run a deck and read its results, and the rules
every deck follows. This prompt gives the case.

ABOUT THESE DECKS
- simulations/scenarios/ holds the Center's reference scenarios. The ones in
  simulations/scenarios/workshop_whatif/ are the no-, mid- and strong-regulation
  scenarios on a coarse time grid (2026, 2027, 2030, then every four years to
  2050), so that one run takes a few minutes instead of about twenty-five. This study uses the
  mid-regulation one.
- The reference decks load DefaultReport already, so every run writes the
  report. Its "Global" sheet has one row per time step.

THE STUDY
The mid-regulation reference scenario includes a global fuel standard ("gfs"):
a limit on the well-to-wake greenhouse-gas intensity of the energy every ship
uses, applied worldwide and tightening year on year. A ship above the limit pays
a penalty; a ship below it earns surplus units it can sell. It is defined in
simulations/scenarios/0_includes/mid_regulation.inc: the Regulation "gfs", the
limit as Forecast "gfs_target_reduction" (a fraction of 93.3 gCO2eq/MJ) and the
penalty as Forecast "gfs_remedial_unit" (USD per t CO2eq above the limit, from
2028).

I want to know what it costs to start the standard late but keep its 2050
target: [THE DELAY, e.g. "five years"].
In my own copy of that file, move every date of both Forecasts that falls
before 2050 by that many years (so the penalty starts in 2033 instead of 2028
for a five-year delay), and leave the 2050 rows where they are. Mark each moved
row with a comment giving its reference date. Nothing else changes.

THE DECKS
Work in a new folder, simulations/user/my_global_study/. Do not change the
reference scenario or its includes.
- reference.nav: a copy of
  simulations/scenarios/workshop_whatif/workshop_basecase_mid_regulation.nav,
  with its two Include paths rewritten so they still point at the original
  files from the new folder.
- delayed.nav: the same, except that it includes your own copy of
  mid_regulation.inc (as includes/gfs_delayed.inc in the new folder) with the
  dates moved as above.
Both decks must differ in that one include line only.

BEFORE YOU TELL ME IT WORKS
Run both decks (a few minutes each; run them one after the other, or in the
background, and wait for both), and report on each as building-a-deck.md says.
Then, from each report, give me side by side:
- the fleet's well-to-wake emissions at every time step (Mt CO2e per year);
- the emissions summed over 2026-2050, weighting each step by the years it
  stands for (say how you weighted them), and the difference: the extra Mt CO2e
  the delay costs;
- the share of the energy consumed in 2030, 2038 and 2050 by each fuel, and
  whether the delayed run catches up with the reference by 2050.
Say plainly that these are coarse-grid runs: compare them with each other, not
with the yearly reference scenarios.
````

### The world fleet, simplified: the global picture at a size you can iterate on

**The study.** No geography here: the Center's reference scenarios model twenty-three vessel classes on the library's own global operating profiles, and the only "places" are two abstract ports that exist so the EU measures know what they cover. This prompt keeps two or three classes of your choice, imported whole from the library with their own fleets, orderbooks and technologies, against the library's full fuel-supply chain in five regions and under EU ETS and FuelEU. Expect several minutes per run.

**What comes from the library.** Everything: the deck is almost entirely `Load`
statements, and each class is imported whole, with its own vessels, age
distribution, orderbook, technologies and retrofit costs.

**What is INVENTED.** Nothing. Which two or three classes to keep is the user's
choice.

**Limits.** Fewer fleets than the library's twenty-three (building-a-deck.md says
what that means for DefaultConverterAvailable), and EU ETS and FuelEU only: no
global fuel standard.

**Tested:** as Session 5's fourth example (added 2026-09-25): built cold, it ran
without errors on the first attempt. It has not yet been checked against the
criteria above the way the other entries were. Moved here from Session 5 on
2026-10-26.

````text
You are helping me build a simulation deck for Navigate, the shipping
decarbonisation model. Write the files yourself; do not only
describe them.

Before writing anything, find the Navigate repository on my machine (a folder
usually named navigate-zcs; ask me where it is if you cannot find it), then read
docs/workshop/building-a-deck.md in it and follow it. It
says how Navigate works, how to run a deck and read its results, and the rules
every deck follows. This prompt gives the case.

THE DECK
A new folder, simulations/user/[YOUR FOLDER NAME]/.

THE CASE
A cut-down version of the Center's reference scenarios. No route, no map, no real
ports - I want the global picture, not a trade.
simulations/scenarios/basecase_mid_regulation/ is the full reference scenario
this case cuts down.

- Fleets: [TWO OR THREE CLASSES, e.g. tanker_127k_dwt and bulk_carrier_80k_dwt],
  imported whole from the library (Import Fleet "..."), so each brings its own
  vessels, age distribution, orderbook, technologies and retrofit costs
- Geography: none of your own. Load DefaultVoyage for the per-class operating
  profiles and DefaultPort for the two abstract ports the library uses.
- Fuels and production: load the library's whole chain - DefaultEmission,
  DefaultFeedstock, DefaultFuel, DefaultProducer, DefaultPlant, DefaultRegion,
  DefaultSource, DefaultTransport
- Regulation: EU ETS and FuelEU at their library settings (DefaultRegulation)
- Also load what every library deck needs, as building-a-deck.md lists it.

NUMBERS
Everything comes from the library by construction here, because the deck is
almost entirely Load statements. If you find yourself writing a number, stop and
tell me why the library has none.

DECK RULES
This deck has fewer than the library's twenty-three fleets: follow what
building-a-deck.md says about DefaultConverterAvailable.

BEFORE YOU TELL ME IT WORKS
Expect a run of five to ten minutes, not seconds. Tell me the fuel mix at both
ends of the horizon, from the report.
````

### Coastal shipping in Norway: two ship classes under a national CO2 tax

**The study.** Coastal cargo ships and ferries between Bergen and Tromsø, 2026 to
2050, owned by many companies, run twice: without policy, and with Norway's CO2
tax on domestic shipping, built as a copy of the library's EU ETS regulation on
the two ports. The question is whether the tax moves the owners to biofuels in
the ships they have, or to new ships. It is the inland Germany entry with
seagoing library classes, and with two classes on one trade, each on its own
Route node.

**What comes from the library.** Both ship classes (general cargo and ferry: their
designs, age profiles, operating profiles and trade growth), the fuels and their
prices, the European fuel production, and the EU ETS regulation the tax copies.

**What is INVENTED.** The fleet size and its split (100 cargo ships, 50 ferries),
the sea distance, the bunker logistics, the feedstock share and the tax path
(100 USD/t CO2 in 2026, 200 from 2030).

**Limits.** The ships and their operating patterns are the library's world
averages for the class, not Norwegian coastal vessels. The library has no
battery-electric ships, which much of Norway's ferry fleet is moving to. Neither
class can be converted to another fuel in the library.

**Tested:** 2026-10-26. Written by Session 5's start-up prompt from a short case
(the model it chose was inland Germany), then built cold and unedited: both
decks ran with no warnings and passed the checks above. Biofuels need roughly
440 USD/t; at 200 USD/t the owners pay the tax, order slightly more LNG ships,
and the cargo ships slow down, which gives most of the 4.5 % cut in emissions.
Treat that as a property of the placeholders.

````text
You are helping me build a simulation study for Navigate, the shipping
decarbonisation model. Write the files yourself; do not only
describe them.

Before writing anything, find the Navigate repository on my machine (a folder
usually named navigate-zcs; ask me where it is if you cannot find it), then read
docs/workshop/building-a-deck.md in it and follow it. It
says how Navigate works, how to run a deck and read its results, and the rules
every deck follows. This prompt gives the case.

THE DECKS
A new folder, simulations/user/norway_coastal/ (if it is taken, use
norway_coastal_2, and so on, and tell me which). Do not change any existing file.
It holds two decks that differ in one Include line only:
- reference.nav: no policy at all
- co2_tax.nav: the same, plus includes/co2_tax.inc
(Two decks, so these two names replace building-a-deck.md's rule of naming the
.nav after the folder.)

THE CASE
Norwegian coastal shipping between Bergen and Tromsø, 2026 to 2050, yearly steps.
The question is whether Norway's CO2 tax on domestic shipping moves the owners to
biofuels in the ships they have, or to new ships.
- Fleets: two Fleet nodes, both owned by many companies, both nearly all on fuel
  oil at the start:
  - coastal cargo ships: the library's general cargo class (Fleet file
    general_cargo.inc), with its own split of ship designs and age profile;
  - ferries: the library's ferry class (Fleet file ferry.inc), with its own split
    of ship designs and age profile.
  Build both with Copy Vessel, as building-a-deck.md describes. The designs that
  can be ordered are oil, LNG and methanol, for both classes. Leave out the
  general cargo ammonia design to keep the deck small (and its InitialSplit and
  age-distribution entries with it; its initial share is 0 in the library). The
  library's Fleet files for these two classes have no set_fuel_conversion_cost
  lines, so no ship can be converted to another fuel: say so in the .nav header
  rather than inventing conversion costs. Keep each class's library TradeGrowth,
  and its AllowSpeedManagement as the library sets it (FALSE for ferries, TRUE
  for general cargo); check ActualSpeed as building-a-deck.md says.
- Trade: one ROUND_TRIP between your own ports bergen and tromso, cargo carried
  both ways. Each class sails it on its own Route node (the two classes have
  different speeds and port times), with the same ports and distances.
- Fuels: fuel oil and LNG at their library prices; biodiesel (FAME), which burns
  in the oil engines; bio-methane, which burns in the LNG engines; bio-methanol
  and e-methanol, which burn in the methanol engines. All the alternative fuels
  are made in Europe (the library's "europe" region).
- Policy: none in reference.nav. EU ETS and FuelEU Maritime are not part of this
  study: do not load DefaultRegulation in either deck. co2_tax.nav adds Norway's
  CO2 tax on domestic shipping as a copy of the library's EU ETS regulation:
  Copy Regulation "eu_ets" to "co2_tax_norway", with its Jurisdiction set to the
  two ports (so it covers the whole voyage) and its RemedialCost set to the tax
  path below. Keep the rest of it: it already counts biofuels and e-fuels as zero
  CO2. It names fuels this case does not otherwise use (e-diesel, e-methane,
  blue and e-ammonia), so import those too, in both decks, or it will not parse.
  building-a-deck.md says why this is a Regulation and not a Levy. The price
  Forecast and the Regulation need different names.

HOW TO BUILD IT
Build the rest as building-a-deck.md describes for a deck on named ports: the
two Fleet nodes, the two ROUND_TRIP routes with speeds and time in port from
each class's operational profile, the ports, the bunker logistics, the European
production region and the plants and producers, with the shares of the library's
feedstock ceilings given below. Leave out the library's orderbooks for both
classes: they are sized for the world fleet.

From the operational profiles (copy these with a comment naming the file, and
show the arithmetic as example_4's route.inc does):
- operational_profile_ferry.inc: 14 kn, capacity utilisation 0.75 on both legs,
  TimeAtSea 0.5 over 50 port calls a year, so 0.5 x 365 / 50 = 3.65 days per call;
- operational_profile_general_cargo.inc: 11.2 kn, capacity utilisation 0.5 on
  both legs, TimeAtSea 0.548 over 20 port calls a year, so
  0.452 x 365 / 20 = 8.25 days per call.
Say in a comment that these are world-average patterns for the class, not
Norwegian coastal service.

For the producers, use the library's European plants for FAME, bio-methane,
bio-methanol and e-methanol, and set Region, Source and CostOfCapital on every
plant as building-a-deck.md says.

NUMBERS
Everything not listed here comes from the library, by name. These are
placeholders, INVENTED for this case: mark each one where it appears, list them
all in both .nav headers, and keep them in one file, includes/placeholders.inc,
as Variables and Forecasts, so I can replace them in one place. The route
distance and the bunker logistics take plain numbers only: write those in their
own files, marked INVENTED, and list them in placeholders.inc as comments.
- Fleet: 150 ships in 2026, a segment owned by many companies: 100 general cargo
  ships and 50 ferries
- Route: 650 nm each way between Bergen and Tromsø
- Bunker logistics: 300 nm from the European plants to bergen and 800 nm to
  tromso, 0.03 USD per ton per nm
- Feedstock: this trade's share of the library's shipping share, 0.0004 of the
  used cooking oil, the biogas, the gasifiable biomass and the biogenic CO2
  (about this fleet's share of world shipping's energy, as building-a-deck.md
  explains; check it against the fleet's first-year energy in the report and
  tell me if it is off by more than a factor of two, but do not change it)
- CO2 tax: 100 USD per t CO2 in 2026, rising linearly to 200 USD in 2030, then
  flat at 200 USD to 2050

RESULTS PER FLEET
DefaultReport gives totals for both fleets together. Add your own Report node,
as building-a-deck.md describes, with per fleet ConsumedEnergy by fuel,
ExistingVessels per vessel, TotalEquivalentWTW and RegulationExpenses; and, in
co2_tax.inc, the tax's own RemedialExpenses, FlexibilityExpenses and
SurplusRevenue.

BEFORE YOU TELL ME IT WORKS
Run both decks one after the other and report on each as building-a-deck.md
says. Then, from the two reports, give me side by side, for each fleet and for
both together:
- the share of energy by fuel in 2026, 2030, 2040 and 2050;
- the well-to-wake emissions in 2026 and 2050, and summed over 2026-2050;
- the ships of each design in 2050 (oil, LNG, methanol), and the newbuilds of
  each design over the period;
- what the CO2 tax cost the owners in 2030 and 2050.
Say plainly what the tax changed: biofuel burnt in the ships the owners already
have (FAME in oil ships, bio-methane in LNG ships), new LNG or methanol ships,
both, or nothing; and whether new methanol ships actually burn methanol rather
than their pilot oil. If the biofuels never compete, work out from the bunker
prices roughly what CO2 price they would need. Remind me which inputs are
placeholders, and that the ships are the library's world-average general cargo
ship and ferry, not Norwegian coastal vessels.
````

### LNG carriers from Qatar to Japan: which fuel wins on cost alone

**The study.** LNG carriers from Ras Laffan to Futtsu (Tokyo Bay), 2026 to 2050,
owned by many companies, with no regulation: every fuel choice is made on cost
alone, with fuels made in the Middle East. The question is which fuel wins by
2050. It is the "one trade, two ports" example (Session 5, example C) for a gas
carrier, whose fleet already burns LNG at the start.

**What comes from the library.** The gas-carrier class (its four designs, age
profile and operating profile), the fuels and their prices, and the Middle East
fuel production.

**What is INVENTED.** The fleet size, the sea distance, the bunker logistics and
the feedstock share.

**Limits.** The library's gas carrier is a 100,000 m3 ship, not a 174,000 m3 LNG
carrier, and Navigate has no boil-off gas: the ships buy LNG at the port like any
fuel. The class cannot be converted to another fuel in the library.

**Tested:** 2026-10-26. Written by Session 5's start-up prompt from a short case
(the model it chose was Session 5's example C), then built cold and unedited: it
ran with no warnings and passed the checks above. Nothing switched: the cheapest
alternative, blue ammonia, costs about 2.6 times LNG in 2050. Methanol and
ammonia ships are still ordered, and burn only their pilot oil, so the oil share
of energy rises; read the switch from ConsumedEnergy, not from ship counts.

````text
You are helping me build a simulation deck for Navigate, the shipping
decarbonisation model. Write the files yourself; do not only
describe them.

Before writing anything, find the Navigate repository on my machine (a folder
usually named navigate-zcs; ask me where it is if you cannot find it), then read
docs/workshop/building-a-deck.md in it and follow it. It
says how Navigate works, how to run a deck and read its results, and the rules
every deck follows. This prompt gives the case.

THE DECK
A new folder, simulations/user/gulf_japan_lng/ (if it is taken, use
gulf_japan_lng_2, and so on), with the .nav
file named after the folder and its .inc files in includes/. Do not change any
existing file.

THE CASE
LNG carriers on one trade, 2026 to 2050, yearly steps, no regulation at all:
every fuel choice is made on cost alone. The question: which fuel wins on cost
by 2050?
- Fleet: the library's gas carrier class, gas_carrier_100k_cbm, with its four
  designs (oil, LNG, methanol, ammonia), built with Copy Vessel as
  building-a-deck.md describes. Keep the library's ship as it is (capacity,
  power, price, lifetime); do not resize it to a 174,000 m3 LNG carrier.
  All four designs can be ordered.
- Starting fleet: 100 ships in 2026, a segment owned by many companies, with the
  library's InitialSplit and InitialAgeDistribution for this class (about two
  thirds LNG-fuelled, one third oil). Leave out the library's orderbook: it is
  sized for the world fleet.
- Trade: Ras Laffan (Qatar) to Futtsu (Tokyo Bay, Japan), laden out, ballast
  home.
- Fuels: fuel oil and LNG at their library prices, as global commodities
  (LiquidMarketFuels); bio-methane, e-methane, blue ammonia, e-ammonia and
  e-methanol made in the Middle East (the library's "middle_east" region), with
  the library's middle_east plants.
- Regulation: none. Do not load DefaultRegulation and write no Regulation or
  Levy. That is the point of the case.

HOW TO BUILD IT
- A trade of its own between two named ports: build the Fleet node with Copy
  Vessel, a ROUND_TRIP route between your own ports ras_laffan and futtsu, the
  ports, the bunker logistics, the middle_east region and the producers as
  building-a-deck.md describes, with this case's own values. Restate in your
  own region file the Region "*" lines (feedstock and process costs) that your
  plants use, from assumptions/modules/installation/default_region.inc.
- Route: the class's operational profile
  (assumptions/defaults/installation/Route/operational_profile_gas_carrier_100k_cbm.inc)
  has one speed, 16.6 kn, so use it both ways; CapacityUtilizations 1.0 laden
  out and 0.0 in ballast home. Port days per call from the profile: TimeAtSea
  0.684 over 24 + 6 = 30 calls a year, (1 - 0.684) x 365 / 30 = 3.8 days; show
  the arithmetic in a comment.
- Retrofits: the library's Fleet file for this class has no
  set_fuel_conversion_cost lines, so the ships cannot be converted; say so in
  the .nav header rather than inventing conversion costs.
- Plants: set Region, Source and CostOfCapital on every plant yourself, as
  default_plant.inc does for middle_east (Source "grid" for bio and blue,
  "renewable" for electro; cost_of_capital_plant_bio/blue/electro_middle_east).
- Energy-efficiency technologies are optional here: leave them out.
- Do not load DefaultConverterAvailable (fewer than the library's 23 fleets):
  say in the .nav header that every design is orderable from year one.
- Add Load DefaultReport, and a Report of your own with
  add_plant_property("*", InvestmentIntensityCost), so we can see how far the
  fuels that are not built are from competing.

NUMBERS
The library covers this vessel class - use its own values, by name:
    assumptions/defaults/installation/Fleet/gas_carrier_100k_cbm.inc
    assumptions/defaults/installation/Route/operational_profile_gas_carrier_100k_cbm.inc
Take structure from simulations/examples/example_4/ and none of its numbers.
These are placeholders, INVENTED for this case: mark each one where it appears,
list them all in the .nav header, and keep them in includes/placeholders.inc
(the plain numbers in their own files, listed there as comments).
- Fleet: 100 ships in 2026 (INVENTED: about 4 % of the library's 2,553 gas
  carriers; the number is mine, the library's is the whole world fleet)
- Route: 6,500 nm each way, Ras Laffan to Futtsu via the Strait of Malacca
- Bunker logistics: 200 nm from the Middle East plants to ras_laffan and
  6,500 nm to futtsu, 0.02 USD per ton per nm
- Feedstock: this trade's share of the library's shipping share, 0.006 of the
  biogenic CO2 (e-methanol, e-methane) and of the biogas feedstock
  (bio-methane): about this fleet's share of world shipping's energy, as
  building-a-deck.md explains. Check it against the first-year energy in the
  report and tell me if it is off by more than a factor of two; do not change
  it to make a fuel appear.

BEFORE YOU TELL ME IT WORKS
Run it and report as building-a-deck.md says. Then, from the report, give me:
- the share of energy by fuel in 2026, 2030, 2040 and 2050;
- the ships of each design in 2050, and the newbuilds of each design over the
  period;
- the fleet's well-to-wake emissions in 2026 and 2050;
- for the alternative fuels not burnt, their levelised cost per GJ in 2050
  (InvestmentIntensityCost) next to the bunker price of LNG.
Say plainly which fuel wins on cost by 2050, and whether anything actually
switched (judge it from ConsumedEnergy, not ship counts). Remind me which
inputs are placeholders.
````

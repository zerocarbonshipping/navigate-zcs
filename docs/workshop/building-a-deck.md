<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Building a deck with an AI assistant

This page is written for the AI assistant that builds a Navigate deck from one of
the prompts of [Session 5](05-build-your-own-case.ipynb) or of the prompt bank, and for the person
checking its work. The prompt gives the case; this page gives what every case
shares: how Navigate works, where the deck goes, where its numbers may come from,
and what to report. Read all of it before writing any file. Where the prompt and
this page disagree, the prompt wins.

## First: find Navigate and check that it runs

This page needs an assistant that can read files and run commands on the person's
machine. If you can only chat, say so at once: the person needs a coding
assistant that works in a folder (see Session 5), or must paste files and run
commands for you.

- Navigate is the repository https://github.com/zerocarbonshipping/navigate-zcs,
  usually a folder named `navigate-zcs` holding `README.md`, `navigate/` and
  `assumptions/`. Every path on this page, and in the prompts, is relative to that
  folder: the repository root.
- If you were not opened in it, look for it on the machine, or ask the person
  where it is. If it is not there, say so and propose cloning it (or downloading
  the zip from GitHub), and wait for the go-ahead. Work from its root from then
  on.
- Check that Navigate is installed, from the root: `python -m pip show
  navigate-zcs` and `python -m navigate --help`. If either fails, the steps are in
  `README.md`, section "Installation" (Python 3.12 in its own environment, then
  `python -m pip install .` from the root), with a slower walk-through in
  `docs/tutorials/getting_started.md`. Show the person the commands and wait for
  the go-ahead before installing, upgrading or creating anything. Do not build a
  deck until both checks pass.

## How Navigate works

- A deck is one `.nav` file plus the `.inc` files it includes. The syntax is
  explained in `docs/reference_manual/overview.md`, and every node type (Fleet,
  Vessel, Route, Port, Fuel, Plant, Producer, Regulation, ...) has its own page in
  `docs/reference_manual/`.
- `assumptions/` is the data library. `Load DefaultVoyage` reads the module file
  `assumptions/modules/installation/default_voyage.inc`. `Import Fleet "tanker_127k_dwt"`
  reads one node from `assumptions/defaults/installation/Fleet/tanker_127k_dwt.inc`.
- `simulations/examples/example_1` to `example_6` are complete decks that run.
  Each is the reference for one structure; read the one closest to your case
  before writing a file of the same kind:
  - `example_4`: the full template for named ports (fleet, route, ports, fuel
    production, producer, EU policy, report), which the specific-trade prompts
    follow;
  - `example_1`: two fleets of two ship sizes on two connected `ROUND_TRIP`
    routes that share a port (a mainline and its feeders), with ports that
    bunker different fuels;
  - `example_2`: one fleet on a `REGIONAL_TRIP` between five ports, where only
    some ports bunker the new fuel, made far away and shipped in;
  - `example_3`: two fleets of the same classes in one market, one fitting
    efficiency measures and the other not;
  - `example_5`: a region's own fleets (tugs and ferries inside ports, cargo
    ships on a loop) and international feeders, in three decks that differ only
    in which ships the policies cover;
  - `example_6`: one `ROUND_TRIP` route through five ports in a fixed order, a
    library vessel resized as a placeholder, and a national CO2 price as a copy
    of the library's EU ETS, in two decks with and without it.

  Examples 1 to 3 are a few ships each, not a market segment: unless the prompt
  rebuilds one of them, do not copy their fleet size (and, as below, none of
  their numbers).
  `simulations/scenarios/` holds the Center's reference scenarios, which a global
  case starts from: the three basecases (no, mid and strong regulation) and
  `business_as_usual`, which splits each ship class into an international and a
  domestic fleet that sail and are covered differently. `workshop_whatif/` holds
  coarse-grid copies that run in a few minutes. Their `.nav` files are almost
  entirely `Load` statements.
- Run a deck from the repository root, in the Python environment where Navigate
  was installed from this repository, with:

  ```bash
  python -m navigate <path to the .nav file> -d ./assumptions
  ```

  `python -m navigate` run from the repository root always uses this repository's
  code; the shorter `navigate` command may point to another copy. Do not install
  or upgrade any package without asking first.
- A run that stays on one time step for several minutes has usually stalled in the
  solver (a known HiGHS problem on some decks), not failed on the deck. Stop it and
  run it once more with the environment variable `PYTHONHASHSEED=0` (PowerShell:
  `$env:PYTHONHASHSEED=0`); if it stalls again on the same step, report the step
  rather than change the deck to get past it.
- If you cannot run terminal commands, give the exact command, wait for the
  person to paste back the end of the output, and fix whatever it reports.
- A run writes a `.log` file next to the `.nav`. The end of the `.log` has a "Log
  summary" table with the number of warnings and errors. Some warnings come with
  the library and are expected on any deck built from it (for example "No
  technology cost of capital supplied", "Does not have convex load functions", or
  a feedstock being over-used by a library producer): report them, but do not try
  to fix them. The count includes repeats: check the list of unique warnings under
  it for any other kind. The same feedstock warning on a producer you wrote yourself means
  its feedstock ceiling binds: report that as a result.
- Add `Load DefaultPlot` to the `.nav` DEFINE block to also get the charts in
  `plots/` and `plots_analysis/`. Two decks in the same folder write their charts
  under the same file names, so the last run overwrites the other's; only the
  reports are kept per deck. Compare such runs from their reports.
- To get results as numbers, add `Load DefaultReport` to the `.nav` DEFINE block.
  The run then also writes `plots/<deck name>_report_default.xlsx`. Its "Global"
  sheet has one row per time step, one ConsumedEnergy column per fuel (GJ per
  year) and the emissions of all fleets together (TotalEquivalentWTW, t CO2e per
  year). It has three header rows (node, property, fuel) and an empty fourth row
  before the first year: read it with `pandas.read_excel(..., header=None)` and
  take the property and fuel names from rows 1 and 2, or the totals silently come
  out as zero. For results per fleet or per
  vessel, add your own Report node as well, with the `add_fleet_property` /
  `add_vessel_property` syntax of `simulations/examples/example_4/includes/report.inc`
  (copy the syntax, not its list). Ship counts per vessel come from
  `add_fleet_property("<fleet>", ExistingVessels)`, one column per vessel:
  ExistingVessels is not a vessel property, and a Report line that names a
  property the node lacks is logged as an error.

## Where the deck goes

Build the deck in the new folder the prompt names, under `simulations/user/`, with
the `.nav` file named after the folder and its `.inc` files in `includes/`. If that
folder already exists, add `_2` to the name (then `_3`, ...), name the `.nav` after
the folder you actually use, and say which one it is. When the prompt names the
decks itself (for example two decks to compare, each with its own name), use its
names instead. Write nothing outside that folder: do not change, move or delete any file
already in the repository.

## Numbers

Every number must come from `assumptions/` and be referenced by name
(`Forecast("...")`, `Curve("...")`, `Variable("...")`), never copied in as a
literal. Where the library itself stores a plain number (the fuel-conversion costs
in a Fleet file, the time at sea in a Route file), copy it with a comment naming
the file it came from. The global fuel standard has no library file: its
Regulation and Forecasts live in `simulations/scenarios/0_includes/`
(`mid_regulation.inc`, `strong_regulation.inc`). Copy them from there, with a
comment naming the file, and set their Jurisdiction to your own ports; they count
as sourced, not INVENTED.

The person may give numbers of their own, in the prompt or in answer to your
questions, and ask for them to be used. Use those as given, in place of the
library's, and mark each one GIVEN in a comment where it appears, with what the
prompt calls it; list them in the `.nav` header next to the INVENTED ones. They
are the person's to source: do not swap them for library values. If one is far
from the library's, say so once, in the case sheet.

Navigate reads each number in the unit its property expects, and has no units
of its own to check them: the reference manual gives the unit of each attribute,
and each library file states it in its header (`# Unit: USD / ton`). Money is in
US dollars of 2024, the library's reference year. When you ask the person for a number, give Navigate's unit for it ("the
fuel oil price, in USD per tonne"), so that they can answer in that unit. When
they give a number in another unit or currency, convert it, and keep the
original with the conversion, so that they can check it and redo it later:

- in the comment where the number appears: the original value with its unit (and,
  for money, its currency and year), each factor with its source, and the result,
  for example `# GIVEN: 12 USD/GJ x 41.2 GJ/t (lower_heating_value_oil) = 494.4 USD/t`;
- in the `.nav` header, one line per converted number, with the other GIVEN ones;
- in the case sheet, for the person to approve before you build.

The conversion is the person's responsibility, as the number is: in the case
sheet, ask them to check each conversion, its factors and its result, and do
not build until they have confirmed it.

Take physical factors from the library where it has them (a fuel's
LowerHeatingValue, a ship's capacity). The library holds no exchange rate: ask
the person for the rate to use, or propose one and give its date and source, and
write both in the comment. Money from another year is brought to 2024 dollars
the same way, with the price index and its source in the comment. If a unit, a currency or a year is missing or can be
read two ways (tonnes or long tons, lower or higher heating value, per TEU or per
tonne, today's money or a past year's), ask rather than guess. Never convert a
number without saying so.

A fleet is a market segment owned by many companies: hundreds of ships, or a
share of a library class, never one company's fleet or a single ship. Navigate
decides for the segment as a whole, in fractions of ships, so a case about one
owner's few ships is outside what it answers: say so, and model the segment
those ships belong to. When the person asks for the few ships all the same, as
the prompts that rebuild examples 1 to 3 do, build them, and say once that the
results are in fractions of ships.

Take structure from the example decks and none of their numbers, unless the
prompt gives them as its own: they hold values that exist nowhere in the
library, and in the file they look exactly as authoritative as a library
reference.

Anything the library genuinely lacks (a port-to-port distance, a bunker transport
or port handling cost, the size of a fleet that is not the whole world fleet) is
left out where the model allows it, or marked INVENTED in
a comment where it appears, and listed in the `.nav` header.

## Deck rules

- The `.nav` DEFINE and EVENTS blocks accept only `Include` and `Load`. Every node
  declaration, `Import` and `Copy` goes in an `.inc` file that they include.
- A deck on a trade of its own builds its Fleet node from the library's Vessel
  files with `Copy Vessel`, as `simulations/examples/example_4/includes/fleet.inc`
  does. `Import Fleet` brings the world fleet, with a world-sized fleet and
  orderbook, which is right for a global deck and wrong for a trade. A deck on named
  ports takes its structure from example_4.
- The library's operational profiles are world-average patterns between two
  abstract ports (`port_global`, `port_europe`) that exist for regulatory scope,
  not places on a map. A deck on named ports builds a ROUND_TRIP route between
  them, taking speeds and time in port from the profile's own values, as
  example_4's `route.inc` does (its comments show the arithmetic). The profile
  lists a spread of speeds: take the most common one in its ConditionDistribution,
  laden and in ballast, and say so in a comment, with a
  realistic sea distance marked INVENTED.
- A deck on named ports also rebuilds the other parts example_4 has, with its own
  values: the ports, the bunker logistics (how fuel travels from the plants to each
  port) and the regions (where the fuels are made). `Import Region` brings only
  the region's own lines (power prices, grid emissions); the process costs and
  most feedstocks are in the `Region "*"` block of
  `assumptions/modules/installation/default_region.inc`, so restate the lines your
  plants use. BunkerLogistics takes its
  distances and transport cost as plain numbers, not as Variables. Give the fuel
  producers a share of the library's feedstock ceilings, marked INVENTED, as
  example_4's `producer.inc` does. The library's ceilings are what all shipping
  may use, so size the share to the fleet: roughly its first-year energy divided
  by world shipping's, about 13,000 PJ in 2026 in the reference scenario. A
  larger share hands a small fleet the world's biomass, and the answer follows the
  feedstock rather than the question. Never raise it to make a fuel appear.
  Estimate the first-year energy from the class's fuel use before the first run;
  after it, check the estimate against the report and say if it is off by more
  than a factor of two.
- The library's biogenic CO2 pool (`carbon_dioxide_biogenic_availability`) grows to
  350 Mt a year by 2050. Use it as it is unless the prompt says otherwise:
  example_4 holds it flat at its 2026 value by choice. The full prompt of the
  bank entry you take as your model counts as the prompt.
- When the case puts fuel production in a country the library has no region for,
  declare a Region of your own with the lines of the nearest library region,
  marked INVENTED, and give it its own `set_distance` lines. The library makes
  FAME in Europe only: elsewhere it is a European import, or a copy of Europe's
  lines marked INVENTED.
- On named ports, say what each port sells. Every fuel can be bunkered at every
  port unless the deck says otherwise (`set_bunkering_allowed` defaults to TRUE),
  and a region-port pair with no `set_distance` delivers at no cost (the default
  distance is 0). Set `set_bunkering_allowed` for every fuel at every port, FALSE
  where it may not be bunkered, and give a distance for every pair that delivers.
- The `set_voyage_distribution` command that splits a route's work between port
  pairs is missing from this version's reference manual. It takes two port
  names and a share; `"*", "*", 0` first clears the default split.
- A plant you Import or Copy brings no Region, Source or CostOfCapital: the
  library sets those in `assumptions/modules/installation/default_plant.inc` by
  wildcards on its own plant names. Set all three on every plant yourself, as that
  file does for the kind and region; a plant without a cost of capital is silently
  financed at 0 %. The regional plants (`plant_*_europe` and the like) are not
  files either: that file makes them with `Copy Plant` lines, so write the same
  Copy in your deck.
- A ROUND_TRIP route has no time-at-sea setting: the year is sailing plus the
  port stays, so the share of the year at sea follows from the distances, speeds
  and port durations. Route distances, like BunkerLogistics, take plain numbers
  only.
- Ships that work inside ports rather than between them (tugs, harbour ferries)
  take a REGIONAL_TRIP route: list the ports, split the work between them with
  `set_voyage_distribution("<port>", "<port>", share)` after
  `set_voyage_distribution("*", "*", 0)`, and split `PortCalls` the same way.
  Without the split every port pair gets an equal share. TimeAtSea, Speeds and
  CapacityUtilizations come from the class's operational profile.
- A Regulation or Levy you write covers no ship unless it says
  `set_include_vessel("*", TRUE)` (or names the vessels). The reference manual
  gives TRUE as the default, but Navigate's code uses FALSE, and nothing warns.
- A carbon price meant to steer which ships are ordered is a Regulation, not a
  Levy. A Levy changes what the existing ships bunker, but it is left out of the
  expected costs the newbuild choice and the investment freight rate are made on.
  The simplest Regulation is a copy of the library's `eu_ets` with its
  Jurisdiction and RemedialCost changed. A Levy's Level is a Forecast, not a
  Curve, and what it cost shows in TotalLevyExpenses, not RegulationExpenses.
  RegulationExpenses is the total over all regulations; for each one, report
  `add_regulation_property` RemedialExpenses, FlexibilityExpenses and
  SurplusRevenue (net = remedial + flexibility - surplus), from a Report node in
  the policy's own `.inc`, so the deck without the policy stays unchanged.
- A copied or imported library node brings every reference it makes: copying
  `eu_ets` needs all the fuels it names to exist. Import the missing ones rather
  than deleting lines from the copy.
- With AllowSpeedManagement on, the ships may sail faster than the route's
  speeds, not only slower. Check ActualSpeed before reading energy use or ship
  counts.
- A deck that changes a vessel's CostOfCapital should set the Fleet's
  TechnologyCostOfCapital explicitly: without it, efficiency technology is
  financed at each vessel's own rate and inherits the change.
- Node names are unique across node types: a Regulation cannot share its name
  with the Forecast that sets its price, nor a Report with the Regulation it
  reports on (call it `report_eu_ets`, not `eu_ets`).
- If you rename copied vessels, check that the Fleet file's
  `set_fuel_conversion_cost` wildcards still match the new names, and restate
  those lines if they do not.
- When the case's ships fall between two library classes, take the nearest class
  by size and say so in the header; resizing it makes its values INVENTED.
- When the case states a change that can be read two ways ("20 % stricter":
  deeper reductions, or a lower limit), ask which, and write the reading down in
  a comment.
- The workshop's coarse grid (`time_steps_coarse.inc`: 2026, 2027, 2030, then
  every four years) has no step in 2028 or 2029, so a policy that starts or
  changes then is never simulated. Add a `Date` for that year to every deck you
  compare, and say so; when the decks must differ in one Include line only, keep
  the grid instead, and say which policy dates fall between steps. A sum over a
  coarse grid weights each step by the years until the next step, and the last
  step by one year: say so next to the sum.
- A deck built on the library's modules also loads what every library deck needs,
  as the reference scenarios' `.nav` files do: `DefaultModelDefinition`,
  `DefaultBunkerLogistics` (without it the first year's bunkering has no feasible
  solution) and `DefaultCalibration` in DEFINE, and `DefaultTimeStepYearly` in
  EVENTS. A deck on named ports declares its own BunkerLogistics instead, as
  example_4 does, and then does not load `DefaultBunkerLogistics` as well.
- Do not load `DefaultConverterAvailable` on a deck with fewer than the library's
  twenty-three fleets. It phases alternative vessel types in over time using
  wildcards like `Fleet "tug*"` that only resolve against the full set, so it
  fails to parse on a cut-down deck. Say in the `.nav` header that every vessel
  type is therefore orderable from year one rather than phased in. When the
  prompt asks for the library's dates instead, write them out in an `.inc` file
  read from EVENTS, with `Start`, `Date` and `End` and one `Fleet` block per
  fleet of yours, copying the dates of
  `assumptions/modules/installation/default_converter_available.inc`.

## Before you say it works

Run the deck (or have the person run it) as above. Report the exit code and the
warning and error counts from the Log summary. Then give what the prompt asks for,
from the report rather than from the charts, and at least the fuel mix in the
first year and the last. Say plainly whether anything actually switched.

Things that are easy to misread:

- A methanol or ammonia ship can run entirely on its oil pilot fuel, and does
  when no alternative fuel is on offer. A growing number of these ships is not a
  fuel switch: judge it from the energy consumed by fuel (ConsumedEnergy), not
  from the ship count. FuelTypeEnergy cannot tell fuel oil, FAME and e-diesel
  apart: all three are of fuel type OIL. A vessel property such as ConsumedEnergy
  in your own Report is per ship: multiply by ExistingVessels before comparing it
  with the Global sheet.
- A bunker price of 0 for a fuel at a port means there is no supply of it, not
  that it is free. So does a price far below what making the fuel costs, close
  to the delivery cost alone, in a year before any plant produces it. To say how far such a fuel is from competing, add
  `add_plant_property("*", InvestmentIntensityCost)` to your Report: it gives
  each plant's levelised cost per GJ every year, even when none is built.
- The investment freight rate and ActualSpeed have no value in the first time
  step; quote the second if the first is asked for. Whether any plant was built does not appear
  in DefaultReport: look at `plots/producer_development.png`.
- The Log summary does not count a bunkering step that failed to converge: it is
  logged as INFO, not as a warning. Search the `.log` for
  "convergence status: Failure" and report the years it names.
- To compare the fleet's fuel use with a published figure, report
  `add_fleet_property("*", TotalConsumedMass)`, the fuel burnt in tonnes a year.

## Then prepare the case's prompt bank entry

The prompt bank grows from the cases people build. Once the decks run cleanly,
end your report with a section headed **Prompt bank entry**, ready to paste:

- the index line: the family, the question, the scale, the ships, the policy,
  what the case changes, and "built <date>";
- the model you took (a bank entry), or "none close" if no entry was;
- the case sheet as approved, written as the differences from that model
  ("Variant of <entry>, with these differences: ...");
- the test result: exit code, warnings and errors per deck, and the first-year
  well-to-wake intensity and energy.

If no entry was close, or the deck needed a structure that none of them has, also
write the full prompt that rebuilds the deck as it now is, in the style of the
bank's full prompts. Tell the person that Step 7 of Session 5 says where to send
the entry.

## Then offer an explanation notebook

Once the deck runs and you have reported, ask the person whether they also want
an explanation notebook for the case. Build it only if they say yes; the deck is
finished either way.

The notebook, `explore.ipynb` in the deck's folder, opens with a picture of the
case, then says what the case is (the ships and how many, the ports, the fuels
that can compete, the policy and whom it covers), how to run the deck, what it
found, and which numbers are INVENTED. Keep to this deck's facts: every number
it quotes comes from the deck or from your run.

Keep its prose to the minimum: short lists rather than paragraphs, no
explanations of Navigate (the workshop sessions give those), and nothing the
figures already show.

The picture is drawn by a script you write in the deck's folder, for example
`figures/make_case_map.py`, which reuses the workshop's map code in
`docs/_figures/` rather than starting from nothing:

- A deck on real ports gets a map. Import `make_gulf_asia_map.py` as a module and
  use its basemap (`ne_110m_countries.geojson`), its label solver and its check
  that every voyage stays at sea. Set your own window and projection, and place
  the ports from your route and the production sites, with their delivery
  distances, from your bunker logistics. Read `docs/_figures/README.md` first.
- A deck without geography (`port_global`, `port_europe`) gets a schematic
  instead: take `make_two_fleets_schematic.py` as the model, and show the fleets,
  the fuels and where the policy applies.

Colours come from `docs/workshop/_style.py`, as in every workshop figure.
Rasterise the SVG with `render_map_png.py`, after setting
`render_map_png.STATIC` and `render_map_png.HERE` to your `figures/` folder, so
that nothing is written under `docs/`. It needs Chrome, Chromium or Microsoft
Edge; if there is none, say so and leave the picture out rather than embed a broken one. Put the
PNG in the notebook's first markdown cell as a base64 image, written as ONE
string in the cell's `source` (the README says why), with `nbformat`.

Build the rest of the notebook on the layout of Session 1,
`docs/workshop/01-run-a-simple-case.ipynb`, or of Session 2,
`02-run-a-global-case.ipynb`, for a global case. Copy their cells and adapt them
to this deck, rather than writing new machinery or new kinds of figures:

1. **The case**: the picture, then the description above.
2. **Setup**: Session 1's Setup cell, which finds the repository root and holds
   the machinery (`run_case`, `scale`, `both`, `summarise`, `plot_cases`,
   `run_your_scenario`), pointed at this deck instead of example_4. Keep
   Session 1's palette and figure functions from `docs/workshop/_style.py`.
3. **Run the case and see the results**: the reference run, with Session 1's
   figure (well-to-wake emissions, freight rate, fuel consumed by fuel) and its
   table of results. When the case has several decks, run each one and show
   them side by side in that same figure, as Session 2 compares its scenarios.
4. **Change the inputs**: Session 1's lever cell, with levers for this deck: a
   multiplier on each INVENTED value and on the inputs the case's question turns
   on (a fuel price, a policy's level), each with the value it multiplies in a
   comment. A lever multiplies a Forecast or a Variable, so keep the INVENTED
   values you want as levers in Variables; plain numbers (distances, bunker
   logistics) cannot be. Running it re-solves the case and compares it with the reference and
   with the previous run.
5. **Navigate's own charts**, for the reference run: drawn again in the
   workshop palette with `navigate_charts(run_folder, out_folder)` from
   `_style.py`, which reads the run's `plot_data.pkl`. Every run overwrites the
   `plot_data.pkl` of its folder, the notebook's lever runs included, so copy it
   to `runs/<deck>/plot_data.pkl` in the cell that runs each deck, before any
   lever runs.

Under each figure, write at most one sentence on what it shows, from your run's
numbers. Keep Session 1's quieting of Navigate's log in `run_case`, or the
library's expected warnings fill the outputs. Run the notebook from the
repository root, and execute it once before handing it over, with
`PYTHONUTF8=1`, so that the figures are saved in it: with `jupyter nbconvert
--to notebook --execute --inplace`, or, if that is missing, with `nbclient` and
the `python3` kernel.
Check that no output shows an error, a local path or a user name.

## Improving this page

End your report with a short section headed **For building-a-deck.md**: anything
you had to work out, or got wrong first, that this page should have told you,
written as the sentence you would add here. Leave it out if there is nothing. The
person can then propose it to the workshop authors, by an issue or a pull request
on this file, so the next deck is built with it.

<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Building a deck with an AI assistant

This page is written for the AI assistant that builds a Navigate deck from one of
the prompts of [Session 5](05-build-your-own-case.ipynb), and for the person
checking its work. The prompt gives the case; this page gives what every case
shares: how Navigate works, where the deck goes, where its numbers may come from,
and what to report. Read all of it before writing any file. Where the prompt and
this page disagree, the prompt wins.

## How Navigate works

- A deck is one `.nav` file plus the `.inc` files it includes. The syntax is
  explained in `docs/reference_manual/overview.md`, and every node type (Fleet,
  Vessel, Route, Port, Fuel, Plant, Producer, Regulation, ...) has its own page in
  `docs/reference_manual/`.
- `assumptions/` is the data library. `Load DefaultVoyage` reads the module file
  `assumptions/modules/installation/default_voyage.inc`. `Import Fleet "tanker_127k_dwt"`
  reads one node from `assumptions/defaults/installation/Fleet/tanker_127k_dwt.inc`.
- `simulations/examples/example_1` to `example_4` are complete decks that run.
  `simulations/scenarios/` holds the Center's reference scenarios; their `.nav`
  files are almost entirely `Load` statements.
- Run a deck from the repository root, in the Python environment where Navigate
  was installed from this repository, with:

  ```bash
  python -m navigate <path to the .nav file> -d ./assumptions
  ```

  `python -m navigate` run from the repository root always uses this repository's
  code; the shorter `navigate` command may point to another copy. Do not install
  or upgrade any package without asking first.
- If you cannot run terminal commands, give the exact command, wait for the
  person to paste back the end of the output, and fix whatever it reports.
- A run writes a `.log` file next to the `.nav`. The end of the `.log` has a "Log
  summary" table with the number of warnings and errors. Some warnings come with
  the library and are expected on any deck built from it (for example "No
  technology cost of capital supplied", "Does not have convex load functions", or
  a feedstock being over-used by a library producer): report them, but do not try
  to fix them.
- Add `Load DefaultPlot` to the `.nav` DEFINE block to also get the charts in
  `plots/` and `plots_analysis/`. Two decks in the same folder write their charts
  under the same file names, so the last run overwrites the other's; only the
  reports are kept per deck. Compare such runs from their reports.
- To get results as numbers, add `Load DefaultReport` to the `.nav` DEFINE block.
  The run then also writes `plots/<deck name>_report_default.xlsx`. Its "Global"
  sheet has one row per time step, one ConsumedEnergy column per fuel (GJ per
  year; the fuel name is in the third header row) and the emissions of all fleets
  together (TotalEquivalentWTW, t CO2e per year). For results per fleet or per
  vessel, add your own Report node as well, with the `add_fleet_property` /
  `add_vessel_property` syntax of `simulations/examples/example_4/includes/report.inc`
  (copy the syntax, not its list).

## Where the deck goes

Build the deck in the new folder the prompt names, under `simulations/user/`, with
the `.nav` file named after the folder and its `.inc` files in `includes/`. If that
folder already exists, add `_2` to the name (then `_3`, ...), name the `.nav` after
the folder you actually use, and say which one it is. Write nothing outside that folder: do not change, move or delete any file
already in the repository.

## Numbers

Every number must come from `assumptions/` and be referenced by name
(`Forecast("...")`, `Curve("...")`, `Variable("...")`), never copied in as a
literal. Where the library itself stores a plain number (the fuel-conversion costs
in a Fleet file, the time at sea in a Route file), copy it with a comment naming
the file it came from.

Take structure from the example decks and none of their numbers: they hold values
that exist nowhere in the library, and in the file they look exactly as
authoritative as a library reference.

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
  orderbook, which is right for a global deck and wrong for a trade.
- The library's operational profiles are world-average patterns between two
  abstract ports (`port_global`, `port_europe`) that exist for regulatory scope,
  not places on a map. A deck on named ports builds a ROUND_TRIP route between
  them, taking speeds and time in port from the profile's own values, as
  example_4's `route.inc` does (its comments show the arithmetic), with a
  realistic sea distance marked INVENTED.
- A deck on named ports also rebuilds the other parts example_4 has, with its own
  values: the ports, the bunker logistics (how fuel travels from the plants to each
  port) and the regions (where the fuels are made). `Import Region` brings only
  the region's own lines (power prices, grid emissions); the process costs and
  most feedstocks are in the `Region "*"` block of
  `assumptions/modules/installation/default_region.inc`, so restate the lines your
  plants use. BunkerLogistics takes its
  distances and transport cost as plain numbers, not as Variables. Give the fuel
  producers a share of the library's global feedstock ceilings, marked INVENTED,
  as example_4's `producer.inc` does.
- A ROUND_TRIP route has no time-at-sea setting: the year is sailing plus the
  port stays, so the share of the year at sea follows from the distances, speeds
  and port durations. Route distances, like BunkerLogistics, take plain numbers
  only.
- A Regulation or Levy you write covers no ship unless it says
  `set_include_vessel("*", TRUE)` (or names the vessels). The reference manual
  gives TRUE as the default, but Navigate's code uses FALSE, and nothing warns.
- A carbon price meant to steer which ships are ordered is a Regulation, not a
  Levy. A Levy changes what the existing ships bunker, but it is left out of the
  expected costs the newbuild choice and the investment freight rate are made on.
  The simplest Regulation is a copy of the library's `eu_ets` with its
  Jurisdiction and RemedialCost changed. A Levy's Level is a Forecast, not a
  Curve, and what it cost shows in TotalLevyExpenses, not RegulationExpenses.
- A copied or imported library node brings every reference it makes: copying
  `eu_ets` needs all the fuels it names to exist. Import the missing ones rather
  than deleting lines from the copy.
- With AllowSpeedManagement on, the ships may sail faster than the route's
  speeds, not only slower. Check ActualSpeed before reading energy use or ship
  counts.
- Node names are unique across node types: a Regulation cannot share its name
  with the Forecast that sets its price.
- If you rename copied vessels, check that the Fleet file's
  `set_fuel_conversion_cost` wildcards still match the new names, and restate
  those lines if they do not.
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
  type is therefore orderable from year one rather than phased in.

## Before you say it works

Run the deck (or have the person run it) as above. Report the exit code and the
warning and error counts from the Log summary. Then give what the prompt asks for,
from the report rather than from the charts, and at least the fuel mix in the
first year and the last. Say plainly whether anything actually switched.

Three things that are easy to misread:

- A methanol or ammonia ship can run entirely on its oil pilot fuel, and does
  when no alternative fuel is on offer. A growing number of these ships is not a
  fuel switch: judge it from the energy consumed by fuel (ConsumedEnergy), not
  from the ship count. FuelTypeEnergy cannot tell fuel oil, FAME and e-diesel
  apart: all three are of fuel type OIL.
- A bunker price of 0 for a fuel at a port means there is no supply of it, not
  that it is free. To say how far such a fuel is from competing, add
  `add_plant_property("*", InvestmentIntensityCost)` to your Report: it gives
  each plant's levelized cost per GJ every year, even when none is built.
- The investment freight rate has no value in the first time step; quote the
  second if the first is asked for. Whether any plant was built does not appear
  in DefaultReport: look at `plots/producer_development.png`.

## Improving this page

End your report with a short section headed **For building-a-deck.md**: anything
you had to work out, or got wrong first, that this page should have told you,
written as the sentence you would add here. Leave it out if there is nothing. The
person can then propose it to the workshop authors, by an issue or a pull request
on this file, so the next deck is built with it.

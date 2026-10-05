<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!-- What gets an entry: CONTRIBUTING.md, Changelog. -->

## [Unreleased]

### Added
- The console prints the number of logged warnings at the end of a run,
  pointing at the `.log` file.
- Vessel report properties `SpeedEnergyIntensitySaving`,
  `OperationalEnergyIntensitySaving`, `TechnologyEnergyIntensitySaving` and
  `EnergyIntensitySaving` on `add_vessel_property`: energy savings per
  cargo-mile, counting the transport work lost when a vessel slows down.
- Report properties `ShorePowerEnergy`, `ShorePowerExpenses` and
  `ShorePowerEmission` at vessel, fleet and global level.
- The `Saving`, `RemedialUnits` and `LevyUnits` report properties can now be
  requested; they used to produce no column.

### Changed
- A calculator (`Variable`, `Forecast`, `Curve`, `Timetable`, `Surface`)
  assigned in `DEFINE` to an attribute or command that `EVENTS` cannot change
  cannot be changed in `EVENTS` either; re-assigning its attributes there is a
  deck error.
- A calculator or expression whose value reaches an attribute's exclusive
  minimum or maximum, such as a zero `Variable` as a Plant's `Capacity`, stops
  the run with an error naming the node instead of being clamped onto it.
- An empty `InitialSplit` (Fleet) or `ConditionDistribution` (Route), or one
  summing to 0, is a deck error at its line. Omitting `InitialSplit` still
  gives a uniform split.
- `CAPEX`/`OPEX` are now `Capex`/`Opex`, and report properties end in
  `Wtt`/`Ttw`/`Wtw` (`TotalEquivalentWtt`). An old report property spelling
  is a deck error at its line.
- An undersized converter raises a `PowerCapacityError` naming the vessel,
  converter, leg or port and the required and installed power, instead of an
  LP infeasibility. The check is also tighter:
  - port electrical demand must fit the onboard electrical converter even
    where shore power is available;
  - on regional routes it holds for each condition leg, not their mean.
- `Propulsion`, `Electrical` and `Heat` on a `PowerSystem` must be three
  distinct converters. One converter may still serve several power systems.
- Fleet and global energy savings are energy-intensity savings against the
  energy the year-0 raw intensity would need for the transport work
  performed. The `fleet_energy_saving` and `global_energy_saving` plots follow.
- On `add_property` and `add_fleet_property`, the `*EnergySaving` properties
  are now `*EnergyIntensitySaving` (they stay on `add_vessel_property`), and
  `SpeedEnergyIntensitySaving` is new.
- Three wildcard uses are rejected at their line: a glob as a command
  argument, a glob on a single-valued attribute (`Route = Route("r_*")`), and
  a node listed beside a glob that also matches it.
- A smoothed price belief (flexibility cost, energy scarcity) ramps up when a
  price first appears after a stretch of exactly zero instead of taking it in
  full; `basecase_mid_regulation` moves by up to about 0.5% from 2030 (#25).
- Nodes that no chain of references connects to a top-level node are removed
  after `DEFINE`, with one aggregated warning. As a result:
  - a `Port` counts only through a `Route`'s `Ports`, not a `Jurisdiction`;
  - `EVENTS` statements targeting only removed nodes are dropped;
  - a command naming a removed node fails with a hint naming it;
  - an incompletely configured unused node no longer errors.
- Technology `Capex`/`Opex` enters the vessel cost metrics, so newbuild choice
  shifts. `TechnologyExpenses` and `CumulativeTechnologyExpenses` replace the
  never-populated `TechnologyNewbuildExpenses` and
  `TechnologyRetrofitExpenses`.
- Shore power is counted in `TotalConsumedEnergy`, `TotalFuelExpenses` and
  the `TotalEquivalentWtw` emissions, and so in the expense and Wtw plots.
- Fuel-conversion expenses are levelized exactly at the destination vessel's
  cost of capital and booked per service year. The old factor overstated them
  (about 21% at a 5-year window and 8% discount rate).
- The fuel-conversion business case compares the two vessel types' fuel costs
  over their common remaining-lifetime window.
- An empty `Speeds` or `PortDurations` on a `Route`, in `EVENTS` too, is
  rejected at its deck line.
- Rescaling `InitialSplit` or `ConditionDistribution` by more than 1% is
  logged as a warning, so it counts in the end-of-run summary.
- A `Report` property request that matches no node logs a warning instead of
  silently producing no columns.
- The warning about a missing `TechnologyCostOfCapital` is removed; the
  fallback to the vessel's cost of capital is documented on the attribute.
- The fuel-conversion warning about differing installed power is logged once
  per vessel pair, and the fleet reference speed at a step with no vessels is
  NaN.
- An attribute's bounds reach the calculator it references when the
  assignment is read, so the calculator keeps them if the attribute is
  re-assigned later in `DEFINE`, as it always did across `EVENTS`.
- The minimum supported Python version is 3.13 (was 3.12).
- `plot_data.pkl` files saved by earlier versions cannot be loaded with
  `--replot`; replot them with the version that produced them.
- A regulation's default fuel WTT averages over every port on the vessel's
  route, each once, not only the jurisdiction ports, where it was 0 without
  supply. Results move where a route leaves the jurisdiction.
- A `Levy`'s `LowerThreshold` and `UpperThreshold` are measured per GJ of
  effective energy, (1 − slip) · LHV, as a `Regulation`'s intensity already
  is, so a threshold covers fewer emissions per ton of a fuel with converter
  slip, such as LNG.
- An `add_*_property` naming a property its command does not report stops the
  parse at its line, instead of dropping the column with an error in the
  `.log` (#105).
- A deck whose node reference is never resolved, such as a node passed where
  a name is expected, now stops at the referencing line instead of running
  with the reference ignored (#148).

### Removed
- `BunkerLogistics`: write `LiquidMarket` on `Fuel`, and `set_fuel_transport`
  and `set_fuel_distance` on `Plant`, priced at the region's
  `set_transport_cost`/`set_transport_wtt`. The examples lose their flat
  transport costs.
- The `-e`/`--export-assumptions` CLI flag.
- The `SharedThreshold` attribute of `Regulation`; write
  `set_vessel_threshold("*", <value>)`. The `SharedThreshold` report property
  remains, as the fleet-level effective target of a `FLEXIBLE` regulation.
- The `CumulativeIntensityEquivalent*` and
  `CumulativeIntensityTotalEquivalent*` report properties.
- Unused profile report properties:
  - volume-denominated output, FuelType mass aggregation, fuel-quantity
    cumulatives and non-GWP-equivalent emission variants;
  - plant Ttw/Wtw and capacity, production and feed output;
  - producer capacity, pipeline and source output;
  - vessel Opex and activity output, policy emission factors, port bunker
    Wtw, fleet scrap-age statistics and the levy level.
- The `producer_changes` plot.
- The debug plots `fuel_supply_demand_expectation`, `fleet_newbuild_sources`,
  `fleet_fuel_conversion_sources`, `fleet_fuel_conversion_sources_normalized`,
  `technology_install_sources` and `technology_install_sources_normalized`,
  with the `InertiaNewbuilds` and `ModelledNewbuilds` report properties.
- The belief fan in the `regulation_flexibility_cost` plot.
- The `fleet_orderbook` plot and the `PrimaryScrap`, `SecondaryScrap` and
  `OrderbookNewbuilds` report properties; `Scrap` and `Newbuilds` remain.
- The always-zero `EmissionExpenses`, `TotalEmissionExpenses` and
  `CumulativeEmissionExpenses` report properties and the "Emission storage"
  layer of the `global_expenses` plot.
- Emission offsetting: `EnableOffsetting`, `OffsettingCost`, `AllowOffsetting`
  and `OffsetThreshold`, the `regulation_offsetting_units`, `_expenses` and
  `_cost` plots, and the offset lines of the emission and compliance plots.

### Fixed
- Reference-manual corrections:
  - default nodes and modules live under `<data_dir>/defaults/` and
    `<data_dir>/modules/`, and a separate reference to a Copy source pulls
    that source from the defaults again;
  - emission intensities are in kg/GJ and both transport measures in grams
    per cargo-mile, where several entries were a factor of 1000 or a million
    out;
  - twelve accepted attributes and commands gain an entry, and five entries
    for attributes no node has are gone;
  - the report-property appendix lists what a report can export: unresolved
    rows are gone or respelled (`VesselThreshold`, `ConverterEnergy`,
    `OverheadTime`, …) and missing rows are added;
  - a Surface or Timetable header row is the y-axis and its first column the
    x-axis, not the other way round;
  - an enum wildcard in a command expands over every member of the enum;
  - the `InitialSplit` and `ConditionDistribution` rescale is proportional,
    not by equal fractions, and is logged above a 1% deviation;
  - the `BunkerOptions` defaults, `Threads` type and exclusive minimums;
  - `Converter` `MinimumLoad`, `Efficiency` and `set_consumption_ttw` take no
    `Forecast`, and `PowerCapacity` takes a `Variable`;
  - `set_voyage_distribution` on `Route` takes no `Forecast`;
  - the port properties are `EquivalentBunkerWtt` and
    `TotalEquivalentBunkerWtt`.
- Deck errors that ended in a Python traceback, named no deck line or were
  badly worded now read as located deck errors:
  - a rejected attribute or command value prints the one-line error and
    exits 1;
  - a node declared, imported or copied under a name already in use;
  - a reference whose type is not a node type, such as `Foo("x")`;
  - a missing user or installation folder under `defaults/` or `modules/` is
    treated as empty;
  - an installation default that imports or copies its own node;
  - a wildcard that matches nothing, or stands where one node is expected;
  - a wildcard `Import` colliding with a used name, at the deck's `Import`
    line;
  - a default file that does not yield the requested node;
  - a node found in neither the deck nor the defaults, which opened with a
    bare colon;
  - a value of a kind the attribute does not take, including a table or an
    enum token in a scalar slot (`Capex = FLAT`);
  - a wrong kind on a boolean, ID or ID-list attribute (`Active = [1.0]`);
  - an integer or boolean in a scalar slot, named by kind;
  - a non-number in `InitialSplit` or `ConditionDistribution`;
  - an unparseable expression, or two statements on one line, when the file
    is read;
  - the `Surface` and `Timetable` messages that printed `{}` for the node;
  - a rejected command value, now ending in a full stop;
  - the missing-assumptions-directory errors, now naming `-d/--data-dir` and
    `ASSUMPTIONS_DATA_DIR`;
  - a rejected bound, which now names the scalars, `-INF` and `INF` it takes;
  - an unassigned `StartDate`, `LowerHeatingValue` or `MassDensity`, now
    reported as unassigned;
  - a list of the wrong length, now reading "at least" or "at most";
  - an invalid boolean keyword in a command (`set_allow_vessel("v", MAYBE)`);
  - a `Variable`, now named `Variable("name")` instead of by its value;
  - a deck with no Fleet, now reading "No Fleets are defined." alone;
  - a command with an unknown key and an invalid value, now reporting the
    value;
  - a `Surface` or `Timetable` table with only a header, one data row or one
    header value.
- An expression (`<...>`) where a node is expected, or in
  `InitialAgeDistribution` or `set_existing_pipeline`, stops the deck at its
  line instead of being stored unevaluated; `set_feed_transport` and
  `set_fuel_transport` refuse a number.
- A `Curve` given to `set_global_warming_potential` on a `Levy` or
  `Regulation` is read at the emissions lifetime; the run used to fail.
- An expression on `Multiplier` or `Addition` of a calculator, or on `Below`,
  `Above` or `Outside` of a table, is evaluated instead of failing the run
  (#226).
- The order of the attributes in a `Curve` or `Surface` no longer matters;
  settings after `Table` were ignored. The default methane GWP and
  `technology_uptake` curves now extrapolate flat outside their tables (#273).
- The `RemedialUnits` and `LevyUnits` report columns sum over the vessels at
  fleet and global scope, where they were zero.
- `set_bunkering_cost` is rejected on a `Port` at its line instead of failing
  the run; use `set_handling_cost`.
- The CLI rejects a deck path whose name is only dots before `.nav`.
- The bounds an attribute imposes reach a calculator matched by a wildcard,
  as they did for one written by name.
- A wildcard matches its other characters literally; only `*` and `?` are
  wildcards, so `a.b` no longer matches `aXb`.
- An `INF` entry in `InitialSplit` or `ConditionDistribution`, or entries
  whose sum overflows, stop the deck at its line instead of yielding NaN.
- `set_operational_saving_port` takes only `ELECTRICAL` and `HEAT`: its
  wildcard no longer reaches `PROPULSION` and fails, and an explicit
  `PROPULSION` is a deck error instead of a silently unread entry.
- `set_operational_saving_port` names the demands it accepts when it rejects
  a key: `only allows assignment of ELECTRICAL, HEAT, but got X`.
- `set_initial_technology_share` values built from expressions are honored
  instead of being ignored.
- `set_fuel_wtt`, `set_fuel_ttw` and `set_global_warming_potential` on a
  `Levy` or `Regulation` hold beyond the first time step. Results change for
  decks using them, including `simulations/examples/example_1`.
- The bunker LP's regulation coefficients reset every time step, so entries
  of vessels that left a fleet no longer leak into later steps.
- The LP is built in the same order on every run, so dual values no longer
  vary between runs in degenerate solves.
- Fuel-conversion expenses are booked on the elapsed-years axis, so
  calendar-date timelines no longer drop or distort the conversion year.
- With sub-year time steps, the fuel-conversion business case no longer
  prorates a year twice.
- The expected fuel-delivery cost from plant to port is levelized against the
  plant's production over its operating years, as the production cost is.
  Results change for decks assigning `FuelTransport`.
- A user default file that pulls another default node before importing its
  own name still overlays the installation node of that name.
- An integer attribute accepts a value just off a whole number from either
  side: `2.999999` is 3, where it was rejected.
- An `InitialAgeDistribution` curve starting at a negative age contributes
  zero tied capital instead of failing for vessels.
- A deck with no Emission node reports its total-equivalent emissions, their
  cumulative totals and the port bunker intensities as zero series, so the
  report keeps those columns.
- A `Variable` in `set_power_transfer` combined with another technology's
  `Curve` for the same energy-type pair no longer fails the run.
- `FlexibilityHorizon` on a `Regulation` whose scheme is not `FLEXIBLE` logs
  a warning that it is ignored.
- A wildcard node declaration whose `InitialSplit` or `ConditionDistribution`
  is rescaled logs the rescale for every matched node, not just the first.
- The fuel-conversion proposal walk skips an increment with no eligible
  destination instead of stopping there.
- `FairShareMaximumIterations` rejects a non-integer such as `2.5` at its line
  instead of truncating it, and an expression instead of ending in a Python
  error.
- An expression on `SolutionTolerance`, `FairShareTolerance` or
  `EmissionsLifetime` on `ModelDefinition` is a deck error at its line instead
  of failing the run.
- `set_slip_fraction` and `set_consumption_ttw` name the fuel types the
  Converter declares when they reject one:
  `only allows assignment of METHANE, OIL, but got AMMONIA`.
- `set_consumption_ttw` accepts a wildcard emission name, such as
  `set_consumption_ttw(OIL, "*", 0.001)`, which it rejected.
- A producer's expected production has pipeline plants enter, and plants at
  the end of their lifetime leave, spread over a time-step, as delivery and
  decommissioning do, where it moved each batch at once. Results change.
- Fuel a producer delivers above a port's `set_bunkering_limit` is
  redistributed to the other ports in proportion to their deficit instead of
  being silently dropped; a port with no limit set absorbs whatever the
  limited ports could not, and a port the producer sends no fuel to receives
  no share.
- A `Levy`'s `LowerThreshold` and `UpperThreshold` are read at every future
  time step of the bunkering expectation instead of holding the value cached
  at the current one; a time-varying threshold no longer freezes at today's
  value for the rest of the run.
- `INF` is rejected with the deck line where it has no meaning, instead of
  giving NaN results or an OverflowError; only limits, bounds and calculator
  values accept it, and tables reject `nan` and infinite coordinates (#336).
- A report property keyed by a two-element tuple summed over the wrong
  element for `FIRST` and `SECOND`; the default report's `FuelConvertedPower`
  now requests `SECOND` to keep its from-fuel columns as before (#209).
- A `Levy` whose `UpperThreshold` falls below its `LowerThreshold` at any time
  step stops the run with an error naming the date, instead of turning the
  penalty into a subsidy from then on (#335).
- A `Producer`'s `JumpStartFraction` now also accepts a `Variable`, and an
  expression assigned to it is evaluated where the producer's evolution
  expectation reads it, instead of crashing with a `TypeError` (#348).
- An expression assigned to a `Vessel`'s `PropulsionLoad`, `ElectricalLoadAtSea`
  or `HeatLoadAtSea` no longer crashes the run with an `AttributeError` at the
  first time step; it sets no technical speed limit and counts as non-convex,
  which logs the existing "does not have convex load functions" warning.
- With the HiGHS solver, a non-compliant `Regulation` with
  `AllowThresholdAdjustment = TRUE` and a measure other than `INTENSITY` no
  longer crashes the run with an `AttributeError` (#365).
- With the HiGHS solver, shore power in port is capped by the vessel's
  `ShorePowerCapacity` and the port's `ShorePowerConnectionShare`, as with
  Gurobi; it could cover all port electrical demand. Results change where the
  cap binds (#364).
- Where a vessel's combined `ShorePowerCapacity` is below its electrical
  load in port, shore power is now also limited to the port's
  `ShorePowerConnectionShare` of the time in port, so results change there
  (#372).
- A `FLEXIBLE` `INTENSITY` `Regulation` with a numeric vessel threshold no
  longer crashes the run with a `ZeroDivisionError` when it regulates nothing
  of a policed vessel, as with `IntraFraction`, `InterFraction` and
  `ExtraFraction` all 0 (#376).
- A `Copy` of `ModelDefinition` or `BunkerOptions` is rejected with a deck
  error naming the line, instead of crashing with a `KeyError` (#382).
- A statement with an unknown node type, or a general node declared with a name,
  is rejected with a deck error naming the line in DEFINE or EVENTS, instead of
  crashing with a `KeyError` (#386).
- Plots of a quantity below one input unit, such as under 1 GJ or 1 MW,
  showed zero or empty axes, or a wrong unit, instead of scaling up to a
  smaller prefix (#389).
- With two Plot nodes rendering the unit-trading plot, the second one
  labelled its y-axis without the unit prefix, such as "units/year" instead
  of "thousand units/year" (#394).
- A deck with an `ETHANOL` fuel, converter or vessel no longer fails ten
  plots with `KeyError: <FuelTypeID.ETHANOL: 3>`, and ethanol consumption no
  longer drops out of the fuel-type consumption stack. The fuel-type
  supply/demand, pilot-fuel share and fuel-type consumption plots now show
  the fuel types a deck declares or uses, in the standard order, instead of
  a fixed list with empty panels or legend rows for the types it does not
  (#393).
- `ConverterEnergy` report requests with a `FIRST`, `SECOND` or `BOTH`
  reduction now reduce over the (vessel fuel type, fuel) key instead of
  failing or being ignored (#405).

## [1.0.0] - 2026-07-16

Initial public release of Navigate, an open-source sectoral integrated
assessment model for simulating transitions of the maritime industry.

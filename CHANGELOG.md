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

### Breaking
- Every row of a `Table` ends with a `;`, and the cells of a row are separated
  by commas as in a list: `"01-01-2024", 1.0;`. A row without the `;` runs
  into the next, a syntax error at the next row's first cell. The committed
  assumptions, examples and tutorials are converted.
- The default library has no `user` and `installation` branches: default
  nodes sit at `<data_dir>/defaults/<NodeType>/` and modules at
  `<data_dir>/modules/`. Move an assumptions folder of the old layout up one
  level. A user file overlaying a default is replaced by an `Import` and the
  reassignments in the deck, or by an own assumptions folder passed with `-d`.

### Added
- Results file: every run writes all its results to `<deck>.parquet` next to
  the deck, or to the path given with `-o`/`--results`: every profile result
  of the global profile and of each fleet, vessel, port, plant, producer,
  regulation and levy, one row per series and date, the values as 32-bit
  floats, with the unit of each result and the fuel and emission constants in
  the file metadata. [Lantern](https://github.com/zerocarbonshipping/lantern-zcs)
  opens it to plot the results in the browser; the built-in plots are kept
  for now. The layout is described on the new reference-manual page "Results
  file".
- Vessel report property `InFleet`: whether the vessel is part of its fleet.
- Report commands take a fourth argument, `CUMULATIVE`, which reports a
  property accumulated over the time steps up to and including each date under
  its name prefixed with `Cumulative`: `add_fleet_property("*", FuelConversions, NONE, CUMULATIVE)`.
- The console prints the number of logged warnings at the end of a run,
  pointing at the `.log` file.
- Vessel report properties `SpeedEnergyIntensitySaving`,
  `OperationalEnergyIntensitySaving`, `TechnologyEnergyIntensitySaving` and
  `EnergyIntensitySaving` on `add_vessel_property`: energy savings per
  cargo-mile, counting the transport work lost when a vessel slows down.
- Report properties `ShorePowerEnergy`, `ShorePowerExpenses` and
  `ShorePowerEmission` at vessel, fleet and global level.
- `set_speed` on a `Route` takes a `Curve` of the share of a leg's sea time
  at each speed, and on a `TRAMP` route `set_utilization` takes a `Curve` of
  the utilization at those speeds, for ballast and laden sailing (#491).
- The `Saving`, `RemedialUnits` and `LevyUnits` report properties can now be
  requested; they used to produce no column.

### Changed
- The deck is read in three phases - collect every file into declarations and
  events, resolve which declarations the simulation holds, build the nodes -
  instead of acting on each statement as it is read. Nothing moves in the
  committed decks' results, but a deck author sees:
  - `End` is accepted and ignored, dates in an `EVENTS` file need no order,
    and a node block under `EVENTS` must follow a `Start` or `Date` (one
    before any date is a deck error at its line).
  - a node declared but not used is removed before any value is assigned, so
    its values are not checked; a reference it makes is looked up in the
    default library like any other, but one found nowhere is not an error;
    the warning listing such nodes reads "declared but not used"; an
    `EVENTS` block targeting only unused nodes is dropped with a warning, and
    one naming a node the deck never declared is a deck error at its line
    when the deck is read.
  - a wildcard node reference such as `Fuels = Fuel("*")` expands over every
    node of the type in the simulation, those pulled from the default library
    included; wildcards match as `fnmatch` does, so `?` matches any one
    character and `[abc]` a character of a set.
  - a reference under `EVENTS` to a node the deck does not declare pulls it
    from the default library when the deck is read and works, instead of
    failing at the first time step; `Copy` and `Import` under `EVENTS`, a
    `Date` inside a library file, a new node name or a wildcard matching
    nothing under `EVENTS`, and a `DEFINE`-only attribute or command used
    under `EVENTS` are all deck errors when the deck is read.
  - a command argument that names a node found nowhere is a deck error even
    when a later command rewrites the entry; an assignment overwritten later
    in `DEFINE` still pulls nothing.
  - a calculator a `DEFINE`-only command holds stays fixed against `EVENTS`
    even when a later `DEFINE` command rewrites the same entry.
  - a `Copy` of a calculator takes the bounds of its own holders only, not
    those of the source's holders.
  - a node referencing itself, directly, through a wildcard or inside an
    expression, is a deck error at the line of the reference.
  - the four deck error classes are one, `DeckError`; syntax errors quote
    the line with a caret and name what was expected; a wrong number of
    command arguments is reported as Python states it, at the deck line;
    `'Fuel' is not an allowed keyword in section EVENTS` becomes the
    attribute's own "does not allow setting ... in 'EVENTS'" message.
  - statements no longer need a line each; `yyyy-mm-dd` dates are accepted
    wherever a date is, quoted or bare; `%name%` is no longer a token.
- `MinimumOfftakeDuration` (Producer) accepts any duration above 0 instead of
  at least 1; a duration under one year counts as one year.
- A calculator (`Variable`, `Forecast`, `Curve`, `Timetable`, `Surface`)
  assigned in `DEFINE` to an attribute or command that `EVENTS` cannot change
  cannot be changed in `EVENTS` either; re-assigning its attributes there is a
  deck error.
- The `Route` types `ROUND_TRIP` and `REGIONAL_TRIP` are now `LINER` and
  `TRAMP`, named after the calculation, not the market segment; the old names
  are a deck error (#491).
- A calculator or expression whose value reaches an attribute's exclusive
  minimum or maximum, such as a zero `Variable` as a Plant's `Capacity`, stops
  the run with an error naming the node instead of being clamped onto it.
- An empty `InitialSplit` (Fleet), or one summing to 0, is a deck error at its
  line. Omitting `InitialSplit` still gives a uniform split.
- `CAPEX`/`OPEX` are now `Capex`/`Opex`, and report properties end in
  `Wtt`/`Ttw`/`Wtw` (`TotalEquivalentWtt`). An old report property spelling
  is a deck error at its line.
- An undersized converter raises a `PowerCapacityError` naming the vessel,
  converter, leg (by its ports), sailing condition or port (by its name), and
  the required and installed power, instead of an LP infeasibility. The check
  is also tighter:
  - port electrical demand must fit the onboard electrical converter even
    where shore power is available;
  - it holds for each sailing condition on a leg, not their mean.
- Fleet and global energy savings are energy-intensity savings against the
  energy the year-0 raw intensity would need for the transport work
  performed. The `fleet_energy_saving` and `global_energy_saving` plots follow.
- On `add_property` and `add_fleet_property`, the `*EnergySaving` properties
  are now `*EnergyIntensitySaving` (they stay on `add_vessel_property`), and
  `SpeedEnergyIntensitySaving` is new.
- The 18 timing report properties (`TotalTime`, `ExpectedBuildTime`, ...) are
  now `ComputationalTime`, one column per phase in `TimingID`:
  - with `BOTH`, it gives each time step's own time, without initialization or
    reading events, where `TotalTime` was the running time since initialization;
  - the computational-performance plots group the time into these phases.
- Three wildcard uses are rejected at their line: a glob as a command
  argument, a glob on a single-valued attribute (`Route = Route("r_*")`), and
  a node listed beside a glob that also matches it.
- A `Route`'s inputs are checked per leg, and these stop the deck (#491):
  - a command key pair that is no leg of the route, or a required leg left
    unset; `set_voyage_distribution` is required on every `TRAMP` leg;
  - an input the route type does not read, such as `TimeAtSea` on a `LINER`;
  - a speed `Curve` whose shares do not sum to 1, a `LINER` sailing a leg
    twice, or an `EVENTS` change to the number of speeds on a leg.
- A smoothed price belief (flexibility cost, energy scarcity) ramps up when a
  price first appears after a stretch of exactly zero instead of taking it in
  full; `basecase_mid_regulation` moves by up to about 0.5% from 2030 (#25).
- Nodes that no chain of references connects to a top-level node are removed
  after `DEFINE`, with one aggregated warning. As a result:
  - a `Port` counts only through a `Route`'s `Ports`, not a `Jurisdiction`;
  - `EVENTS` statements targeting only removed nodes are dropped;
  - a command naming a removed node fails with a hint naming it;
  - an incompletely configured unused node no longer errors.
- On a `TRAMP` `Route`, the share set with `set_voyage_distribution`
  is the share of the sea miles sailed between the two ports, no longer of the
  sailing time. Results are unchanged where all legs sail the same conditions.
- Technology `Capex`/`Opex` enters the vessel cost metrics, so newbuild choice
  shifts. `TechnologyExpenses` replaces the never-populated
  `TechnologyNewbuildExpenses` and `TechnologyRetrofitExpenses`.
- Shore power is counted in `TotalConsumedEnergy`, `TotalFuelExpenses` and
  the `TotalEquivalentWtw` emissions, and so in the expense and Wtw plots.
- Fuel-conversion expenses are levelized exactly at the destination vessel's
  cost of capital and booked per service year. The old factor overstated them
  (about 21% at a 5-year window and 8% discount rate).
- The fuel-conversion business case compares the two vessel types' fuel costs
  over their common remaining-lifetime window.
- Rescaling `InitialSplit` by more than 1% is logged as a warning, so it
  counts in the end-of-run summary.
- A `Report` property request that matches no node logs a warning instead of
  silently producing no columns.
- The warning about a missing `TechnologyCostOfCapital` is removed; the
  fallback to the vessel's cost of capital is documented on the attribute.
- The fuel-conversion warning about differing installed power is logged once
  per vessel pair, and the fleet reference speed at a step with no vessels is
  NaN.
- The `.log` file is written in UTF-8, with convergence tables to three
  significant figures. Its summary comes after the plots, counts their records
  and how often each unique warning was logged, under `navigate.app.logs`.
- The command line logs its records, such as the fatal-error line, under
  `navigate.app.cli` instead of `navigate.__main__` (`__main__` under
  `python -m navigate`).
- An attribute's bounds reach the calculator it references when the
  assignment is read, so the calculator keeps them if the attribute is
  re-assigned later in `DEFINE`, as it always did across `EVENTS`.
- The minimum supported Python version is 3.13 (was 3.12).
- The 8 default bulk-carrier and tanker routes merge ballast and laden into one
  utilization per speed. At equal speeds energy and cargo miles hold, but a
  merged bin's lowest sailable speed shifts, nudging results slightly (#491).
- A regulation's default fuel WTT averages over every port on the vessel's
  route, each once, not only the jurisdiction ports, where it was 0 without
  supply. Results move where a route leaves the jurisdiction.
- A `Regulation`'s or `Levy`'s default fuel WTT is the plain mean, over every
  plant defined for the fuel, of its investment-time plus delivery WTT, not
  the port supply mix or installed plants; route ports weigh equally.
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
- A deck that leaves a required attribute unassigned now stops with a one-line
  `Error:` message naming the node and the attribute, instead of a Python
  traceback.
- In the `.log` file:
  - an `Initialize model before start of simulation` heading opens the time
    steps, and the first time step's heading follows it, reading
    `Time-step: 0, current date: …` like every later one;
  - the time-step headings and the completion line log under
    `navigate.driver.run`, the initialization and post-processing headings
    under `navigate.simulation.time_stepping`;
  - the model's modules log under `navigate.simulation.<domain>.<module>`,
    such as `navigate.simulation.bunker.solver`.
- A path written with `./` or a doubled `/` in an `Include` or a report
  `Directory` now appears normalised in error and log messages, such as
  `/deck/includes/x.inc` instead of `/deck/./includes/x.inc`.
- An empty `Vessels`, `Plants`, `Tanks`, `Ports`, `Emissions` or `Fuels` list,
  or a fuel type repeated in `MainFuelTypes` or `PilotFuelTypes`, is rejected
  at its line, also on a node the deck does not use.
- With the HiGHS solver, runs with an `INDIVIDUAL` or `FLEXIBLE` `Regulation`
  are several times faster. Results change where the bunkering optimum is not
  unique, by up to several percent late in a long run (#32).
- The report property `FuelTypeDemand` is now `FuelTypeCapacity`, and the
  `fuel_type_supply_demand` plot labels that line "Fleet capacity" instead of
  "Demand" (#522).
- The log line for inertia newbuilds held back by the newbuild limit reads
  `<fleet>: Deferred inertia newbuilds due to newbuild limit (N% delivered).`
  like the orderbook deferral lines, instead of `Inertia not fully applied
  due to newbuild limit`.
- The VS Code extension is downloaded from the getting-started page of the
  documentation instead of taken from the checkout.
- The errors for a bad deck path or `-d` folder now read `argument PATH: file
  not found: '...'`, `argument PATH: a directory, not a file: '...'`, `argument
  PATH: must have a '.nav' extension: '...'` and `argument -d/--data-dir:
  folder not found: '...'`.
- The error for a `Process` whose `Feeds` and `Conversions` differ in length
  names the process and reads `The length of Feeds (n) and Conversions (m)
  must correspond.`

### Removed
- Wildcards in enum arguments and enum lists, such as `set_slip_fraction(M*, 0.03)`
  or `MainFuelTypes = *`: name each member. An unquoted `*` is a syntax error.
- Wildcard `Import`, such as `Import Converter "electrical_*"`: import each
  node by name.
- `BunkerLogistics`: write `LiquidMarket` on `Fuel`, and `set_fuel_transport`
  and `set_fuel_distance` on `Plant`, priced at the region's
  `set_transport_cost`/`set_transport_wtt`. The examples lose their flat
  transport costs.
- The `PowerSystem` node: write its converters on the `Vessel` as three
  distinct `PropulsionConverter`, `ElectricalConverter` and `HeatConverter`,
  and add its `Capex` and `Opex` to the vessel's `Capex` and `Opex`. Its
  `Lifetime` and `Replacement` have no counterpart: that cost now lasts the
  vessel's lifetime.
- The `-e`/`--export-assumptions` CLI flag.
- The `-r`/`--replot` CLI flag and the `plot_data.pkl` file every run wrote;
  rerun the deck to regenerate the plots.
- The `SharedThreshold` attribute of `Regulation`; write
  `set_vessel_threshold("*", <value>)`. The `SharedThreshold` report property
  remains, as the fleet-level effective target of a `FLEXIBLE` regulation.
- The `CumulativeIntensityEquivalent*` and
  `CumulativeIntensityTotalEquivalent*` report properties.
- Report properties that are a reduction, accumulation or unit conversion of
  another one; they are no longer in the results file either:
  - every `Cumulative*` property: add the property with `CUMULATIVE`, e.g.
    `add_property(FuelExpenses, NONE, CUMULATIVE)`; its value at a date now
    includes the time step ending at that date;
  - `TotalEquivalentWtt`, `TotalEquivalentTtw`, `TotalLevyExpenses`,
    `TotalEnergyPort`, `TotalEquivalentBunkerWtt` and plant
    `TotalEquivalent*Wtt`: add the property without `Total` with `BOTH`;
  - the per-key `IntensityEquivalentWtt`, `IntensityEquivalentTtw` and
    `IntensityEquivalentWtw`; the `IntensityTotalEquivalent*` totals remain;
  - port `BunkerIntensityPrice`, `BunkerIntensityWtt`,
    `BunkerIntensityEquivalentWtt` and `BunkerIntensityTotalEquivalentWtt`,
    and plant `*IntensityCost` and `IntensityEquivalent*Wtt`: report the
    per-ton property (`BunkerPrice`, `BunkerWtt`, `EquivalentBunkerWtt`,
    `InvestmentCost`, `EquivalentInvestmentWtt`, ...) and divide by the
    fuel's heating value, which the results file metadata lists with the
    fuel each plant produces.
- Unused profile report properties:
  - volume-denominated output, FuelType mass aggregation, fuel-quantity
    cumulatives and non-GWP-equivalent emission variants;
  - plant Ttw/Wtw and capacity, production and feed output;
  - producer capacity, pipeline and source output;
  - vessel Opex and activity output, policy emission factors, port bunker
    Wtw, fleet scrap-age statistics and the levy level.
- The `producer_changes` plot.
- The list attributes of `Route`; write the command keyed by the leg's
  origin and destination ports instead (#491):
  - `Speeds`: `set_speed`, and `ConditionDistribution`: a speed `Curve`;
  - `CapacityUtilizations`: `set_utilization`, `Distances`: `set_distance`;
  - `PortDurations`: `set_port_duration`, the days at the leg's destination;
  - `PortCalls`: `set_port_calls`, keyed by one port.
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
- An unbounded bunkering LP, or a solve that stops at a limit, now stops the run
  with an error naming the bunkering scope, instead of a `RecursionError` on
  HiGHS or a silent continuation on Gurobi (#368).
- The `--help` text and the README no longer say `-p` silences other console
  output or that `-s` leaves Excel reports; reports keep their own format
  (#444).
- An expression that references a `Curve`, given to a `Route` leg by `set_speed`
  or `set_utilization`, is now refused before the run starts, with an error that
  names the route and the leg, instead of crashing at the first time step (#727).
- The `--help` text and the README named `auto` as the default of `--solver`;
  without the flag, the deck's `BunkerOptions` `Solver` applies.
- A dearer vessel type no longer lowers its fuel type's newbuild share unless the
  `set_newbuild_limit` of a cheaper vessel type of that fuel type binds, nor a
  dearer plant its fuel's plant uptake: each is valued by its cheapest option (#653).
- A `set_newbuild_limit` that is not reached no longer lowers the vessel type's
  newbuild share, and one that is reached caps the share at the limit instead of
  below it, where a fuel type has more than one vessel type in the fleet (#654).
- The VS Code extension in `syntax/vscode/` highlights the current node types:
  `Plot` and `Technology` are highlighted, and names that are no longer node
  types are not (#608).
- The producer's expected feed consumption, and hence its feed-constrained
  build-out, was overstated further into the horizon; each year now counts
  only the feed of a plant invested in that year (#587).
- A producer's `Development` at the first date counts the existing pipeline
  of every plant, not only of the last plant with a pipeline.
- The warning for a plant of zero capacity states the initial capacity it
  could not initialize.
- A fleet whose vessels differ in `Lifetime` no longer stops with a
  `ValueError` once it has `Technologies`. Technology costs are amortized over
  each vessel's own lifetime, or the years left for a retrofit, so a
  replacement outlasting them is charged only in part (#546).
- `set_power_transfer` (Technology) accepts a transfer above 1 MW; the value
  is a power in MW and was capped at 1.
- `--solver auto` no longer fails with a traceback (#402).
- The `computational_performance_cumulative` plot no longer weights each time
  step's computational time by the step's length in years.
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
  - the `InitialSplit` rescale is proportional, not by equal fractions, and
    is logged above a 1% deviation;
  - the `BunkerOptions` defaults, `Threads` type and exclusive minimums;
  - `Converter` `MinimumLoad`, `Efficiency` and `set_consumption_ttw` take no
    `Forecast`, and `PowerCapacity` takes a `Variable`;
  - `set_voyage_distribution` on `Route` takes no `Forecast`;
  - the port properties are `EquivalentBunkerWtt` and
    `TotalEquivalentBunkerWtt`;
  - `set_include_vessel` on Levy and Regulation defaults to FALSE, so a vessel
    is only covered once included;
  - defaults that differed from the code: `Threads` 0, `MaximumRampUp` 1,
    `JumpStartFraction` 0.1, the Region WTT commands 0, and
    `EmissionsLifetime` on a policy falls back to the ModelDefinition's;
  - `Dependency` (Source), `Efficiency` (Converter), `LowerHeatingValue`,
    `MassDensity`, `Source` (Plant) and `MaximumDevelopment` are marked as
    required;
  - minimums that exclude 0 read `>0`, and missing minimums and maximums are
    added;
  - `ShorePowerCapacity` and `NominalCapacity` take no `Forecast`, Region
    `set_source_capex` and `set_source_opex` take no `Timetable`, and
    `Tank` `Size` and `InitialVessels` take a `Variable`;
  - `Orderbooks` is a cumulative count, `set_newbuild_limit` caps yearly
    newbuilds as a fraction of the fleet's vessel count, and ports on a
    `TRAMP` must be unique;
  - `set_process_opex` (Region) accepts negative values, and
    `MaximumRampUp` and `set_existing_pipeline` (Producer) have the right
    units;
  - the calculator pages show how `Addition`, `Multiplier` and the bounds
    combine, and which attributes take an expression or `INF`;
  - commands that accept wildcards and commands allowed only in `DEFINE`
    say so;
  - `TechnologyHorizon` (Fleet) shapes retrofits as well as newbuilds,
    `JumpStartFraction` (Producer) blends into the expected uptake in every
    time-step, and `SolutionTolerance` is also the LP solver's tolerance;
  - a Plant's `Fuel` must not be a liquid-market fuel, a Fleet's `Vessels`
    must be unique, and an inactive Levy or Regulation is ignored.
- Deck errors that ended in a Python traceback, named no deck line or were
  badly worded now read as located deck errors:
  - a rejected attribute or command value prints the one-line error and
    exits 1;
  - a node declared, imported or copied under a name already in use;
  - a reference whose type is not a node type, such as `Foo("x")`;
  - default files that import or copy each other in a cycle;
  - a wildcard that matches nothing, or stands where one node is expected;
  - a default file that does not yield the requested node;
  - a node found in neither the deck nor the defaults, which opened with a
    bare colon;
  - a value of a kind the attribute does not take, including a table or an
    enum token in a scalar slot (`Capex = FLAT`);
  - a wrong kind on a boolean, ID or ID-list attribute (`Active = [1.0]`);
  - an integer or boolean in a scalar slot, named by kind;
  - a non-number in `InitialSplit`;
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
- Setting `Active = FALSE` on a `Regulation` in `EVENTS` no longer stops the
  run with a `KeyError`; the regulation stops applying from that step (#496).
- `set_bunkering_cost` is rejected on a `Port` at its line instead of failing
  the run; use `set_handling_cost`.
- The CLI rejects a deck path whose name is only dots before `.nav`.
- The bounds an attribute imposes reach a calculator matched by a wildcard,
  as they did for one written by name.
- A wildcard matches its other characters literally; only `*` and `?` are
  wildcards, so `a.b` no longer matches `aXb`.
- On HiGHS, an infeasible bunkering problem writes both
  `bunkering_infeasible.ilp` and `bunkering_infeasible.lp`, with the model's
  own constraint and variable names instead of `r0` and `c0` (#466).
- An `INF` entry in `InitialSplit`, or entries whose sum overflows, stop the
  deck at its line instead of yielding NaN.
- `set_operational_saving_port` takes only `ELECTRICAL` and `HEAT`: an
  explicit `PROPULSION` is a deck error instead of a silently unread entry.
- `set_operational_saving_port` names the demands it accepts when it rejects
  a key: `only allows assignment of ELECTRICAL, HEAT, but got X`.
- `set_initial_technology_share` values built from expressions are honored
  instead of being ignored.
- The warning count at the end of a run no longer counts a repeated
  consistency warning once more after the last time step.
- `set_fuel_wtt`, `set_fuel_ttw` and `set_global_warming_potential` on a
  `Levy` or `Regulation` hold beyond the first time step. Results change for
  decks using them, including `simulations/examples/example_1`.
- The bunker LP's regulation coefficients reset every time step, so entries
  of vessels that left a fleet no longer leak into later steps.
- The LP is built in the same order on every run, so dual values no longer
  vary between runs in degenerate solves.
- On a `TRAMP` `Route` with unequal shares in a port pair's two
  directions, each direction's sea energy demand sat on the opposite leg in the
  bunker optimisation; decks with such shares (`business_as_usual`) shift.
- Fuel-conversion expenses are booked on the elapsed-years axis, so
  calendar-date timelines no longer drop or distort the conversion year.
- With sub-year time steps, the fuel-conversion business case no longer
  prorates a year twice.
- The expected fuel-delivery cost from plant to port is levelized against the
  plant's production over its operating years, as the production cost is.
  Results change for decks assigning `FuelTransport`.
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
- A wildcard node declaration whose `InitialSplit` is rescaled logs the
  rescale for every matched node, not just the first.
- The fuel-conversion proposal walk skips an increment with no eligible
  destination instead of stopping there.
- Fuel conversion's supply limit counts a port's supply once however often a
  route calls there, and each vessel's share as the bunkering allocates it;
  results change where a route repeats a port or port supply is short (#520).
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
- A sailing condition with a zero share of its leg's sea time no longer sets
  a vessel's minimum or maximum speed, nor makes its energy NaN under a
  technology with a power transfer.
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
- The completion line in the `.log` file no longer reads "in elapsed time:
  ... seconds" (#404).
- A simulation whose timeline includes 1970-01-01 now runs past that date
  instead of stopping there (#403).
- `ConverterEnergy` report requests with a `FIRST`, `SECOND` or `BOTH`
  reduction now reduce over the (vessel fuel type, fuel) key instead of
  failing or being ignored (#405).
- `NominalCapacity` (Vessel), `RetrofitFrequency` (Fleet), `TimeAtSea` (Route)
  and `set_process_lifetime` (Region) must now be above 0; a 0 used to crash or
  hang the run or give invalid results.
- `PlantTiedCapital` no longer repeats the capital tied up by the plants
  invested in the last time step for every investment time; each time step
  now reports its own plant capital (#588).
- The editor grammars in `syntax/` no longer highlight `Array`, which is not a
  DSL keyword (#614).
- An infeasible bunkering problem on HiGHS now names its limiting constraints,
  or says they could not be identified, instead of listing none (#465).

## [1.0.0] - 2026-07-16

Initial public release of Navigate, an open-source sectoral integrated
assessment model for simulating transitions of the maritime industry.

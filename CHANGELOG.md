<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- The regulation spend coefficient, shore-power regulation coefficient, and
  regulation measure containers of the bunker algorithm are now reset at
  every time-step like the other dynamic policy coefficients; the reset
  previously targeted an unused attribute, so entries of vessels that left
  the fleet could leak into later time-steps.
- LP variable and constraint creation order for in-port energy demands is now
  deterministic across runs: the electrical/heat demand set is an ordered
  tuple instead of a `set`, whose iteration order varied between interpreter
  processes. The LP itself was unaffected, but row/column order could select
  a different (equally valid) optimal basis in degenerate solves, making
  order-sensitive outputs such as dual values vary run-to-run.
- The `Converter` reference-manual page and docstrings no longer show
  `Forecast` references for `MinimumLoad`, `Efficiency`, and
  `set_consumption_ttw`: the code accepts only floats and `Variable`
  references there, and the documented `Forecast("name")` assignment raises
  a `ValueError`. `PowerCapacity` gains the opposite correction — it accepts
  `Variable` references but was documented as `Float` only.

### Changed
- Internal Python identifiers containing uppercase acronyms are now
  lowercase (`set_capex`, `get_total_equivalent_wtt`, formerly `set_CAPEX`,
  `get_total_equivalent_WTT`). The DSL surface is unchanged: decks keep
  writing `CAPEX`, `Scope = WTT`, and Report properties such as
  `TotalEquivalentWTT`.
- The converter power-capacity check moved out of the bunker LP into a
  per-time-step fleet validation. The LP rows were redundant: the
  energy-conservation equalities fix each row's left-hand side, so a row
  either held for every solution or made the LP infeasible. Undersized
  converters now raise a `PowerCapacityError` naming the vessel, converter,
  leg or port, and the required versus installed power, instead of an LP
  infeasibility with an IIS dump. Two behavior tightenings follow:
  - **Breaking**: port electrical demand must fit the onboard electrical
    converter; previously, when shore power was available, the LP forced a
    shore-power purchase to cover the shortfall instead of failing.
  - **Breaking**: on regional routes the check holds per condition leg;
    the LP row only constrained the sailing-fraction-weighted mean, which
    could mask an overload at the fastest sea condition.
- **Breaking**: the `Propulsion`, `Electrical`, and `Heat` attributes of a
  `PowerSystem` must reference three distinct converters; initialization now
  fails otherwise. A converter shared across the slots of one power system
  was never exercised by any committed deck and would be double-counted
  wherever the converters are summed (installed power, cost, fuel demand).
  Reusing a converter across different power systems remains supported.
- Internal refactor of the bunker constraint builders (no result changes):
  a shared get-or-create constraint helper in
  `navigate/bunker/_build.py`, converter-fuel maps precomputed
  once per algorithm instance instead of rebuilt per builder call,
  uniform re-apply-every-build coefficient semantics, and docstrings stating
  the constraints' mathematical form.
- Internal refactor of the remaining bunker constraint builders (no result
  changes): energy-conservation rows built by explicit per-demand calls
  (propulsion/electrical/heat at sea, electrical/heat in port), extracted
  pilot-fuel and power-capacity coefficient helpers, named regulation term
  construction, docstrings completing the constraints' mathematical
  documentation, and the leg intra/inter/extra jurisdiction classification
  shared as `navigate.policy.leg_jurisdiction_fraction`.
- Internal refactor of the bunker variable builders (no result changes): the
  add-if-absent variable idiom shared as a helper next to the constraint
  helper in `navigate/bunker/_build.py` (moved from
  `navigate/bunker/constraints/_common.py`).

### Removed
- **Breaking** for code importing navigate as a library: the remaining
  node-class getters are replaced by direct attribute access (CODESTYLE.md,
  Class variables) — the keyed dict getters on `Region` (13, backing dicts
  now public), `Port` (4), `Plant` (2), `Technology` (3), `Fuel.get_TTW`,
  `Converter.get_slip_fraction`/`get_consumption_TTW`, and
  `Regulation.get_vessel_threshold` become direct dict indexing;
  `Source.get_dependency` becomes a public `dependency` attribute;
  `Fleet.get_vessels`/`get_operational_saving_sea`/`get_operational_saving_port`
  and `Producer.get_plants`/`get_fuels` are read via the public
  `vessels`/`plants`/`fuels` names; the table and calculator accessors
  (`get_x`/`get_y`/`get_x_min`/`get_x_max`/`get_extrapolate`/`get_bounds`/
  `get_addition`/`get_multiplier`) become public
  `x`/`y`/`extrapolate`/`lower_bound`/`upper_bound`/`addition`/`multiplier`
  attributes. `Converter.get_slip_fraction`'s missing-key fallback was
  unreachable through the parser (the dict is seeded for every fuel type
  before deck commands run), so direct indexing behaves identically; for
  library callers, an unknown fuel type now raises `KeyError` instead of
  returning zero.
- **Breaking** for code importing navigate as a library: `Node.get_name()`/
  `get_type()` and `NodeReference.get_name()`/`get_type()` are replaced by
  direct attribute access (CODESTYLE.md, Class variables) — `name` was
  already public, and the internal `_type` is now public `type` on both
  classes. `CommandReferenceMixin.get_command_references()` is likewise
  replaced by a public `command_references` attribute (`add_`/`clear_`
  mutators unchanged). Nodes inside `plot_data.pkl` carry the renamed
  attribute, so the pickle incompatibility with earlier versions noted
  below extends to this change.
- **Breaking** for code importing navigate as a library: trivial getters on
  the helper classes are replaced by direct attribute access
  (CODESTYLE.md, Class variables) — `SimulationManager.get_timeline`/
  `get_dateline`/`get_name` (now plain `timeline`/`dateline`/`name`, and
  `_parser` is now public `parser`), `Parser.get_model_definition`/
  `get_dates`/`get_deck_directory`/`get_deck_name` (now `dates`/
  `deck_directory`/`deck_name`), `PlotData.get_dateline`/`get_timeline`/
  `get_deck_directory`/`get_plot_configs`, `Plot`'s internal
  `_directory`/`_selected_plots` (now public), `BunkerAlgorithm.get_build_time`/
  `get_solve_time`/`get_transfer_time`, all six `BunkerOptions` getters,
  `ModelDefinition.get_start_date`/`get_emissions_lifetime`,
  `CommandReference.get_command`, `Event.get_stmts`,
  `Expression.get_node_references`/`set_node_references` (now plain
  `node_references`), and the `Package.cost_flow` read-only property (now a
  plain attribute). `Expression`'s attribute-reference consistency check was
  deleted outright: its backing list was never populated, so the check never
  ran. `plot_data.pkl` files saved by earlier versions cannot be loaded with
  `--replot` by this version — replot old results with the version that
  produced them.
- **Breaking** for code importing navigate as a library: unused accessor
  methods with no callers in the codebase —
  `Forecast.get_x_date`, `Timetable.get_x_date`,
  `_Table1D.get_y_min`/`get_y_max`, `_Table2D.get_y_min`/`get_y_max`,
  `_Calculator.get_internal_lower_bound`/`get_internal_upper_bound`,
  `Fleet.get_multiplier_increments`/`get_fuel_conversion_cost_pairs`,
  `_Policy.get_global_warming_potential` (the expectation-level method
  remains), `Parser.get_bunker_logistics`/`get_bunker_options`,
  `CommandReference.get_inputs`,
  `SimulationManager.get_time`/`get_date`/`get_parser`, and
  `Package.get_component` — along with backing state that only those
  accessors read (`Forecast`/`Timetable._x_date`, `Package._component`
  with its `set_component` and pickling special-case).
- **Breaking**: the Excel assumptions export — the `-e`/`--export-assumptions`
  CLI flag, `SimulationManager.export_assumptions`,
  `navigate/output/assumptions.py`, and the parser's assumption-update
  tracking. Assumptions should not pass through the simulation model to be
  re-serialized, and the export reflected only a deterministic run — not
  scenario or uncertainty assumptions. Readable assumption views will be
  produced upstream of Navigate, without running a simulation.
- The cumulative-intensity emission output of fuel-consumer profiles: the
  `CumulativeIntensityEquivalent{WTT,TTW,WTW}` and
  `CumulativeIntensityTotalEquivalent{WTT,TTW,WTW}` report properties and
  their profile getters. No committed deck or plot consumed them.
- **Breaking**: the `SharedThreshold` attribute of `Regulation`.
  `set_vessel_threshold` is the only threshold source; migrate with
  `set_vessel_threshold("*", <value>)`, which assigns the same threshold to
  every vessel. Every vessel included in a regulation now requires a
  threshold, for all schemes and measures. Under `Scheme = FLEXIBLE` the
  per-vessel thresholds pool into the fleet-level constraint, so a fleet-total
  ABSOLUTE cap distributed by dynamic fair share is no longer expressible; the
  fair-share threshold machinery is removed with it. The `SharedThreshold`
  report property remains but is now the derived fleet-level effective target
  of a FLEXIBLE regulation (identical to the input value for uniform,
  wildcard-assigned thresholds).
- Unused profile output (getters, their writers, and stored state) across all
  profile classes: volume-denominated output, FuelType mass aggregation,
  fuel-quantity cumulatives, non-GWP-equivalent emission variants,
  plant TTW/WTW and capacity/production/feed output, producer
  capacity/pipeline/source output and per-plant change tracking, vessel
  OPEX/activity output, policy emission factors, port bunker WTW, fleet
  scrap-age statistics, and the levy level. The corresponding report
  properties are removed from the Report DSL surface (see
  `docs/reference_manual/report.md`).
- The `producer_changes` plot.
- The debug plots `fuel_supply_demand_expectation`, `fleet_newbuild_sources`,
  `fleet_fuel_conversion_sources`(`_normalized`), and
  `technology_install_sources`(`_normalized`), together with the profile
  output only they consumed — including the never-populated fleet limit
  series, the demand/supply expectation records, and the
  `InertiaNewbuilds`/`ModelledNewbuilds` report properties. The limit
  behavior they were meant to visualize is asserted by unit tests instead.
- The expectation-belief fan from the `regulation_flexibility_cost` plot and
  the flexibility-cost belief series on the regulation profile.
- The `fleet_orderbook` plot and the per-source fleet report properties
  `PrimaryScrap`, `SecondaryScrap`, and `OrderbookNewbuilds`; the aggregate
  `Scrap` and `Newbuilds` properties remain.
- The never-populated emission-storage expenses: the fuel-consumer profile
  member, the report properties `EmissionExpenses`, `TotalEmissionExpenses`,
  and `CumulativeEmissionExpenses`, and the always-zero "Emission storage"
  layer of the `global_expenses` plot. The fuel-related expense totals lose
  only a zero addend.
- Emission offsetting: the DSL attributes `EnableOffsetting` and
  `OffsettingCost` (ModelDefinition), `AllowOffsetting` (Regulation and
  Levy), and `OffsetThreshold` (Regulation), the offsetting step of the
  simulation loop, the offset capping of expected compliance costs and of
  threshold adjustment, the offset series on profiles, the
  `regulation_offsetting_units`/`_expenses`/`_cost` plots, and the
  offset lines and bands of the emission and compliance plots. Offsetting
  is not relevant to the model; the emission output now shows residual
  emissions.

### Changed
- Internal simplification (no DSL or result changes): `BunkerAlgorithm` no
  longer mirrors per-vessel node data in scratch containers (converters,
  usable fuels, converter fuels, port/leg indices, efficiencies, port-name
  indices) — the LP builders and transfers read the vessel nodes directly,
  via shared helpers in `navigate/bunker/utils.py`; only the effective-LHV
  values remain pre-computed. Leg-index enumeration is now
  `Route.get_leg_indices()`, also replacing the duplicate in
  `navigate/policy/jurisdiction.py`. `navigate/bunker/vessel_setup.py` →
  `coefficients.py`: the module now computes only LP coefficients
  (effective LHV, emission factors, regulation and levy coefficients).
- Internal reorganization (no DSL or result changes): the remaining
  top-level modules regroup into two domain packages over shared layers.
  `navigate/fleet/` merges `vessel/`, `route/` operation and speed, and
  `vessel/fleet/`; `navigate/fuel/` absorbs `fuel/producer/` and
  `route/import_export.py` (renamed `port_supply.py`);
  `navigate/economics/` is the generic cash-flow/metric/discrete-choice
  toolkit formerly `investment/`; `illustrations/` becomes
  `navigate/output/plots/`; `output/logger.py` becomes top-level
  `logging_.py`; `manager.py` becomes `simulation.py`;
  `vessel/fair_share_fuel.py` becomes `bunker/supply_allocation.py`. The
  `vessel/`, `route/`, `investment/` and `illustrations/` packages are
  removed; `util.py` is split into a `util/` package (`collections`,
  `numeric`, `dates`, `naming`) and the shared constants (`TOLERANCE`,
  `ROUND_OFF`, `DAY`, `MONTH`, `YEAR`) move from `navigate.core.misc` into
  it. Most `navigate.util` names are re-exported unchanged, but
  `round_for_display`, `get_attributes`, `get_files_in_directory` and
  `print_elapsed_time` became private helpers of their single consumers and
  the unused `average` is deleted. Breaking for
  code importing navigate as a library. Regulation flexibility-cost belief
  smoothing lives in `navigate/policy/flexibility_beliefs.py` (the belief
  itself is regulation-owned state; vessels only receive the derived
  expenses), separate from the vessel scarcity beliefs in
  `navigate/fleet/scarcity_beliefs.py`, and the missing-technology
  approximation moves from the simulation loop into
  `navigate/fleet/technology_adoption.py`.
  As with the
  previous reorganization, `plot_data.pkl` files saved by earlier versions
  cannot be loaded with `--replot` by this version — replot old results
  with the version that produced them.
- Internal reorganization (no DSL or result changes): `navigate/core/misc.py`
  is dissolved — the `EMPTY_*` sentinel arrays move to
  `navigate/core/initial_values.py`, and `SECTION_*`, `BOOL_ID` and
  `BOUNDS_MAP` move into their consumers (`parser/_keywords.py`,
  `core/assign.py`, `core/nodes/_calculator.py`). `navigate/core/time_.py`
  is likewise dissolved: `calculate_inertia` and `calculate_compound_growth`
  join the shared numeric helpers in `navigate/util/numeric.py` and are
  re-exported from `navigate.util` instead of `navigate.core`. The root
  `Node` base class moves from `navigate/core/nodes/node.py` to
  `navigate/core/node.py`, beside `node_reference.py` and
  `node_registry.py` — every non-underscored file in `core/nodes/` is now
  a DSL keyword.
- Internal renames for descriptive module names (no DSL or result
  changes): in `navigate/fleet/`, `beliefs.py` → `scarcity_beliefs.py`,
  `heuristic.py` → `marginal_saving.py`, `saving.py` →
  `residual_energy.py` and `technology.py` → `technology_adoption.py`
  (dropping the node-file/domain-module same-name convention, which had
  no other instance); `navigate/policy/coefficient.py` →
  `emission_coefficient.py`; in `navigate/bunker/`, `helpers.py` →
  `utils.py` (matching the `fleet`/`fuel` convention),
  `constraints/regulation_helpers.py` → `regulation_terms.py`, and the
  `transfer/regulations_*.py` trio → `regulation_*.py`, singularizing
  their `transfer_regulations_*` functions with them.
- Internal reorganization (no DSL or result changes): calculation logic
  moved out of the node classes into sibling modules; all node classes
  moved into `navigate/core/nodes/` and all general-node classes into
  `navigate/core/general_nodes/`, with package-private bases
  underscore-prefixed in module and class name (`_GeneralNode`, `_Machinery`,
  `_Policy`, `_Calculator`, `_Table1D`, `_Table2D`, `_AssetManager`) and the
  cross-package foundational types (`Node`, `Increment`, `TableData`)
  public; the `navigate/asset/` and `navigate/calculator/` packages are
  removed. Because pickled objects reference their defining
  module, `plot_data.pkl` files saved by earlier versions cannot be loaded
  with `--replot` by this version — replot old results with the version
  that produced them.
- Technology CAPEX/OPEX now enters the vessel cost metrics. Every install
  event (newbuild bundle, retrofit, seeded initial uptake) is levelized at
  the vessel cost of capital over the window it serves — the full lifetime
  for newbuilds and initial uptake, the remaining lifetime for retrofits —
  and carried on the age cohort as a constant USD/year charge. The
  fleet-average carried charge is added to the investment freight rate and
  cargo charter rate (matching the fleet-average uptake the fuel expenses
  reflect) and, as a realized yearly series, to the post-processed
  instantaneous freight rate. The asset charter rate and CAPEX NPV remain
  hull-and-machinery only. Adoption decisions are unchanged (still
  discounted at `TechnologyCostOfCapital`). Newbuild vessel choice shifts
  accordingly, since the freight rate is its decision metric. The
  never-populated `TechnologyNewbuildExpenses`/`TechnologyRetrofitExpenses`
  report properties (and their cumulatives) are replaced by a live
  `TechnologyExpenses`/`CumulativeTechnologyExpenses` pair — the
  multiplier-weighted carried charge, the levelized analogue of
  `VesselExpenses` — which now also feeds `VesselRelatedExpenses`,
  `Expenses`, and a single Technology band in the `global_expenses` plot.
- **Breaking**: the fleet- and global-level energy-saving metrics are
  redefined as energy-intensity savings against a counterfactual baseline —
  the energy the year-0 raw intensity (year-0 speed, no operational measures,
  no technologies) would require to perform the transport work actually
  performed. This replaces the vessel-count-weighted average of per-vessel
  intensities scaled by initial trade, which under-weighted the vessel types
  performing most of the transport work and froze cross-fleet weights at
  year-0 trade. The `add_property`/`add_fleet_property` report properties
  `OperationalEnergySaving`, `TechnologyEnergySaving`, and `EnergySaving`
  become `OperationalEnergyIntensitySaving`, `TechnologyEnergyIntensitySaving`,
  and `EnergyIntensitySaving` (the old names remain valid on
  `add_vessel_property`, where they are absolute vessel-energy savings), and
  `SpeedEnergyIntensitySaving` is newly exposed. The `fleet_energy_saving`
  and `global_energy_saving` plots show the redefined metrics.
- The investment post-processing and fleet aggregation read vessel
  cargo-miles from the expectation instead of the profile (value-identical).
- Shore power is now part of the fuel-consumer accounting: its energy is
  included in `TotalConsumedEnergy`, its cost in `TotalFuelExpenses` (and
  transitively the fuel-related expense totals, the expense plots, and the
  investment post-processing cash flows), and its emissions in the
  `TotalEquivalentWTW` family. The three shore power series propagate from
  vessel to fleet to global level, so the WTW emission plots and the new
  fleet/global-level report properties include shore power. The WTT/TTW
  intensity totals keep fuel-only numerators over the shore-inclusive energy
  denominator, since shore power has no well-to-tank or tank-to-wake
  component.
- The fleet profile stores scrap and newbuilds as single per-vessel
  aggregates instead of per-source arrays (value-identical; the evolution
  code still computes the sources separately).

### Added
- Vessel-level energy-intensity savings (`SpeedEnergyIntensitySaving`,
  `OperationalEnergyIntensitySaving`, `TechnologyEnergyIntensitySaving`,
  `EnergyIntensitySaving` on `add_vessel_property`): per-cargo-mile
  counterparts of the absolute vessel-energy savings, accounting for the
  transport work lost when a vessel slows down. The technology variant
  equals its absolute counterpart, since cargo-miles cancel in that ratio.
  Vessel and fleet profiles store the transport work performed
  (cargo-miles) to support them.
- Report properties `ShorePowerEnergy`, `ShorePowerExpenses`, and
  `ShorePowerEmission`, available at vessel, fleet, and global level.
- Behavior guardrail test suite (`tests/guardrails/`): committed decks that
  each isolate one desired model behavior, enforced by property assertions
  paired with intent prose (`BEHAVIOR.md` per deck); run via
  `make test-guardrails`. Initial decks: `no_incentive`,
  `supply_constrained`, `supply_then_demand_constrained`.
- `FleetProfile.get_fleet_technology_uptake`: fleet-wide technology uptake
  (existing-vessel-weighted), shared by the technology_uptake plot and the
  guardrail tests.

## [1.0.0] - 2026-07-16

Initial public release of Navigate, an open-source sectoral integrated
assessment model for simulating transitions of the maritime industry.

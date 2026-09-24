<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- An attribute-suite check that every registered DSL attribute and command has a
  heading on its node's reference-manual page, that every heading there names a
  registered one, and that the report-property appendix and the profile getters
  cover each other in both directions. The manual is hand-written with no
  autodoc, so its drift from the parser tables and from what a report can
  actually extract was previously found by readers rather than by CI.
- A golden-baseline regression suite (`tests/regression`, `make
  test-regression`, run in CI): small pinned-constant decks whose report CSV
  output is compared against committed baselines within a documented
  runner-noise floor, so unintended result changes fail with a structured
  per-cell diff and intended ones are reviewed as a baseline git diff
  regenerated via `make regen-regression`. Conventions in
  `tests/regression/README.md`.
- The console prints the number of logged warnings at the end of a run,
  pointing at the `.log` file. Warnings were previously visible only in the
  log, so a run whose results they affect could look clean on the console.
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
- `navigate.economics.flows.trim_flow_to_lifetime`: trims a yearly flow to a
  possibly fractional number of years on a copy, prorating the final year.
  Shared by the technology-retrofit and fuel-conversion business cases
  (previously a package-private helper and the legacy
  `get_remaining_cost_flow`).

### Changed
- A wildcard node reference is expanded against the registered nodes of its
  type before the value reaches the attribute, where it used to be handed to
  the attribute as written and the matched nodes spliced into the stored list
  afterwards. What a deck may write is unchanged — a glob still stands for
  every registered node of its type whose name matches, and both
  `Fuels = Fuel("*")` and `Fuels = [Fuel("*")]` still work — but three
  constructs that used to slip past the attribute are now rejected. A glob as
  a command argument, which was never documented and died later in the run
  with a misleading "may only appear inside lists", is refused at its deck
  line naming the command. A glob on a single-valued attribute is refused by
  the attribute itself, so `Route = Route("r_*")` on a Vessel now reads
  `Vessel("v") attribute 'Route' only allows assignment of nodes of type
  Route, but got list`. And an attribute listing both a node and a glob that
  also matches it is rejected as a duplicate, where the uniqueness check ran
  before the expansion and passed. Expansion also no longer depends on how
  far the reference resolution had progressed when the glob was reached.
  **Breaking** for code importing navigate as a library: `assign_value` and
  `assign_list` no longer accept a `WildcardNodeReference`; the parser
  expands the glob into the matched nodes first. No result moves.
- A `Route` rejects an empty `Speeds` or `PortDurations` list at assignment
  (`List must contain at least 1 values.`), naming the deck line that emptied
  it. Both are assignable under EVENTS, where an empty list previously passed
  the setter and was reported later, if at all, as an inconsistency between
  the route's leg lists.
- A deck whose `ModelDefinition` omits `StartDate` is now reported as the
  unassigned attribute it is (`ModelDefinition: Attribute 'StartDate' is
  unassigned.`), as every other required node attribute is, in place of
  `Error in ModelDefinition: 'StartDate' must be defined.`.
- A `Fuel` whose `LowerHeatingValue` or `MassDensity` is missing is now
  reported as the unassigned attribute it is (`Attribute 'LowerHeatingValue'
  is unassigned.`), as every other required node attribute is; the
  greater-than-zero bound is reported separately and only when a value was
  actually assigned.
- Internal reorganization (no DSL or result changes): the five profiles that
  weigh emissions by global warming potential (vessel, fleet, manager, port
  and plant) share one `_FuelEmissionProfile` layer that reads the emission
  nodes once, where three of them each built the same lookup; `PlantProfile`
  joins the fuel-profile branch and reads its fuel's lower heating value from
  the shared lookup by fuel name. **Breaking** for code importing navigate as
  a library: `Plant.initialize_profile` takes the fuels dict and
  `PlantProfile.initialize` the fuels dict and the fuel name;
  `Emission.global_warming_potential` holds its zero default from
  construction, typed as the scalar, curve, variable or expression a deck can
  assign, and `Emission.initialize` is gone; `Scalar.get` is typed with
  paired overloads (an array in returns an array, anything else a `float`).
- **Breaking** for code importing navigate as a library: `expand_id_wildcard`'s
  second parameter is named `domain` and takes an enum class or a tuple of its
  members.
- `make` runs its targets through a local `.venv` when one exists and only
  otherwise through the `nav` conda env, so a git worktree runs its own
  source tree instead of the checkout the conda env's editable install
  points at. The `PATH` it builds is quoted, so the `.venv` path also works
  on WSL where Windows entries with spaces are inherited.
- **Breaking** for code importing navigate as a library: `assign_fraction_list`
  returns the rescaled fractions instead of also rescaling the list it was
  handed, and its second return value is named for the rescale it reports.
  Both setters that call it already assigned the returned list, so no deck
  result moves.
- A wildcard node declaration whose `InitialSplit` or `ConditionDistribution`
  needs rescaling logs the rescale once per matched node. The parser hands one
  list to every node it matched, so the in-place rescale left all but the
  first with a list already summing to 1 and only the first reported it. The
  fractions themselves are unchanged.
- **Breaking** for code importing navigate as a library: `Scalar` requires the
  value it answers with, so `Scalar()` no longer constructs.
- **Breaking** for code importing navigate as a library: the `-INF`/`INF`
  keywords move out of `assign_id` into a new `assign_bound`, which owns the
  whole bound contract — a scalar or one of the keywords — as `assign_boolean`
  already owns `TRUE`/`FALSE`. The calculator nodes' public `BOUNDS_MAP` is
  gone with them, and `assign_id` takes an enum class and returns one of its
  members.
- **Breaking** for code importing navigate as a library:
  `build_table_1d`/`build_table_2d` lose `allow_date` to
  `build_table_1d_dated`/`build_table_2d_dated`, so the undated pair returns
  float arrays only while the dated pair still returns float arrays for a
  numeric table.
- **Breaking** for code importing navigate as a library:
  `command_assignment_to_tuple_dict` loses its `symmetric` flag, which nothing
  assigned.
- A bound the deck writes is reported against its own line: an unaccepted one
  reads `only allows assignment of scalars, -INF or INF, but got X` rather
  than `does not accept ID 'X'`, which named neither the keywords nor the
  number the setter also takes, and a list or a table now reads as that
  message instead of dying as a `TypeError` no deck line could be attached to.
- The assignment boundary's annotations carry the shapes it validates instead
  of a wide union: `assign_value` and `assign_list` are generic over what they
  are handed, so a setter no longer inherits `Node | WildcardNodeReference |
  Scalar | float | Expression`; `as_scalar` pairs a wrapping overload with a
  passthrough; and the three `command_assignment_to_*` helpers are generic
  over their dictionary's key type. No runtime behavior changes, and neither
  does spelling "no length check" as `length=None` rather than `length=()`.
- **Breaking** for code importing navigate as a library: the two reference
  classes are split along the line the parser already draws between them.
  Both are parser-internal tokens and move to
  `navigate.parser._node_reference`, out of the `navigate.core` namespace;
  each is now a frozen dataclass of `type` and `name`, so it compares by
  value and carries no `is_type()`, the wildcard's `pattern` property is gone
  — read `name` — and `WildcardNodeReference` no longer subclasses
  `NodeReference`.
- **Breaking** for code importing navigate as a library: the parser resolves
  every `Type("name")` a deck writes when it reads the assignment or command,
  so node setters receive the referenced node itself, never a `NodeReference`.
  A name not yet declared is a node from that moment on, filled when its
  declaration is read or, failing that, pulled from the default library where
  the reference walk used to swap it in — same order, same pulls, same
  registry, and the same results on every committed deck. `assign_value` and
  `assign_list` accept a `Node` and reject either reference token;
  `Expression.node_references` holds nodes as soon as the parser initializes
  the expression; and `NodeReference` loses `reference_location`,
  `internal_bounds` and `set_internal_bounds`, which nothing writes any more —
  the calculator nodes expose the bounds they hold as `internal_bounds`. The
  one delta: a reference's bounds reach the calculator when the assignment is
  read, so a reference re-assigned later in `DEFINE` leaves them behind, as one
  re-assigned across time steps in `EVENTS` always did.
- **Breaking** for code importing navigate as a library: the calculator nodes
  (`Curve`, `Forecast`, `Surface`, `Timetable`, `Variable`) take the bounds an
  attribute imposes on them as two floats, `set_internal_bounds(lower, upper)`,
  replacing `transfer_internal_bounds(reference)`, which read them off the node
  reference the parser was resolving. The merge is unchanged — the tightest
  bound offered by any referencing attribute wins — and so are the warnings it
  logs and the simulation results. The two floats are also the shape
  `assign_value` passes, so a calculator node handed to a bounded attribute
  tightens its own bounds directly. The write-only
  `set_internal_lower_bound`/`set_internal_upper_bound`, which nothing called,
  are removed without replacement.
- **Breaking** for code importing navigate as a library: a `Copy` statement
  duplicates only the named node, and the nodes it references are shared with
  the source instead of being cloned and re-bound afterwards. `Node` loses
  its `just_copied` attribute, which existed only to drive that re-binding.
  Simulation results are unchanged.
- The minimum supported Python version is 3.13 (was 3.12).
- `navigate.util` and `navigate.exceptions` are fully type-annotated and
  type-checked; shared numpy array aliases (`FloatArray`, `BoolArray`, …)
  live in the new `navigate.util.types_`. **Breaking** for code importing
  navigate as a library — the helpers keep only their exercised surface:
  the caller-less `no_value_assigned_dict_error`, `merge_dicts`,
  `divide_dicts`, `collapse_dict`, `sum_tuple_dict_results` (its summations
  are covered by `collapse_tuple_dict`), `normalize_fractional` (`Route`
  normalizes its voyage distribution at (re-)initialization instead of per
  getter call, with identical values), `decompose_dates`, and the
  `DAY`/`MONTH` constants are removed, as are the never-passed parameters
  `in_place` (dict arithmetic), `transform` (`extract_from_dict`,
  `slice_list`, `slice_dict`), `x`/`y`/`length` (`to_numpy`), and `key`/`n`
  (`sum_dict_results`).
  `is_single_dict`/`is_tuple_dict` return False (was None) for
  empty dicts, `add_dicts`/`multiply_dicts` rebuild their result instead of
  deep-copying the first argument (values unchanged and still never aliasing
  the inputs), and keyword-visible helper parameters have clearer names:
  `divide_nonzero(numerator, denominator, ...)` (was `a`, `b`),
  `is_strictly_increasing(values)` / `is_non_strictly_increasing(values)`
  (was `x`), and `interpolate_yearly_flow(yearly_flow, age)` (was
  `interpolate_tied_capital` — nothing in it is tied-capital-specific).
  `retrieve_keys`/`matching_keys` no longer take a `key_fn` extractor —
  enum wildcard expansion matches member names inside
  `expand_id_wildcard` — and `get_increments_origin_index` folds into
  `get_increment_origin_index`, which takes a scalar age or an array of
  ages.
  `extract_from_dict` carries overloads keyed on `key is None` (a given
  key yields the sliced value, no key the whole dict), the extraction and
  slicing helpers' `idx` accepts the full set of index kinds — the new
  `Index` alias (`int | np.signedinteger | slice | IntArray`) — and
  `extract_from_dict`'s `idx=None` arm is replaced by a full-slice
  default (identical values; non-empty whole-dict extraction no longer
  aliases the backing dict).
- **Breaking** for code importing navigate as a library: the `is_*()`
  type-check methods on `TypeCheckMixin` are replaced by `TypeIs` guard
  functions in `navigate.core.node_type` (`is_calculator`, `is_feedstock`,
  `is_process`, `is_surface`, `is_variable`), so type checkers narrow node
  types at call sites; the sixteen unused predicates and the unused
  `Scalar.is_forecast()` are removed without replacement. The guards take a
  `Node`.
- Deck errors surface as a single clean traceback (the internal exception
  that triggered them is no longer chained), internal parallel-structure
  mismatches in the calculation modules now raise instead of silently
  truncating, and log messages are formatted lazily with unchanged text.
- The lint toolchain is now `ruff` (formatting, linting, import sorting) and
  `mypy` (type checking), replacing `flake8`/`isort`; `make lint` runs both
  plus the REUSE check. The whole codebase was reformatted in a single
  mechanical commit recorded in `.git-blame-ignore-revs` — run
  `git config blame.ignoreRevsFile .git-blame-ignore-revs` once to keep
  `git blame` useful across it. Pre-existing findings are grandfathered in
  generated ratchet regions in `.ruff.toml` and `mypy.ini` that only ever
  shrink; new code is checked in full.
- **Breaking**: the DSL surface no longer contains uppercase acronym runs.
  The `CAPEX`/`OPEX` attributes are now `Capex`/`Opex` (Converter,
  PowerSystem, Tank, Technology, Vessel), and report properties end in
  `Wtt`/`Ttw`/`Wtw` (`TotalEquivalentWtt`, formerly `TotalEquivalentWTT`),
  which changes the report column headers. An old attribute spelling fails
  parsing; an old report property spelling makes its column disappear from
  the report, with the reason recorded only in the `.log` — report
  properties have no parse-time validation. Enum keyword values
  (`Scope = WTT`, `AMMONIA`, `FLAT`) remain ALL_CAPS, so that casing now
  means exactly one thing in a deck: an enum value.
- The output-only fleet aggregations (in-fleet flags, vessel-to-fleet
  consumer totals, fuel-conversion expenses, installed/newbuild/scrapped and
  fuel-converted power, fleet speeds, transport work and baseline energy) run
  once after the simulation instead of every time step. Outputs are
  bit-identical, with two edge deltas: the differing-installed-power fuel
  conversion warning is logged once per vessel pair instead of once per
  affected time step, and the fleet reference speed at a step where the
  fleet has no vessels is NaN (previously an undefined division).
- `FleetProfile.set_instantaneous_freight_rate` accepts a slice and an array
  like the other fleet timeline setters, and the fleet-level instantaneous
  freight rate is aggregated in one whole-timeline array operation instead of
  once per time-step. Outputs are bit-identical.
- **Breaking** for code importing navigate as a library: every public getter
  on the profile classes in `navigate.core.profiles` takes no arguments and
  returns the whole timeline array, or the whole dict keyed as the storage
  is (tuple-keyed getters by the `(key1, key2)` pair), so callers index the
  result; `get_length` and `get_shape` are gone. The totals (`get_energy`,
  `get_raw_energy`, `get_operational_energy`, every `get_total_*`) keep
  their meaning, and the emission intensity getters divide by the total
  consumed energy on every path. `get_saving`, `get_remedial_units` and
  `get_levy_units` lose their mandatory key and therefore resolve as report
  properties. Report and plot output is bit-identical; the one behavioural
  difference is `FleetProfile.get_fleet_technology_uptake`, whose dict has
  no entry for a technology no vessel carries where the keyed call returned
  a zero series.
- **Breaking** for code importing navigate as a library: the getters on the
  expectation classes in `navigate.core.expectations` lose their never-passed
  parameters, so each returns one concrete type instead of a key-switched
  union — `energy_type_id` from the eight vessel energy getters, `port_name`
  from `ProducerExpectation.get_export_distribution`, and `idx` from
  `RegulationExpectation.get_flexibility_cost`, which returns the whole
  timeline array. `_Expectation.get_length` is gone, and `get_shape` names
  its argument for the `start` step it sizes from. In `navigate.util`,
  `extract_from_dict_list` loses the same key parameter and is renamed
  `slice_dict_list`, beside the `slice_list` and `slice_dict` it joins.
  Results are unchanged.
- **Breaking** for code importing navigate as a library: every key on an
  expectation getter is mandatory. `PlantExpectation`'s
  `get_levelized_delivery_cost`, `get_production_wtt`,
  `get_expected_production_wtt`, `get_delivery_wtt` and
  `VesselExpectation.get_fair_share_fuel_expected` index their storage
  directly, and the two getters that served both one key and the whole dict
  split by name: `PlantExpectation.get_feed_mass(feed_name, idx)` beside the
  new `get_feed_masses(idx)`, and
  `VesselExpectation.get_fair_share_fuel_existing(port_name, fuel_name)`
  beside the new `get_fair_share_fuels_existing()`. A keyed read of an empty
  storage now raises `KeyError` rather than yielding an empty dict; a key
  missing from a populated storage always raised one. The storages are
  prepopulated at initialization over the same collections their callers
  iterate, so no run reaches either case and results are unchanged.
- Internal reorganization (no DSL or result changes): the retrofit flow of
  `navigate/fleet/technology_adoption.py` communicates through
  `_RetrofitProposal`/`_AdoptionBasis` dataclasses instead of an anonymous
  6-tuple and loose per-vessel parameters; the two technology cap
  reconcilers share their scaling arithmetic (`_scale_tails_to_cap`); the
  residual-energy update and the missing-technology approximation are
  decomposed into per-phase helpers. Outputs are bit-identical.
- **Breaking** for code importing navigate as a library:
  `get_technology_discount_rate` (folded into the per-vessel adoption
  basis), `collect_retrofit_proposals` and `apply_uptake_transition`
  (replaced by the module-internal `_propose_retrofits` and
  `_apply_retrofits`), and `shares_to_package_mix`,
  `calculate_packages_saving`, `reconcile_retrofit_technology_caps`, and
  `transfer_retrofit_uptake` (renamed module-internal with a `_` prefix),
  all in `navigate/fleet/technology_adoption.py`. No callers outside the
  module remain.
- The warning about a missing `TechnologyCostOfCapital` is removed; the
  fallback to the vessel's cost of capital is documented on the attribute
  instead.
- **Breaking** for code importing navigate as a library: the `Report` and
  `Plot` node classes no longer carry export methods — the core → `output`
  back-edge is gone. `Report.start_export`, `end_export`, and the
  `export_*` methods are replaced by the free function
  `navigate.output.report_writer.write_report`, which owns the workbook/CSV state and the
  per-sheet error containment; `Plot.generate_plots` is replaced by
  `navigate.output.plots.render.generate_plots`, a free function taking the
  plot node. `NodeReport` moves from `navigate.output.report_writer` to
  `navigate.core.node_report`. The DSL surface and simulation results are
  unchanged.
- Internal simplification (no DSL or result changes): profile and expectation
  `initialize` methods build default-valued per-key storage through the
  base-class helpers (`_default_dict`, `_default_dict_float`,
  `_allocate_list`, and a new `_default_nested_dict`) instead of manual
  per-key loops and raw `[None] * length` expressions; the unused
  profile-side `_allocate_list` is removed. Loops that copy real per-key
  values (heating values, GWP, liquid-market supply sentinels) are
  unchanged.
- Internal simplification (no DSL or result changes): node initialization is
  unified on one idiom — `initialize_dependencies` seeds dictionary keys with
  `setdefault(key, None)` and all defaulting happens in `initialize` via
  `is None` checks. Defaults that previously lived in the seeding step
  (`Fleet` limits and availability flags, `Producer.allow_plant`,
  `Route.voyage_distribution`, policy `IncludeVessel`) moved to `initialize`
  with unchanged values, and `Converter` now seeds per key instead of only
  into an empty dictionary — the latter can only turn a `KeyError` on
  late-added fuel types or emissions into a seeded default, never change a
  working deck.
- A `Report` property request that matches no node in the simulation logs a
  warning at export instead of silently producing no columns.
- Nodes that no chain of node references connects to a top-level node
  (`Fleet`, `Producer`, `Levy`, `Regulation`, `Emission`, `Fuel`, `Report`,
  `Plot`) are removed after the DEFINE section is processed, with one
  aggregated warning listing them. A `Port` counts as connected only through
  a `Route`'s `Ports`: a `Levy`/`Regulation` `Jurisdiction` selects among
  routed ports and does not keep a port alive, and removed ports are dropped
  from surviving `Jurisdiction` lists with a warning, so an unrouted
  jurisdiction port no longer feeds the fuel-supply aggregation. A
  `Jurisdiction` listing only unrouted ports is emptied by this and the
  policy fails with the unassigned-attribute error. Previously such nodes
  half-participated in results: an unassigned `Port` was summed into the
  global supply aggregation, the ports of an unassigned `Route` were seeded
  as producer export destinations, and unassigned `Vessel`s/`Plant`s
  exported zero-filled report columns. Consequences: queued `EVENTS` statements targeting only
  removed nodes are dropped; a removed node never runs its initialization,
  so an incompletely configured unused node no longer errors; a command
  naming a removed node raises the unknown-name error, with a hint naming
  the removed node; a node used only as a `Copy` source is removed without
  a warning; the per-node "is not assigned to a 'Fleet'/'Producer'"
  warnings are superseded by the aggregated warning. For code importing
  navigate as a library, `Vessel.is_assigned_to_fleet` and
  `Plant.is_assigned_to_producer` are removed — after the prune every
  surviving vessel and plant is assigned, so both predicates were
  tautological; for the same reason `Producer.initialize_dependencies` and
  `navigate.fuel.calculate_fuel_import_to_ports` no longer take a `routes`
  argument — every surviving port is routed.
- **Breaking** for code importing navigate as a library: the node type is
  set through the constructor instead of being assigned afterwards —
  `Node.__init__` (and the `_AssetManager`, `_Machinery`, and `_Policy`
  bases) takes a required `type_` argument that the node stores, so
  external `Node` subclasses must pass their type constant to
  `super().__init__`. The never-read `unit` attribute on `NodeReference`
  is removed. Simulation results are unchanged.
- **Breaking** for code importing navigate as a library: the
  `navigate.core._mixin` module is dissolved — `TypeCheckMixin` lives in
  `navigate.core.node_type` next to the type constants it checks against,
  and `CommandReferenceMixin` is removed with its `command_references`
  storage and `add_`/`clear_` mutators defined directly on `Node` and
  `_GeneralNode`. The unused `is_node()` statics on both classes are
  removed. Simulation results are unchanged.
- The fuel-conversion supply/demand snapshot is read from the fleet
  expectation, which accumulates the fuel-type totals per time-step, instead
  of being read back from the fleet profile — profiles are output-only
  (ARCHITECTURE.md, Data-flow invariants). Simulation results are unchanged.
- **Breaking** for code importing navigate as a library: the fuel-conversion
  phases exchange dataclasses instead of nested dicts —
  `propose_fuel_conversions` returns a list of `_ConversionProposal` objects,
  each holding a `_ConversionCandidate` per destination type, rather than a
  dict keyed by `(name_from, increment_idx)`, and
  `reconcile_fuel_conversion_caps` / `apply_fuel_conversions` take that
  list. Simulation results are unchanged.
- The fuel-conversion business case compares fuel costs over the common
  remaining-lifetime window of the source and destination vessel types,
  prorating both flows at that window. Previously each flow was prorated at
  its own remaining lifetime and then truncated to the shorter length,
  weighing a full year against a prorated year whenever the lifetimes
  differ. No committed deck defines conversion pairs with differing
  lifetimes, so current results are unchanged.
- The fuel-conversion proposal walk no longer stops at the first increment
  without an eligible destination; it skips to the next cohort instead. The
  early-out could drop proposals only for a cohort sharing an age with a
  longer-spanning cohort walked before it — a layout no committed deck
  produces, so current results are unchanged.
- Fuel-conversion expenses are levelized exactly: the reported yearly charge
  discounts back to the conversion cost at the destination vessel's cost of
  capital, replacing the approximate capital-recovery factor `1/L + r`,
  which overstated the discounted total (about 21% at a 5-year window and
  8% discount rate). The charge is booked per service year within the window
  (prorated in a partial final year) instead of being interpolated between
  yearly anchors, which zeroed or blended timeline points near the window's
  edges.
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
- Internal parser identifiers are renamed to descriptive names (no DSL or
  result changes): the AST classes `CopyStmt`/`ImportStmt`/`DateStmt`/
  `NodeDecl`/`GeneralNodeDecl` are now `CopyStatement`/`ImportStatement`/
  `DateStatement`/`NodeDeclaration`/`GeneralNodeDeclaration` (grammar rules
  and transformer callbacks follow), `Event.stmts`/`add_stmt` are now
  `statements`/`add_statement`, and the remaining abbreviated identifiers in
  `navigate/parser/` are spelled out (`statement`, `declaration`,
  `node_reference`, `arguments`, `copy_from`/`copy_to`). `SourceLoc` moves
  from `navigate/core/table_data.py` into the parser AST module as
  `SourceLocation` — the parser is its only consumer — and the never-read
  `TableData.source` field is dropped.
- **Breaking** for code importing navigate as a library: the `Producer` and
  `Fleet` node classes no longer carry calculation methods — the
  core → `fuel`/`fleet` back-edge is gone. `initialize_existing_producer`
  (new `navigate.fuel.initialization`), `perform_progression`, and
  `perform_planning` are free functions in `navigate.fuel`, and
  `Producer.calculate_expectation` is replaced by calling
  `calculate_export_expectation` directly. `initialize_existing_fleet`
  (new `navigate.fleet.initialization`), `transfer_multipliers_to_profile`
  (`navigate.fleet.aggregation`), `get_cargo_miles`
  (`navigate.fleet.utils`), and `transfer_operational_saving_to_vessels`
  (`navigate.fleet.operation`) are free functions taking the fleet. The
  fleet newbuild-decision functions (`calculate_orderbook_newbuilds`,
  `calculate_modelled_newbuilds`, `calculate_modelled_uptake`,
  `log_orderbook_deferral`, `add_newbuilds`) move from
  `navigate.fleet.evolution` to the new `navigate.fleet.planning`, and
  `navigate.fleet.evolution.calculate_evolution_expectation` now takes
  `(fleet, timeline, idx)`. The fleet newbuild choice now runs through the
  shared `navigate.economics.calculate_two_axis_uptake`, whose unused
  `intra_limit`/`inter_limit` parameters are replaced by one per-asset
  `limits` parameter projected onto both axes. Simulation results are
  unchanged.
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
  `ROUND_OFF`, `YEAR`) move from `navigate.core.misc` into it. Most
  `navigate.util` names are re-exported unchanged, but
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
- **Breaking** for code importing navigate as a library: `Expression` carries
  the deck text it was written as in `text`, the node references it parses in
  `reference_strings`, and the nodes the parser resolves those to in
  `node_references` — one attribute no longer holds both — and the references
  of an arbitrary expression text are read through the module-level
  `parse_reference_strings`, replacing the `reference_strings()` probe.
  Evaluating an expression before it is initialized raises `RuntimeError`.
  `navigate.core.expression` is fully type-annotated and type-checked.
- **Breaking** for code importing navigate as a library: the nearest-index
  helpers in `navigate.util` split by the shape they take instead of
  overloading one name. `find_nearest` takes an array of query values only; a
  single value goes through `find_nearest_index`, which returns an `int`.
  `get_increment_origin_index` takes a single age and returns an `int`; an
  array of ages goes through `get_increment_origin_indexes`. No result moves.

### Removed
- **Breaking** for input decks: the `BunkerLogistics` general node is
  removed. Its responsibilities move to regular nodes: whether a fuel
  belongs to a liquid market is the new `LiquidMarket` attribute on `Fuel`
  (replacing `LiquidMarketFuels`; the shipped defaults for
  `fossil_fuel_oil` and `liquefied_natural_gas` set it, replacing the
  deleted `DefaultBunkerLogistics` module), and fuel delivery to ports is
  the new `set_fuel_transport`/`set_fuel_distance` commands on `Plant`,
  mirroring the feed twins: a per-port transport mode and distance priced
  through the plant region's `set_transport_cost`/`set_transport_wtt`
  rates (replacing `set_distance`/`set_transport_cost`/`set_transport_wtt`
  keyed by fuel, whose per-fuel global rates could not differ per plant).
  General nodes no longer accept commands, and no general node
  participates in node-dependency initialization. For library code,
  `Fuel.belongs_to_liquid_market()` is replaced by the public
  `liquid_market` attribute, and `calculate_plant_logistics_expectations`
  loses its `bunker_logistics` parameter. Committed decks are results-
  neutral except the examples, which lose their flat transport-cost
  assignments (delivery costs become zero).
- The fuel-type supply members on `FleetProfile`
  (`add_fuel_type_supply`/`get_fuel_type_supply`): their only reader was the
  fuel-conversion snapshot, which now reads the fleet expectation; no report
  or plot consumes fleet-level fuel-type supply.
- **Breaking** for code importing navigate as a library: the remaining
  node-class getters are replaced by direct attribute access (CODESTYLE.md,
  Classes and attributes) — the keyed dict getters on `Region` (13, backing
  dicts
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
  direct attribute access (CODESTYLE.md, Classes and attributes) — `name` was
  already public, and the internal `_type` is now public `type` on both
  classes. `get_command_references()` on `Node` and `_GeneralNode` is
  likewise replaced by a public `command_references` attribute
  (`add_`/`clear_` mutators unchanged). Nodes inside `plot_data.pkl` carry the renamed
  attribute, so the pickle incompatibility with earlier versions noted
  below extends to this change.
- **Breaking** for code importing navigate as a library: trivial getters on
  the helper classes are replaced by direct attribute access
  (CODESTYLE.md, Classes and attributes) — `SimulationManager.get_timeline`/
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
- **Breaking** for code importing navigate as a library:
  `write_binding_lp` (`navigate/bunker/optimize.py`), a debugging helper
  that exported a solved model's binding constraints to an LP file. It had
  no callers.
- **Breaking** for code importing navigate as a library:
  `get_remaining_cost_flow` (`navigate/economics/flows.py`), superseded by
  `trim_flow_to_lifetime`; its slice-from-the-end mode (`initial=False`) had
  no callers. The `get_flow_residual` re-export from `navigate.economics`
  goes with it — no consumer outside `flows.py` remains.
- **Breaking** for code importing navigate as a library:
  `calculate_annualization_factor` (`navigate/economics/metric.py`) and
  `as_equal_installments` (`navigate/economics/flows.py`). The approximate
  capital-recovery annualization they implemented is replaced by exact
  levelization in the conversion expense booking; nothing else called them.
- **Breaking** for code importing navigate as a library: 17 expectation
  readers with no call site in the package or the tests —
  `PlantExpectation.get_capacity`;
  `ProducerExpectation.get_existing_production`/`get_pipeline_production`/
  `get_newbuild_production`;
  `FleetExpectation.get_newbuild_multipliers`/`get_total_existing_multipliers`/
  `get_total_expected_multipliers`;
  `PortExpectation.get_bunker_mass_expected`/`get_bunker_mass_existing` (the
  same-named `VesselExpectation` pair the fuel-inertia constraint calls stays);
  and `VesselExpectation.get_distances`/`get_raw_energy_per_leg`/
  `get_raw_energy_per_port`/`get_operational_energy_per_leg`/
  `get_operational_energy_per_port`/`get_operational_saving_sea`/
  `get_operational_saving_port`/`get_regional_raw_energy_sea`. Unlike profile
  getters, expectation getters are never dispatched by name from a report or
  plot property, so no deck reaches one. The state behind them is still
  written and unchanged.
- **Breaking** for code importing navigate as a library:
  `extract_from_tuple_dict` (`navigate/util/collections.py`, re-exported from
  `navigate.util`). All three call sites selected on a single key part and
  passed neither an index nor a transform, so each now builds the dict it
  needs with a comprehension; the both-keys arm, the whole-dict arm, the
  `idx` parameter and the never-passed `transform` parameter had no caller.
  The `transform` parameter of the internal `_resolve_dict` goes with it.
- **Breaking** for code importing navigate as a library: `extract_from_dict`
  (`navigate/util/collections.py`, re-exported from `navigate.util`), which
  had no call site left in the package. Library callers that sliced a whole
  dict should reach for `slice_dict`, which differs only in indexing every
  value rather than passing a non-array through untouched. The internal
  `_resolve_dict` and `_slice_value`, reachable from nowhere else, go with it.
- **Breaking** for code importing navigate as a library: the five expectation
  storages left write-only when their unread getters were removed, along with
  the setters and adders that fed them — `PlantExpectation.set_capacity`,
  `VesselExpectation.set_distances`/`set_regional_raw_energy_sea`, and
  `PortExpectation.reset_bunker_mass_expected`/`add_bunker_mass_expected`/
  `reset_bunker_mass_existing`/`add_bunker_mass_existing`. Their call sites go
  with them: the annual plant capacity stays the local that production is
  computed from, the per-leg distances stay on the operations record the
  cargo-mile calculation reads, and the regional raw sea energy loses its
  `convert_to_regional_steps` conversion (the function itself is shared and
  stays). The same-named `VesselExpectation` bunker-mass members,
  keyed by port and fuel and read by the fuel-inertia constraint, are
  untouched, as are `Plant.set_capacity` and `Route.set_distances` on the DSL
  nodes. No deck result moves.

### Fixed
- The reference manual states the units an emission intensity is reported
  and given in. The `RegulationMeasureID` appendix had INTENSITY in ton/GJ,
  a factor of 1000 out, and both transport measures in ton per cargo-mile, a
  factor of a million out; the report-property footnote repeated the
  INTENSITY error and gave the two transport measures a cost unit, USD per
  cargo-nautical mile. The same factor of 1000 sat on seven report
  properties documented in ton per gigajoule: the four plant
  `Intensity*Wtt` rows and the three port `BunkerIntensity*Wtt` rows, which
  share the conversion that the six vessel and fleet `Intensity*` rows
  already documented in kg per gigajoule. A reader sizing a threshold or
  reading an intensity column off these pages was out by that factor. The
  code and the `Regulation` page always had it right — an emission intensity
  is kg/GJ, equivalently g/MJ, and both transport measures are grams per
  cargo-mile — so no behaviour and no result changes.
- The `RemedialUnits` and `LevyUnits` report columns sum the vessels below a
  fleet and below the whole simulation, as the remedial and levy expenses of
  the same policies already did. Only vessel scope accumulated them, so a
  fleet- or global-scope report gave zero across the whole timeline beside
  non-zero expenses for those policies, and the zeros read as a result rather
  than as missing data. Reported results at fleet and global scope move
  accordingly; vessel scope is unchanged.
- The four `Outside`/`Extrapolate` messages a `Surface` or a `Timetable`
  raises or logs name the node that carried the contradiction. Each was
  written with a literal `{}` and never formatted, so the error read
  `{}: 'Outside' must be defined when 'Extrapolate' is set to FLAT.` and gave
  the reader nothing to look for in the deck.
- The bounds an attribute imposes reach the nodes a wildcard matched, as they
  already did for a node written out by name. A calculator (`Curve`,
  `Forecast`, `Surface`, `Timetable`, `Variable`) reached through a glob — on
  `Route.PortDurations`, for instance — kept whatever bounds its other
  references gave it, so the limit of the attribute it was assigned to never
  applied. No committed deck globs a calculator, so no shipped result moves.
- The two errors a wildcard node reference can raise — it matched no node, or
  it stands where a single node is expected — name the deck line and the
  include file they were written in, as every other deck error does. Both
  were raised after the decks had been read, with no line left to report.
- The reference manual documents the DSL surface the parser accepts. Twelve
  registered names had no entry — `Table` on `Curve`, `Forecast`, `Surface` and
  `Timetable`, `FuelType` on `Emission`, `ShorePowerCost` and
  `ShorePowerConnectionShare` on `Port`, `FlexibilityHorizon` and
  `AllowThresholdAdjustment` on `Regulation`,
  `set_shore_power_emission_factor` on `Port`, `set_export_distribution` on
  `Producer`, and `add_producer_property` on `Report` — and five entries named
  attributes no node has: `WindUtilization` and `SolarUtilization` on `Port`,
  which the page also used in its example, and
  `FlexibilityMaximumIterations`, `FlexibilityToleranceX` and
  `FlexibilityToleranceY` on `BunkerOptions`.
- The report-property appendix of the reference manual documents the properties
  a report can carry. Thirty-four documented tokens resolved to no profile
  getter, and seventy-six resolvable properties, over forty-six distinct tokens,
  had no row under a command that exposes them. The twenty-two `*Demand*` rows
  are gone: a fuel consumer stores its demand as dicts keyed by energy demand
  type, which `RawEnergy*`, `OperationalEnergy*` and `Energy*` export as one
  column per type. `PropulsionSaving`, `ElectricalSaving` and `HeatSaving` are
  gone with no replacement — they name a getter the report writer cannot call.
  `CumulativeScrappedPopwer`, `VesselTreshold`, `ConverterFuelEnergy`,
  `DevelopmentConstraint`, `CumulativeDevelopmentConstraint`, `OtherTime`,
  `IntendedUnits` and `AchievedUnits` are spelled `CumulativeScrappedPower`,
  `VesselThreshold`, `ConverterEnergy`, `MaximumDevelopment`,
  `CumulativeMaximumDevelopment`, `OverheadTime`, `SharedAllowance` and
  `SharedUnits`, and `EvolutionTime` splits into `FleetEvolutionTime` and
  `ProducerEvolutionTime`. The appendix gains the rows it was missing, among
  them the per-phase timers, `CargoMiles`, `BaselineEnergy`,
  `WeightedAverageAge`, the speed extremes, `BunkeringAllowed`, the plant
  intensity costs and the regulation allowance and unit properties.
- `set_bunkering_cost` is no longer accepted on a `Port`. The command was
  registered but implemented nowhere, so a deck writing it passed the parser's
  allow-list and then died with an `AttributeError`; it is now rejected at its
  deck line like any other unknown command. Use `set_handling_cost` for the
  cost of bunkering a fuel in a port.
- A value the model rejects — an attribute's or a command's — prints the
  located one-line error and exits 1, as a deck naming an attribute no node
  has already did. The sentence was the same, but arrived as the last line of
  a Python traceback.
- A non-number in an `InitialSplit` or `ConditionDistribution` list is
  rejected against its deck line, naming the kind that was written, as
  `only allows assignment of plain numbers, but got Curve("c")`. The
  entries were checked for a negative sign before their kind, so
  anything that does not compare against a number escaped as an
  unlocated `TypeError`.
- A boolean or an ID attribute reports whatever kind of value a deck wrote
  against its own line: `Active = [1.0]` reads as `only allows assignment of
  TRUE or FALSE, but got list`, `FuelType = [1.0]` as `only allows assignment
  of IDs, but got list`, and `FuelTypes = [1.0]` — a list-valued ID attribute
  such as a `Tank`'s or a `Converter`'s — as the same sentence for the element
  at fault. Each of the three died as a `TypeError` that no deck line could be
  attached to. The `does not accept ID 'X'` message an unknown token produces
  is unchanged.
- A whole-number fraction list is accepted whatever it sums to. Only a list
  the rescale happened to divide reached the attribute as fractions, so
  `Route.set_condition_distribution([1])` — the single-leg value its docstring
  and the Route reference page give as the example — along with `[1, 0]`,
  `[0, 0]` and, `bool` subclassing `int`, `[True, False]`, failed as
  `only allows assignment of scalars, but got integer`, a rule the attribute
  does not have, while `[1, 1]` passed. The same held for
  `Fleet.set_initial_split`. Only a Python caller could reach this, and no
  deck moves: the DSL grammar reads every number as a float, so the example
  written in a deck has always arrived as `[1.0]`.
- `set_operational_saving_port` names the energy demands it accepts whenever
  it rejects one: both `PROPULSION`, a member the attribute does not hold, and
  an unknown token such as `BOGUS` now read `only allows assignment of
  ELECTRICAL, HEAT, but got X`, the same two demands the wildcard spelling
  names. `PROPULSION` read as `attempts to reference non-existing name(s)
  'PROPULSION'`, the sentence written for a reference to a node that no deck
  declares, and `BOGUS` as `does not accept ID 'BOGUS'`. This is the one
  command whose unknown-token message differs from its siblings', which name
  no set and still read `does not accept ID 'X'`.
- `set_operational_saving_port(*, 0.1)` sets the energy demands a vessel has
  in port, `ELECTRICAL` and `HEAT`. The wildcard previously expanded over
  every `EnergyDemandTypeID` member and so also reached `PROPULSION`, which
  the attribute does not hold, failing the command with the message written
  for a reference to a node that no deck declares.
- The error for a node found in neither the deck nor the default library
  names the deck line and include file of the reference; it opened with a
  bare colon before.
- A default file found by name that does not yield the requested node is
  rejected with an error naming the deck location of the reference, from the
  user branch as well. The user branch previously passed unchecked: a
  reference to the node then failed with a bare `KeyError`, and an `Import`
  of it silently imported nothing.
- A reference whose type is not a node type, such as `Foo("x")`, is reported
  as a deck error at its line. It previously surfaced as an attribute type
  mismatch or, written as a command argument, as an unhandled `KeyError`.
- `InitialSplit` and `ConditionDistribution` report the rescale they perform on
  a list that does not sum to 1. Both console messages, and `InitialSplit`'s
  reference-manual entry, said the list was "normalized to 1 by equal
  fractions", where the rescale is proportional.
- An error naming a `Variable` node identifies it as `Variable("name")`, the
  way the deck wrote it, like every other node. It previously printed the
  node's value instead, and failed with `AttributeError` while no value was
  assigned — which is exactly when the missing-value error needs the name.
- Computing the expected fleet fuel demand no longer raises a `TypeError`
  when a simulation defines no fleets (`add_dicts` with no arguments returns
  an empty dict).
- The reference manual documented two port report properties under names that
  never resolved (`BunkerEquivalentWTT`, `BunkerTotalEquivalentWTT`); the
  working names are `EquivalentBunkerWtt` and `TotalEquivalentBunkerWtt`.
- `set_initial_technology_share` values built from expressions (e.g.
  `<0.5 * Curve("uptake")>`) are honored; the seeding previously accepted
  only direct node references and silently ignored anything else, so
  expression-valued shares left the fleet without initial technology.
- `Levy`/`Regulation` values assigned through `set_fuel_wtt`, `set_fuel_ttw`,
  and `set_global_warming_potential` now survive timeline progression. The
  per-time-step dependency pass unconditionally re-seeded these dictionaries
  to `None`, so the overrides applied only until the first time step and then
  silently fell back to the `Emission` nodes' values. Results change for any
  deck using these commands, including `simulations/examples/example_1`
  (CII and EU-ETS overrides).
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
- Fuel-conversion expenses are booked on the elapsed-years axis. The
  installment schedule was previously anchored at time-step indices, which on
  calendar-date timelines (365/366-day years against the 365.25-day model
  year) dropped or distorted the conversion-year installment.
- Trimming a fuel-cost flow to an increment's remaining lifetime in the
  conversion business case no longer prorates the shared flow in place;
  repeated trims could double-prorate a year when two increments' horizons
  rounded to the same length (reachable only with sub-year time steps — no
  committed deck is affected). The float-fuzz rounding that guarded this
  trim now sits in the shared `get_flow_size`/`get_flow_residual`
  primitives, so every flow-sizing caller quantizes lifetimes at the same
  5-decimal precision.
- The expected fuel-delivery cost from plant to port is production-levelized
  over the same window as the levelized cost of production: rates and
  distance are sampled over the plant's operating years (construction lead
  time excluded, re-anchored at every forward step) and levelized against
  the discounted production flow. It was previously age-levelized with the
  cost flow spanning the remaining simulation timeline but the leveling flow
  spanning the plant lifetime, so even a constant per-ton rate did not
  levelize to itself and the delivery cost drifted with the remaining
  horizon. Results change for any deck assigning `FuelTransport` on a plant.
- A user default file that pulls another library node before importing its own
  name now still overlays the installation node of that name. The parser
  cleared its default-reading state after the nested pull instead of restoring
  it, so the user file re-entered itself and the parse failed with "the name is
  already in use"; the overlay idiom held only when the self-`Import` came
  first. The same state also decides which error a default file containing a
  timeline statement reports.
- A value whose kind an attribute does not accept now fails with the
  attribute's allowed-types message, located to the deck line like every other
  assignment error. An enum token or a stray word where a scalar or node
  reference belongs (`Capex = FLAT`), or a table body pasted into a value slot,
  previously fell through every accepted kind into an internal bounds call and
  died as an `AttributeError`, with no indication of where in the deck. A table
  is named by kind, as a list already was, rather than echoed row by row.
- An attribute error naming a value it does not accept always names the value,
  by kind where the value has one: an `int` or a `bool` reaching a scalar
  attribute reads `only allows assignment of scalars, but got integer` instead
  of the self-contradicting `but got 3`, and a node reference reaching an
  attribute that takes no node is named where the value was omitted entirely.
  A stray token, a node the attribute does not accept and `None` are echoed,
  as their own text is what identifies them.
- An integer attribute accepts a value written just off a whole number equally
  on either side of it: `2.999999` is 3, where truncation toward zero
  previously rejected it while accepting `3.000001`.
- A list length violation reads "at least"/"at most" for a bounded length,
  which is what the bound means; it said "more than"/"less than" for a length
  equal to the bound, which the check accepts.
- An invalid boolean keyword in a command (`set_allow_vessel("name", MAYBE)`,
  and likewise `set_newbuild_available`, `set_conversion_available`,
  `set_include_vessel`, `set_bunkering_allowed` and `set_allow_plant`) fails as
  an assignment error located to the deck line, instead of being reported as a
  reference to a non-existing name. The same keyword written as an attribute
  (`AllowSpeedManagement = MAYBE`) already failed at its deck line, and now
  names the keywords it accepts: `only allows assignment of TRUE or FALSE, but
  got MAYBE`, where it read `does not accept ID 'MAYBE'`.
- A command key that is an enum member must be one the attribute's dictionary
  was prepopulated with. `set_operational_saving_port(PROPULSION, 0.1)`
  silently created an entry for a demand type that is not in port (the command
  covers electrical and heat, as its reference-manual page now states), which
  nothing then read; it is now a deck error. No committed deck assigns it.
- The DSL reference names the axes of a Surface and a Timetable table the way
  they are read: the header row is the y-axis, and the first cell of every
  subsequent row is the x-axis. It had them the other way round, so a table
  written from the manual came out transposed, and the note on a timetable's
  float axis named the wrong axis for the dates it replaces.
- The DSL reference states that a wildcard in an enum-typed command argument
  expands over every member of the enum class, not over the subset of members
  the command accepts.
- `ConditionDistribution`'s reference-manual entry states the proportional
  rescale of a list whose positive total is not 1, which it required to sum to
  1 exactly; both it and `InitialSplit`'s entry name the 1% deviation above
  which the rescale is logged, and that a list summing to 0 is accepted
  unchanged.
- The tied-capital expectation store of plants and vessels is zero-initialized
  like its sibling list storages, and both `get_tied_capital` getters declare
  the `np.ndarray` they now always return. An unwritten slot previously held
  `None`, reachable through an `InitialAgeDistribution` whose curve starts at a
  negative age: that read one index past the current time step, where the plant
  store already returned a real array and the charter rate zero, while the
  vessel store raised an `AttributeError`. Such an increment now contributes
  zero tied capital. No committed deck is affected.

## [1.0.0] - 2026-07-16

Initial public release of Navigate, an open-source sectoral integrated
assessment model for simulating transitions of the maritime industry.

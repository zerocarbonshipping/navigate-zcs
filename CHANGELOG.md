<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Removed
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
- Report properties `ShorePowerEnergy`, `ShorePowerExpenses`, and
  `ShorePowerEmission`, available at vessel, fleet, and global level.
- Behavior guardrail test suite (`tests/guardrails/`): committed decks that
  each isolate one desired model behavior, enforced by property assertions
  paired with intent prose (`BEHAVIOR.md` per deck); run via
  `make test-guardrails`. Initial decks: `no_incentive`,
  `supply_constrained`, `supply_then_demand_constrained`.
- `navigate.testing.simulation`: shared in-process simulation runner and
  universal result invariants, used by the attribute and guardrail suites.
- `FleetProfile.get_fleet_technology_uptake`: fleet-wide technology uptake
  (existing-vessel-weighted), shared by the technology_uptake plot and the
  guardrail tests.

## [1.0.0] - 2026-07-16

Initial public release of Navigate, an open-source sectoral integrated
assessment model for simulating transitions of the maritime industry.

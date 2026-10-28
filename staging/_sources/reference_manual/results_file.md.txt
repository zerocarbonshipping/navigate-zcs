<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Results file

Every run writes its full results to one Parquet file, `<deck>.parquet` next to
the deck. `--name` and `--output-dir` change its name and folder, and a run with
`--set` writes it into the `parquets` subfolder of that folder. Open it with
[Lantern](https://github.com/zerocarbonshipping/lantern-zcs) to browse the
plots, or read it with any Parquet reader, for example polars, pandas or DuckDB:

```python
import polars as pl

results = pl.read_parquet("my_deck.parquet")
emissions = results.filter(pl.col("attribute") == "total_equivalent_wtw", pl.col("kind") == "global")
```

The results file holds every result of every node that holds results, and
nothing else. Node inputs, such as a fleet's trade target, are not in it, except
the fuel and emission constants the results were converted with, which the
[metadata](#metadata) holds.

## Table

The table is long: one row per series and date. A series whose values are all
below 1e-5 in magnitude or missing is left out.

| Column | Type | Content |
|---|---|---|
| `kind` | string | `global`, `fleet`, `vessel`, `port`, `plant`, `producer`, `regulation` or `levy` |
| `node` | string | Node name; empty for `global` |
| `attribute` | string | Result name, e.g. `consumed_energy`, `total_equivalent_wtw`, `in_fleet` |
| `key1` | string or missing | First key of a result kept per fuel, fuel type, vessel, ... |
| `key2` | string or missing | Second key of a result kept per pair, e.g. (fuel, emission) |
| `date` | date | Date of the time step |
| `value` | 32-bit float or missing | Value, to about seven significant digits; `true`/`false` results are 1 and 0. Missing marks a value that is not set or has no bound, such as a feed constraint without limit |

Keys that are identifiers, such as fuel types or energy demand types, are
written by name (`OIL`, `PROPULSION`, see [Appendix: IDs](appendix_ids.md)). The
attributes of each kind are listed under [Results](#results).

Values are per year where the unit says so. The results that count what
happened in a time step, `newbuilds`, `scrap`, `fuel_conversions`,
`newbuild_power`, `scrapped_power`, `fuel_converted_power`, `development` and
`computational_time`, are divided by the length of the step in years of 365.25
days, the first step counting as one year.

## Metadata

The Parquet key-value metadata holds a JSON document under the key `navigate`:

| Key | Content |
|---|---|
| `schema_version` | Version of this layout, currently `1`. It changes when a reader has to change. |
| `navigate_version` | Navigate version that wrote the file |
| `deck` | Name of the run: the deck's file name without extension, or the name given with `--name` |
| `created` | Time the file was written, UTC, ISO 8601 |
| `params` | The [placeholder](dsl_reference.md#placeholders) values given with `--set`, as text, by name; empty without any |
| `units` | Unit of each attribute, e.g. `"consumed_energy": "GJ/year"`. `measure` means the unit of the regulation's measure. |
| `constants` | The run's constants: `lower_heating_value` per fuel, GJ/t; `fuel_type` per fuel; `liquid_market_fuels`; `global_warming_potential` per emission at `emissions_lifetime`, years |
| `plant_fuel` | The fuel each plant produces |

A per-ton result converts to per energy with the heating value of its fuel: a
port's `bunker_price` divided by `lower_heating_value` of the fuel in `key1` is
the price in USD/GJ, and a plant's `investment_cost` divided by the heating value
of its `plant_fuel` is the cost in USD/GJ.

## Results

This section lists every series a results file can hold. A series is one
`kind`, `node`, `attribute`, `key1` and `key2`, and has a row for every date
of the run:

```python
consumed = results.filter(
    pl.col("kind") == "fleet",
    pl.col("node") == "bulk_carrier",
    pl.col("attribute") == "consumed_energy",
    pl.col("key1") == "fossil_fuel_oil",
)
```

The tables name a series by `kind.attribute`, the way Lantern's plot catalogue
does: `fleet.consumed_energy` stands for the series with `kind` `fleet` and
`attribute` `consumed_energy`, one per fleet and fuel. A row that names several
kinds describes the attribute in each of them.

`global` holds one series per attribute and key, with no node. Every other
kind holds one per node of that type in the run. That means every Fleet,
Vessel, Port, Plant, Producer, Regulation and Levy the deck uses, including
those it loads from the assumptions library.

A series is written only when some date of it holds a value of at least 1e-5
in magnitude. The *Present when* column says what a run needs for that. If the
run doesn't meet it, the series is left out of the file, so filtering for it
returns no rows. A series that is in the file can still be missing at some
dates, as that column says.

Some rules hold throughout:

- **Vessel results describe one ship.** A `vessel` series is one ship of
  that type, regulation results per vessel included. The fleet sums its
  vessel types, each weighted by its `existing_vessels`, and `global` sums
  the fleets. Speeds, rates, savings, shares and intensities are not summed:
  each kind computes its own from its totals.
- **The first date sets up the run.** The first time step starts the fleets
  and production and runs the bunkering. Newbuilds, scrapping, fuel
  conversions, technology installation, speed management and plant
  development start at the second date. Their counts are 0 at the first date,
  and the results they write are missing there.
- **The keys hold names.** The *Keys* column names what `key1` holds and,
  after the comma, `key2`:
  - *fuel*, *emission*, *vessel*, *technology*, *regulation* and *levy* are
    node names.
  - *feed* is a Feedstock or Process name.
  - *fuel type* is a [FuelTypeID](appendix_ids.md#fueltypeid). On a vessel
    it is the vessel's primary fuel type, so `installed_power` keyed `OIL`
    is the power of the oil-fuelled vessels.
  - *energy demand* is an
    [EnergyDemandID](appendix_ids.md#energydemandid). In port it is only
    `ELECTRICAL` or `HEAT`.
  - *timing* is a [TimingID](appendix_ids.md#timingid).

### Energy demand

| Series | Unit | Keys | Content | Present when |
|---|---|---|---|---|
| `global.raw_energy_sea`<br>`fleet.raw_energy_sea`<br>`vessel.raw_energy_sea` | `GJ/year` | energy demand | Energy demand at sea before operational measures and technologies. | Each demand the vessels have at sea |
| `global.raw_energy_port`<br>`fleet.raw_energy_port`<br>`vessel.raw_energy_port` | `GJ/year` | energy demand | Energy demand in port before operational measures and technologies. | Vessels with a demand in port |
| `global.raw_energy`<br>`fleet.raw_energy`<br>`vessel.raw_energy` | `GJ/year` | | `raw_energy_sea` plus `raw_energy_port`. | Always |
| `global.operational_energy_sea`<br>`fleet.operational_energy_sea`<br>`vessel.operational_energy_sea` | `GJ/year` | energy demand | Energy demand at sea after operational measures, before technologies. | As `raw_energy_sea` |
| `global.operational_energy_port`<br>`fleet.operational_energy_port`<br>`vessel.operational_energy_port` | `GJ/year` | energy demand | Energy demand in port after operational measures, before technologies. | As `raw_energy_port` |
| `global.operational_energy`<br>`fleet.operational_energy`<br>`vessel.operational_energy` | `GJ/year` | | `operational_energy_sea` plus `operational_energy_port`. | Always |
| `global.energy_sea`<br>`fleet.energy_sea`<br>`vessel.energy_sea` | `GJ/year` | energy demand | Energy demand at sea after operational measures and technologies. | As `raw_energy_sea` |
| `global.energy_port`<br>`fleet.energy_port`<br>`vessel.energy_port` | `GJ/year` | energy demand | Energy demand in port after operational measures and technologies. | As `raw_energy_port` |
| `global.energy`<br>`fleet.energy`<br>`vessel.energy` | `GJ/year` | | `energy_sea` plus `energy_port`. | Always |
| `global.baseline_energy`<br>`fleet.baseline_energy`<br>`vessel.baseline_energy` | `GJ/year` | | `raw_energy` at the first date, scaled by the growth of `cargo_miles` since: the energy the transport work would take at the first date's intensity. `global` sums the fleets'. | Vessels at the first date; 0 for a fleet that starts empty |
| `global.saving`<br>`fleet.saving`<br>`vessel.saving` | `-` | energy demand | 1 − energy / raw energy of the demand, in port included for `ELECTRICAL` and `HEAT`. | Operational measures or technologies reduce the demand |
| `global.speed_energy_intensity_saving`<br>`fleet.speed_energy_intensity_saving`<br>`vessel.speed_energy_intensity_saving` | `-` | | 1 − `raw_energy` / `baseline_energy`: the reduction of energy intensity from speed changes. | `raw_energy` departs from the baseline, through speed management or a changing fleet mix |
| `global.operational_energy_intensity_saving`<br>`fleet.operational_energy_intensity_saving`<br>`vessel.operational_energy_intensity_saving` | `-` | | 1 − `operational_energy` / `baseline_energy`: from speed and operational measures. | As above, or operational measures apply |
| `global.technology_energy_intensity_saving`<br>`fleet.technology_energy_intensity_saving`<br>`vessel.technology_energy_intensity_saving` | `-` | | 1 − `energy` / `operational_energy`: from technologies. | Technologies are installed |
| `global.energy_intensity_saving`<br>`fleet.energy_intensity_saving`<br>`vessel.energy_intensity_saving` | `-` | | 1 − `energy` / `baseline_energy`: from speed, operational measures and technologies. | Any of the three above |

### Fuel consumption

| Series | Unit | Keys | Content | Present when |
|---|---|---|---|---|
| `global.consumed_energy`<br>`fleet.consumed_energy`<br>`vessel.consumed_energy` | `GJ/year` | fuel | Fuel burnt, in energy. | Each fuel burnt |
| `global.fuel_type_energy`<br>`fleet.fuel_type_energy`<br>`vessel.fuel_type_energy` | `GJ/year` | fuel type | `consumed_energy` summed by the fuels' type. | Each fuel type burnt |
| `global.total_consumed_energy`<br>`fleet.total_consumed_energy`<br>`vessel.total_consumed_energy` | `GJ/year` | | All fuels plus shore power. | Always |
| `global.converter_energy`<br>`fleet.converter_energy`<br>`vessel.converter_energy` | `GJ/year` | fuel type, fuel | Fuel burnt by the vessels of a primary fuel type. | Each pair burnt |
| `global.pilot_fuel_share`<br>`fleet.pilot_fuel_share`<br>`vessel.pilot_fuel_share` | `-` | fuel type | Share of the energy the vessels of a primary fuel type burn that is a fuel of another type: their pilot fuel. | Vessels burn a pilot fuel. The share is also 1 for every fuel type whose vessels burn nothing, so read it only for the fuel types in `converter_energy` |

### Expenses and compliance

| Series | Unit | Keys | Content | Present when |
|---|---|---|---|---|
| `global.fuel_expenses`<br>`fleet.fuel_expenses`<br>`vessel.fuel_expenses` | `USD/year` | fuel | Bunker price times the fuel bunkered. | Each fuel bunkered |
| `global.levy_expenses`<br>`fleet.levy_expenses`<br>`vessel.levy_expenses` | `USD/year` | fuel | Levies charged on the fuel bunkered; negative for a subsidy. | A Levy charges a fuel bunkered in its Jurisdiction |
| `global.fuel_related_expenses`<br>`fleet.fuel_related_expenses`<br>`vessel.fuel_related_expenses` | `USD/year` | fuel | `fuel_expenses` plus `levy_expenses`. | Each fuel bunkered |
| `global.remedial_expenses`<br>`fleet.remedial_expenses`<br>`vessel.remedial_expenses` | `USD/year` | | Cost of the remedial units the regulations require. | Vessels miss a regulation's threshold |
| `global.flexibility_expenses`<br>`fleet.flexibility_expenses`<br>`vessel.flexibility_expenses` | `USD/year` | | Cost of the flexibility units bought from vessels that over-comply. | A `FLEXIBLE` Regulation's vessels trade units |
| `global.surplus_revenue`<br>`fleet.surplus_revenue`<br>`vessel.surplus_revenue` | `USD/year` | | Revenue from the surplus units sold to vessels that under-comply. | As `flexibility_expenses` |
| `global.regulation_expenses`<br>`fleet.regulation_expenses`<br>`vessel.regulation_expenses` | `USD/year` | | `remedial_expenses` plus `flexibility_expenses` less `surplus_revenue`. | Any of the three |
| `global.total_fuel_expenses`<br>`fleet.total_fuel_expenses`<br>`vessel.total_fuel_expenses` | `USD/year` | | All fuel expenses plus shore power expenses. | Always |
| `global.total_fuel_related_expenses`<br>`fleet.total_fuel_related_expenses`<br>`vessel.total_fuel_related_expenses` | `USD/year` | | `total_fuel_expenses` plus all levy expenses. | Always |
| `global.remedial_units`<br>`fleet.remedial_units`<br>`vessel.remedial_units` | `tCO2e/year` | regulation | Remedial units required, under the regulation's global warming potentials. | As `remedial_expenses` |
| `global.levy_units`<br>`fleet.levy_units`<br>`vessel.levy_units` | `tCO2e/year` | levy | Emissions a levy charged: its charge over its Level. | A Levy with a positive Level charges |

### Emissions

The CO2-equivalents use the model's global warming potentials, which the
[metadata](#metadata) holds.

| Series | Unit | Keys | Content | Present when |
|---|---|---|---|---|
| `global.equivalent_wtt`<br>`fleet.equivalent_wtt`<br>`vessel.equivalent_wtt` | `tCO2e/year` | fuel, emission | Well-to-tank emissions of the fuel bunkered. | Each fuel bunkered and emission it has |
| `global.equivalent_ttw`<br>`fleet.equivalent_ttw`<br>`vessel.equivalent_ttw` | `tCO2e/year` | fuel, emission | Tank-to-wake emissions of the fuel burnt. | As `equivalent_wtt` |
| `global.equivalent_wtw`<br>`fleet.equivalent_wtw`<br>`vessel.equivalent_wtw` | `tCO2e/year` | fuel, emission | `equivalent_wtt` plus `equivalent_ttw`. | As `equivalent_wtt` |
| `global.total_equivalent_wtw`<br>`fleet.total_equivalent_wtw`<br>`vessel.total_equivalent_wtw` | `tCO2e/year` | | All of `equivalent_wtw` plus the shore power emissions. | Always |
| `global.intensity_total_equivalent_wtt`<br>`fleet.intensity_total_equivalent_wtt`<br>`vessel.intensity_total_equivalent_wtt` | `gCO2e/MJ` | | Total well-to-tank emissions per `total_consumed_energy`. | Always |
| `global.intensity_total_equivalent_ttw`<br>`fleet.intensity_total_equivalent_ttw`<br>`vessel.intensity_total_equivalent_ttw` | `gCO2e/MJ` | | Total tank-to-wake emissions per `total_consumed_energy`. | Always |
| `global.intensity_total_equivalent_wtw`<br>`fleet.intensity_total_equivalent_wtw`<br>`vessel.intensity_total_equivalent_wtw` | `gCO2e/MJ` | | `total_equivalent_wtw` per `total_consumed_energy`. | Always |

### Shore power

| Series | Unit | Keys | Content | Present when |
|---|---|---|---|---|
| `global.shore_power_energy`<br>`fleet.shore_power_energy`<br>`vessel.shore_power_energy` | `GJ/year` | | Shore power drawn in port. | Vessels call at a Port with a ShorePowerConnectionShare above 0 |
| `global.shore_power_expenses`<br>`fleet.shore_power_expenses`<br>`vessel.shore_power_expenses` | `USD/year` | | Cost of the shore power, at the port's ShorePowerCost. | As `shore_power_energy`, with a cost |
| `global.shore_power_emission`<br>`fleet.shore_power_emission`<br>`vessel.shore_power_emission` | `t/year` | emission | Emissions of the shore power, well-to-wake, one gas unweighted. Counted in `total_equivalent_wtw`, not in `equivalent_wtw`. | As `shore_power_energy`, with an emission factor |

### Fleet power and costs

| Series | Unit | Keys | Content | Present when |
|---|---|---|---|---|
| `global.installed_power`<br>`fleet.installed_power` | `MW` | fuel type | Installed power of the vessels. | Always |
| `global.newbuild_power`<br>`fleet.newbuild_power` | `MW/year` | fuel type | Installed power of the newbuilds. | Newbuilds |
| `global.scrapped_power`<br>`fleet.scrapped_power` | `MW/year` | fuel type | Installed power scrapped. | Scrapping |
| `global.fuel_converted_power`<br>`fleet.fuel_converted_power` | `MW/year` | fuel type, fuel type | Installed power fuel converted from one type to the other. | Fuel conversions |
| `global.vessel_expenses`<br>`fleet.vessel_expenses` | `USD/year` | | Asset charter of the vessels: their acquisition cost, levelized. | Always |
| `global.technology_expenses`<br>`fleet.technology_expenses` | `USD/year` | | Levelized cost of the installed technologies. | Technologies are installed |
| `global.fuel_conversion_expenses`<br>`fleet.fuel_conversion_expenses` | `USD/year` | | Running cost of the fuel conversions made. | Fuel conversions |
| `global.vessel_related_expenses`<br>`fleet.vessel_related_expenses` | `USD/year` | | `vessel_expenses` plus `technology_expenses` plus `fuel_conversion_expenses`. | Always |
| `global.expenses`<br>`fleet.expenses` | `USD/year` | | `total_fuel_related_expenses` plus `regulation_expenses` plus `vessel_related_expenses`. | Always |
| `global.vessel_tied_capital`<br>`fleet.vessel_tied_capital` | `USD` | | Capital tied up in the vessels, depreciated linearly. | Always |
| `global.weighted_average_age`<br>`fleet.weighted_average_age` | `years` | fuel type | Power-weighted average age of the vessels. | Each fuel type in the fleet |
| `global.fuel_type_capacity`<br>`fleet.fuel_type_capacity` | `GJ/year` | fuel type | Fuel the vessels could burn, at their minimum pilot fuel share. | Each fuel type the vessels can burn |

### Fleet composition

| Series | Unit | Keys | Content | Present when |
|---|---|---|---|---|
| `fleet.trade` | `cargo-miles/year` | | Trade satisfied; at the first date, the fleet's trade. | Always |
| `fleet.existing_vessels` | `vessels` | vessel | Number of vessels of each type in the fleet. | Each vessel type ever in the fleet |
| `fleet.newbuilds` | `vessels/year` | vessel | Vessels built. | Newbuilds |
| `fleet.scrap` | `vessels/year` | vessel | Vessels scrapped, primary and secondary. | Scrapping |
| `fleet.fuel_conversions` | `vessels/year` | vessel, vessel | Vessels fuel converted from one type to the other. | Fuel conversions |
| `fleet.technology_uptake` | `-` | vessel, technology | Share of the vessels of a type carrying the technology. | The fleet has Technologies |
| `fleet.newbuild_technology_uptake` | `-` | vessel, technology | Share of the newbuilds of a type carrying the technology. | As `technology_uptake` |
| `fleet.retrofit_technology_uptake` | `-` | vessel, technology | Share of the vessels of a type retrofitted with the technology. | Retrofits, at the dates RetrofitFrequency allows |
| `fleet.fleet_technology_uptake` | `-` | technology | `technology_uptake` averaged over the vessel types, weighted by `existing_vessels`. | As `technology_uptake` |

### Transport work, speeds and freight rate

A fleet's speeds are its vessels' averaged by `existing_vessels`.

| Series | Unit | Keys | Content | Present when |
|---|---|---|---|---|
| `fleet.cargo_miles`<br>`vessel.cargo_miles` | `cargo-miles/year` | | Transport work performed. | Always |
| `fleet.reference_speed`<br>`vessel.reference_speed` | `knots` | | Speed the Route sets, weighted by the time at sea. | Always |
| `fleet.minimum_speed`<br>`vessel.minimum_speed` | `knots` | | Lowest speed attainable on the route. | The fleet has AllowSpeedManagement; missing at the first date |
| `fleet.maximum_speed`<br>`vessel.maximum_speed` | `knots` | | Highest speed attainable on the route. | As `minimum_speed` |
| `fleet.actual_speed`<br>`vessel.actual_speed` | `knots` | | Speed sailed, averaged over the route. | As `minimum_speed` |
| `fleet.optimal_speed`<br>`vessel.optimal_speed` | `knots` | | Speed that speed management aims for; `actual_speed` moves toward it by at most the MaximumSpeedChange. | As `minimum_speed` |
| `fleet.lowest_speed`<br>`vessel.lowest_speed` | `knots` | | Lowest speed sailed on the route. | As `minimum_speed` |
| `fleet.highest_speed`<br>`vessel.highest_speed` | `knots` | | Highest speed sailed on the route. | As `minimum_speed` |
| `fleet.instantaneous_freight_rate`<br>`vessel.instantaneous_freight_rate` | `USD/cargo-mile` | | For a vessel: the cost of a ship ordered at the date, levelized over the cargo-miles it carries. The cost is its asset charter plus the fuel, levy, regulation and technology expenses it actually has. For a fleet: the `cargo_charter_rate` of those vessels summed over the fleet, per cargo-mile they carry. | Missing where the vessel type leaves the fleet within the ship's lead time and lifetime; for a fleet, where none of its vessel types has a rate |

### Vessel

| Series | Unit | Keys | Content | Present when |
|---|---|---|---|---|
| `vessel.in_fleet` | `-` | | 1 where the fleet holds vessels of the type, 0 elsewhere. | The type is ever in the fleet |
| `vessel.lifetime` | `years` | | Lifetime. | Always |
| `vessel.lead_time` | `years` | | Lead time, used only in the levelized costs. | The vessel has a LeadTime |
| `vessel.asset_charter_rate` | `USD/year` | | What an operator pays the owner: the acquisition cost of a ship ordered at the date, levelized over its operating years. | Always |
| `vessel.cargo_charter_rate` | `USD/year` | | What a cargo owner pays the operator: the asset charter rate plus the fuel, levy, regulation and technology expenses, levelized over the operating years. They are the expenses the ship actually has where `instantaneous_freight_rate` is present, and the ones expected when ordering elsewhere. | Missing at the first date where `instantaneous_freight_rate` is |
| `vessel.investment_freight_rate` | `USD/cargo-mile` | | Freight rate expected when ordering a ship at the date, which the newbuild choice weighs. | Missing at the first date |
| `vessel.technology_cost` | `USD/year` | | Levelized cost of the installed technologies, averaged over the fleet's vessels of the type. | Technologies are installed |
| `vessel.investment_signal_technology` | `USD/GJ` | | Energy-weighted average of the smoothed energy-conservation duals over the TechnologyHorizon: the value of a GJ saved, which drives technology installation. | Missing at the first date |
| `vessel.investment_signal_speed` | `USD/GJ` | | The same over the SpeedHorizon, which drives speed management. | Missing at the first date |
| `vessel.speed_energy_saving` | `-` | | 1 − `raw_energy` / `raw_energy` at the first date. | `raw_energy` changes |
| `vessel.operational_energy_saving` | `-` | | 1 − `operational_energy` / `raw_energy` at the first date. | As above, or operational measures apply |
| `vessel.technology_energy_saving` | `-` | | Equal to `technology_energy_intensity_saving`. | Technologies are installed |
| `vessel.energy_saving` | `-` | | 1 − `energy` / `raw_energy` at the first date. | Any of the three above |

### Bunkering

The energies are the masses times the fuel's `lower_heating_value`.

| Series | Unit | Keys | Content | Present when |
|---|---|---|---|---|
| `global.bunker_mass`<br>`port.bunker_mass` | `t/year` | fuel | Fuel bunkered. | Each fuel bunkered |
| `global.bunker_supply_mass`<br>`port.bunker_supply_mass` | `t/year` | fuel | Fuel available for bunkering. | A fuel from producers that reaches the port. A liquid-market fuel only at a port that allows it with a bunkering limit, and never in `global` |
| `global.bunkering_limit_mass`<br>`port.bunkering_limit_mass` | `t/year` | fuel | Limit the port's infrastructure puts on bunkering. | The Port has `set_bunkering_limit` for the fuel; missing at dates without one. Never in `global` |
| `global.bunker_energy`<br>`port.bunker_energy` | `GJ/year` | fuel | `bunker_mass` in energy. | As `bunker_mass` |
| `global.bunker_supply_energy`<br>`port.bunker_supply_energy` | `GJ/year` | fuel | `bunker_supply_mass` in energy. | As `bunker_supply_mass` |
| `global.bunkering_limit_energy`<br>`port.bunkering_limit_energy` | `GJ/year` | fuel | `bunkering_limit_mass` in energy. | As `bunkering_limit_mass` |

### Port

| Series | Unit | Keys | Content | Present when |
|---|---|---|---|---|
| `port.bunkering_allowed` | `-` | fuel | 1 where the port allows bunkering the fuel, 0 elsewhere. | The fuel is allowed at some date |
| `port.bunker_price` | `USD/t` | fuel | Bunker price. | A liquid-market fuel the port allows, or a fuel from producers that reaches the port; 0 at other dates |
| `port.bunker_wtt` | `t/t` | fuel, emission | Well-to-tank emissions per ton of the fuel bunkered, one gas unweighted. | As `bunker_price` |
| `port.equivalent_bunker_wtt` | `tCO2e/t` | fuel, emission | `bunker_wtt` in CO2-equivalents. | As `bunker_price` |

### Production

| Series | Unit | Keys | Content | Present when |
|---|---|---|---|---|
| `global.production_energy`<br>`producer.production_energy` | `GJ/year` | fuel | Fuel produced. | Each fuel the plants produce |
| `global.production_type_energy`<br>`producer.production_type_energy` | `GJ/year` | fuel type | `production_energy` summed by the fuels' type. | As `production_energy` |
| `global.feed_mass`<br>`producer.feed_mass` | `t/year` | feed | Feed used. | Plants in production use the feed |
| `global.feed_constraint`<br>`producer.feed_constraint` | `t/year` | feed | Availability of the feed. | The Producer has `set_feed_constraint` for the feed. Never in `global` |
| `global.plant_tied_capital`<br>`producer.plant_tied_capital` | `USD` | | Capital tied up in the plants, depreciated linearly. | Plants in production |

### Producer

| Series | Unit | Keys | Content | Present when |
|---|---|---|---|---|
| `producer.maximum_development` | `plants/year` | | Plants the producer can add to its pipeline, its MaximumDevelopment. | Always |
| `producer.development` | `plants/year` | | Plants added to the pipeline; at the first date, the plants in the initial pipeline. | Plants are developed |
| `producer.fair_share_fuel_fraction` | `-` | fuel | Share of the expected shortfall of a fuel the producer is asked to supply: its share of the development potential of the producers that can make the fuel. | Each fuel the producer can make, while it has potential |

### Plant

The fuel a plant makes is in the [metadata](#metadata) under `plant_fuel`.

| Series | Unit | Keys | Content | Present when |
|---|---|---|---|---|
| `plant.investment_cost` | `USD/t` | | Levelized production cost of a plant invested in at the date. | Always |
| `plant.instantaneous_cost` | `USD/t` | | Production-weighted average cost of the plants of this type producing. | Missing at dates the plant type is not expected to produce |
| `plant.equivalent_investment_wtt` | `tCO2e/t` | emission | Well-to-tank emissions per ton of fuel from a plant invested in at the date. | Each emission of the fuel |
| `plant.equivalent_instantaneous_wtt` | `tCO2e/t` | emission | Production-weighted average well-to-tank emissions per ton of fuel. | As `instantaneous_cost` |

### Regulation

A regulation writes results only at dates it is Active. `measure` is the unit
of its Measure. CO2-equivalents use its own global warming potentials.

| Series | Unit | Keys | Content | Present when |
|---|---|---|---|---|
| `regulation.remedial_cost` | `USD/tCO2e` | | Cost of a remedial unit, its RemedialCost. | Always |
| `regulation.flexibility_cost` | `USD/tCO2e` | | Price of a flexibility unit. | A `FLEXIBLE` scheme |
| `regulation.vessel_threshold` | `measure` | vessel | Threshold of each policed vessel type. | Each policed vessel type with a threshold |
| `regulation.shared_threshold` | `measure` | | Threshold of the pool: the vessel thresholds averaged by measure. | A `FLEXIBLE` scheme with an `ABSOLUTE` or `INTENSITY` Measure |
| `regulation.adjusted_vessel_threshold` | `measure` | vessel | Threshold after adjustment for non-compliance; a vessel that complies keeps its threshold. | AllowThresholdAdjustment |
| `regulation.adjusted_shared_threshold` | `measure` | | Threshold of the pool after adjustment. | A `FLEXIBLE` scheme with AllowThresholdAdjustment; missing at dates the pool complies |
| `regulation.vessel_allowance` | `tCO2e/year` | vessel | Emissions allowed per vessel. | Policed vessel types in a fleet that call at a port of the Jurisdiction |
| `regulation.shared_allowance` | `tCO2e/year` | | Emissions allowed across the policed vessels. | Always |
| `regulation.vessel_compliance` | `measure` | vessel | Measure achieved per vessel. | As `vessel_allowance` |
| `regulation.shared_compliance` | `measure` | | Measure achieved across the policed vessels. | An `ABSOLUTE` or `INTENSITY` Measure |
| `regulation.vessel_units` | `tCO2e/year` | vessel | Emissions per vessel. | As `vessel_allowance` |
| `regulation.shared_units` | `tCO2e/year` | | Emissions across the policed vessels. | Always |
| `regulation.surplus_units` | `tCO2e/year` | | Surplus units generated. | A `FLEXIBLE` scheme |
| `regulation.flexibility_units` | `tCO2e/year` | | Flexibility units used. | A `FLEXIBLE` scheme |
| `regulation.remedial_units` | `tCO2e/year` | | Remedial units required. | Vessels, or a `FLEXIBLE` pool, miss the threshold |
| `regulation.non_compliance_units` | `tCO2e/year` | | `flexibility_units` plus `remedial_units`. | Either of the two |
| `regulation.surplus_revenue` | `USD/year` | | Revenue from the surplus units sold. | A `FLEXIBLE` scheme |
| `regulation.flexibility_expenses` | `USD/year` | | Cost of the flexibility units bought. | A `FLEXIBLE` scheme |
| `regulation.remedial_expenses` | `USD/year` | | Cost of the remedial units. | As `remedial_units` |

### Levy

| Series | Unit | Keys | Content | Present when |
|---|---|---|---|---|
| `levy.collected` | `USD/year` | | Revenue collected; negative where the levy pays a subsidy. | The Levy is Active and charges a fuel bunkered in its Jurisdiction |

### Run

| Series | Unit | Keys | Content | Present when |
|---|---|---|---|---|
| `global.computational_time` | `s/year` | timing | Computational time of the time step, without initialization and reading events, per phase of the step. | Always |

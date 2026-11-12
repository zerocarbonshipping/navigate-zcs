<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Bio-methane plants (`plant_methane_bio`) read their lifetime from a new
  Forecast `lifetime_plant_methane_bio` instead of sharing
  `lifetime_plant_methane` with the electro-methane plants. The new Forecast
  carries the same value as before (30 years), so results do not change; the
  two plant families can now be given different lifetimes.
- Bio plants read their lead time from one Forecast per plant
  (`lead_time_plant_ethanol_bio`, `lead_time_plant_methanol_bio_gasification`,
  `lead_time_plant_methane_bio`) instead of the shared `lead_time_plant_bio`,
  which is removed. Each new Forecast carries the same value as before
  (3 years), so results do not change.
- Biogas feedstock (`feedstock_biogas`) moves on a new Transport
  `truck_wet_organics`. Its emission factor is `truck_emissions` times the new
  Variable `feedstock_biogas_wet_mass_factor` (wet ton per dry ton). The plant
  feed mass is in dry tonnes and the truck moves wet tonnes. The Variable
  carries 1.0, so results do not change until a value is supplied.

### Fixed
- Parse errors now name keywords as the grammar spells them. Lark derives
  keyword terminal names from the literal, uppercased, so a misspelled
  `Include` reported "expected INCLUDE" — inviting exactly the spelling the
  grammar rejects. Errors now read "expected 'Include'".

## [1.0.0] - 2026-07-16

Initial public release of Navigate, an open-source sectoral integrated
assessment model for simulating transitions of the maritime industry.

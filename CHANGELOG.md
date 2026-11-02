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

### Fixed
- Parse errors now name keywords as the grammar spells them. Lark derives
  keyword terminal names from the literal, uppercased, so a misspelled
  `Include` reported "expected INCLUDE" — inviting exactly the spelling the
  grammar rejects. Errors now read "expected 'Include'".

## [1.0.0] - 2026-07-16

Initial public release of Navigate, an open-source sectoral integrated
assessment model for simulating transitions of the maritime industry.

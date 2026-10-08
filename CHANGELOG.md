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
- Five vessel segments from segment taxonomy v1: `chemical_tanker_40k_dwt`,
  `ropax_25k_gt`, `ferry_small_2k_gt`, `lng_carrier_174k_cbm` and
  `lpg_carrier_84k_cbm`, registered in the default fleet, voyage, converter
  availability, domestic/international split, CII and plot labels. Their
  structure is cloned from `tanker_47k_dwt`, `ferry` and
  `gas_carrier_100k_cbm`; value leaves are generated from provisional
  assumption records; leaves without a public source are inherited from the
  parent segment and say so in their header.

### Removed
- The `gas_carrier_100k_cbm` segment, replaced by `lng_carrier_174k_cbm` and
  `lpg_carrier_84k_cbm` (segment taxonomy v1).
- The `ferry` segment, replaced by `ropax_25k_gt` and `ferry_small_2k_gt`
  (segment taxonomy v1).

### Fixed
- Parse errors now name keywords as the grammar spells them. Lark derives
  keyword terminal names from the literal, uppercased, so a misspelled
  `Include` reported "expected INCLUDE" — inviting exactly the spelling the
  grammar rejects. Errors now read "expected 'Include'".

## [1.0.0] - 2026-07-16

Initial public release of Navigate, an open-source sectoral integrated
assessment model for simulating transitions of the maritime industry.

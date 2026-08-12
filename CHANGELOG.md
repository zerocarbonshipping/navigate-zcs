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
- Behavior guardrail test suite (`tests/guardrails/`): committed decks that
  each isolate one desired model behavior, enforced by property assertions
  paired with intent prose (`BEHAVIOR.md` per deck); run via
  `make test-guardrails`. Initial decks: `no_incentive`,
  `supply_constrained`, `supply_then_demand_constrained`.
- `navigate.testing.simulation`: shared in-process simulation runner and
  universal result invariants, used by the attribute and guardrail suites.

## [1.0.0] - 2026-07-16

Initial public release of Navigate, an open-source sectoral integrated
assessment model for simulating transitions of the maritime industry.

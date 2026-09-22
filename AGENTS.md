<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# Working in this repository

Navigate is a sectoral integrated assessment model of the maritime industry's
transition to zero-carbon shipping. It is a command-line tool: `navigate
deck.nav` runs a simulation written in a small DSL (a `.nav` deck plus `.inc`
includes, importing assumptions from a data directory) and writes its log,
reports and plots beside the deck. The external contract is the DSL, the CLI
flags and the output files; the Python internals are not a public API. Users
are researchers who write decks; contributors change the Python.

## Where things are described

- `ARCHITECTURE.md` — the model's structure: packages and layering, how
  results flow between modules, and the places the DSL surface lives. Read it
  before changing code.
- `CODESTYLE.md` — the conventions ruff and mypy cannot check. The lint and
  type configuration is the arbiter for everything mechanical.
- `docs/reference_manual/` — the DSL and every node's attributes and
  commands as users read them. It is hand-written; nothing generates it from
  the code.
- `tests/README.md` — which suite answers which question; each suite's
  conventions are in its own README.
- `CONTRIBUTING.md` — branches, pull requests and CHANGELOG entries.
- An `AGENTS.md` beside the code in `navigate/core/nodes/`,
  `navigate/parser/`, `navigate/bunker/`, `navigate/output/plots/` and
  `tests/` holds that area's conventions. Read the one for the area you touch.

## Environment and verification

- `make pip-setup` builds a `.venv` for the checkout you are in; every
  checkout, including a git worktree, gets its own. `make help` lists the
  targets.
- CI runs `make lint` and every test suite except the guardrails on each pull
  request.
- Test decks run in seconds. The reference scenarios under
  `simulations/scenarios/` take about 25 minutes and are not tests.
- A run writes to fixed paths beside its deck, so never run the same deck, or
  the same simulation suite, twice at once in one checkout.
- Guardrail failures are domain findings, so that suite is not a gate and is
  not always green. Before a change that can move results, run it and note the
  failing identities; afterwards compare identities, never counts. A new
  failure is something to report, not a threshold to adjust.

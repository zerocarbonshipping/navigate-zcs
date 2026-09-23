<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Working on Navigate

<!-- Skeleton: headings and keyword bullets, agreed before the text is
written. Each bullet becomes one or two sentences; nothing is added without
observed need. -->

- Navigate in one line: sectoral integrated assessment model of the maritime
  transition; a Python 3.13 package driven by DSL decks and assumption data
- What this file holds: the document map, the layout, the commands, the rules
  that apply to every change; detail lives in the linked files

## Documentation map

- `README.md` — install, run, CLI flags, licence split
- `ARCHITECTURE.md` — package map, layering, data-flow invariants, naming;
  read before touching `navigate/`
- `CODESTYLE.md` — conventions tooling cannot check
- `CONTRIBUTING.md` — how a change gets in: issue first for large features,
  PR expectations, assumption provenance
- `tests/README.md` — which suite a check belongs in, what each suite
  answers, then the suite READMEs
- `docs/reference_manual/` — the DSL and model behaviour as users see it;
  hand-written, no autodoc
- `CHANGELOG.md` — Keep a Changelog, `[Unreleased]`; user-facing changes only
- `make help` — the target list

## Layout

- `navigate/` — the package; CLI entry point `navigate`
- `tests/` — four pytest suites, `helpers/`, test decks
- `assumptions/` — model inputs in the DSL; `defaults/` and `modules/`, each
  `installation/` (shipped) vs `user/` (empty placeholders for overrides);
  the bulk of the repository by file count; CC-BY-4.0 content
- `simulations/` — `scenarios/` (reference runs, ~25 min each, not tests) and
  `examples/` (smoke-run in CI)
- `tutorials/` — teaching decks with example solutions (smoke-run in CI)
- `docs/` — Sphinx/MyST source; published to `gh-pages`, `dev` to `/staging/`
- `syntax/` — editor highlighting for the DSL, includes a committed `.vsix`
- Run output is written beside the deck (`plots*/`, `*.pkl`, `*.xlsx`,
  `*.log`), is gitignored, and two runs of one deck at once collide

## Environment and commands

- Python 3.13 only; pip + setuptools, no lock file; `make pip-setup`
  (`.venv`, editable, dev extras) or `make conda-setup` (env `nav`)
- `make` runs tools from the checkout's own `.venv` when present, so each
  checkout, worktrees included, gets its own setup
- Solvers: HiGHS bundled and default; Gurobi an optional extra needing a
  commercial licence
- Every deck run needs `-d ./assumptions` or `ASSUMPTIONS_DATA_DIR`
- `make lint` = `ruff check`, `ruff format --check`, `mypy navigate`,
  `reuse lint`
- Test targets: `test-unit`, `test-attribute`, `test-guardrails`,
  `test-regression`, `test-tutorials`, `test-examples`, `test-all`; what
  each suite answers, its runtime and its conventions live under `tests/`
- `make docs`
- CI on every PR: Lint, Build package, Run tests (unit, attribute,
  regression, tutorials, examples); guardrails are not in CI, run them
  locally for any change that can move results

## Rules for every change

- Pull requests never target `main`, the release branch; the base is `dev`
  or the integration branch of the larger effort the work belongs to;
  squash merged, so the PR title becomes the commit subject: an imperative
  sentence with no prefix
- Licence header on every new file: Apache-2.0 for code, tests and tooling;
  CC-BY-4.0 for decks, assumptions, docs and figures; `REUSE.toml` when the
  file cannot carry a header; `reuse lint` catches a missing header, not a
  wrong licence
- Ratchet regions in `.ruff.toml` and `mypy.ini`: entries are only ever
  removed; a listed file is cleaned whole-file in a style-only commit; a new
  file never gets an entry
- No lint or type suppressions in code (`noqa`, `type: ignore`); the
  configuration is the arbiter
- `CHANGELOG.md` entry for user-facing changes only: deck behaviour,
  results, CLI, output; Navigate is not a library, so changes to what
  Python code can import are not user-facing
- Assumption value changes carry references or a justification

## What a change touches

- A DSL attribute or command: node setter with docstring → parser table
  (`navigate/parser/_attributes.py` / `_commands.py`) → reference-manual page
  → attribute coverage test; the first two are checked against each other,
  the manual is not
- A change that moves results: explain the difference in the PR; guardrails
  pass locally; baselines regenerated with `make regen-regression` in their
  own commit, never hand-edited; guardrail assertions are never edited to
  pass
- A new non-trivial calculation: a unit test with an independent oracle
  (`tests/unit/README.md`)
- A user-visible behaviour change: reference manual, docstrings, CHANGELOG

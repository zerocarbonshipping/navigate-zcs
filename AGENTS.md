<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Working on Navigate

Navigate is a sectoral integrated assessment model of the maritime
transition: a Python 3.13 package that runs simulation decks written in its
own DSL against a library of assumption data. This file is the entry point
for anyone changing the repository, human or coding agent. It maps the
documents, the layout and the commands, and states the rules that apply to
every change. The detail lives in the files it points to.

## Documentation map

- `README.md` — installing, running, the CLI flags, and which licence
  covers which content.
- `ARCHITECTURE.md` — the package map, the layering, the data-flow
  invariants, where model work lives and the node lifecycle inside
  `navigate/`. Read it before changing code there.
- `CODESTYLE.md` — the conventions the tooling cannot check.
- `.ruff.toml` — this repository's lint rules and ruff settings. They are
  owned here and changed here.
- `CONTRIBUTING.md` — how a change gets in: an issue first for large
  features, what a pull request must carry, provenance for assumption
  changes.
- `tests/AGENTS.md` — what earns a test, which suite it belongs in, and
  the rule that agents propose tests rather than write them. Read it before
  suggesting a test or touching anything under `tests/`.
- `docs/` — the user manual, published as the documentation site.
  `docs/reference_manual/` describes the DSL and the model behaviour as
  users see it; it is written by hand, nothing generates it. Codebase
  internals never go there; they belong in the root files and the folder
  READMEs.
- `CHANGELOG.md` — Keep a Changelog format; what gets an entry is in
  `CONTRIBUTING.md`.
- `.agents/skills/` — Agent Skills for filing issues and writing pull
  requests; `.claude/skills/` symlinks them for Claude Code.
- `make help` — the list of targets.

## Layout

- `navigate/` — the package. `navigate` is the command-line entry point;
  `ARCHITECTURE.md` maps the inside.
- `tests/` — two pytest suites, `unit/` and `end_to_end/`, shared helpers in
  `tests/helpers/`, the small decks the end-to-end suite runs, and the
  result comparison that maintenance pull requests must pass.
- `assumptions/` — the model inputs, written in the DSL: `defaults/` holds
  the default nodes, one file per node, and `modules/` the default modules,
  `.inc` files shared across decks. Each has an `installation/` branch that
  ships with Navigate and a `user/` branch, searched first, for one's own
  definitions. By file count this is most of the repository. It is model
  content under CC-BY-4.0, not code.
- `simulations/` — `scenarios/` are the reference runs, about 25 minutes
  each; they are not tests. `examples/` are small decks that CI smoke-runs.
- `docs/` — the Sphinx/MyST source of the user manual. It publishes to
  `gh-pages`; `dev` publishes to `/staging/`. `docs/tutorials/` holds each
  tutorial's starting files next to its page; the docs build zips them into
  the page's download, and the example solution is written into the page.
  Nothing runs the tutorials.
- `syntax/` — editor syntax highlighting for the DSL, including a committed
  VS Code `.vsix`.

A run writes its output next to its deck: `plots*/`, `*.xlsx` and `*.log`.
All of it is gitignored. Two runs of one deck at the same time overwrite
each other's files, and the test suites run decks too.

## Environment and commands

- Python 3.13 only. Dependencies are plain pip and setuptools; there is no
  lock file. `make pip-setup` creates `.venv` and installs the package
  editable with the dev extras; `make conda-setup` does the same in a conda
  environment named `nav`.
- `make` runs its tools from the checkout's own `.venv` when one exists. A
  second checkout, a git worktree included, needs its own `make pip-setup`,
  or it imports the primary checkout's source.
- HiGHS is bundled and is the default solver. Gurobi is an optional extra
  that needs a commercial licence.
- Run a deck with `navigate <deck>.nav -d ./assumptions -s`; `-s` skips the
  plots. `ASSUMPTIONS_DATA_DIR` replaces `-d`.
- `make lint` runs `ruff check` and `ruff format --check` over `navigate/`
  and `tests/`, `mypy` over `navigate/` only, and `reuse lint`.
- The test targets are `test-unit`, `test-e2e`, `test-examples` and
  `test-all`; `compare-results` compares the results of a fixed set of decks
  between this checkout and another ref. What each suite answers and its
  conventions are in `tests/AGENTS.md`.
- `make docs` builds the user manual.
- CI runs on every pull request: Lint, Build package, and Run tests with the
  unit and end-to-end suites and the examples. A pull request labelled
  `maintenance` also runs Compare results against its base.

## Rules for every change

- No pull request targets `main`; it is the release branch. The base is
  `dev`, or the integration branch of the larger effort the work belongs
  to.
- Every new file carries a licence header: Apache-2.0 for code, tests and
  tooling; CC-BY-4.0 for decks, assumptions, documentation and figures. A
  file that cannot carry a header gets an annotation in `REUSE.toml`.
  `reuse lint` catches a missing header, not a wrong licence.
- No lint or type suppressions in code: no `noqa`, no `type: ignore`. The
  configuration catches only the blanket forms, through `PGH`; a targeted
  suppression passes `make lint` and is still not written. Fix the code, or
  change the rule for everyone in the configuration.
- `CHANGELOG.md` takes user-facing changes and bugs only; what gets an
  entry, and its form, is under Changelog in `CONTRIBUTING.md`.
- A change to an assumption value carries references or a justification.
- Issues and pull requests follow the `filing-issues` and
  `writing-pull-requests` skills; a problem found during a task and outside
  its scope is filed as an issue, not fixed in the task's branch.

## What a change touches

- A DSL attribute or command lives in four places: the setter on the node
  class, whose docstring is one line for developers; the parser table in
  `navigate/parser/_attributes.py` or `_commands.py`, which also lists the
  attribute as required when every deck must assign it; its entry on the
  node's page in `docs/reference_manual/`, the only place it is explained
  to users, with its units, limits, default and examples; and the attribute
  coverage test. `tests/unit/docs/test_setters_registered.py` checks the
  registries against the setters and `test_node_pages.py` the manual pages
  against the registries, both in both directions; the report-property
  appendix of `docs/reference_manual/report.md` is checked against the
  profile getters the same way by `test_report_property_docs.py`. The
  coverage deck is checked against the registries by
  `tests/end_to_end/test_attribute_coverage.py`.
- A change that moves simulation results explains the difference in the
  pull request and keeps `tests/end_to_end` green. A change meant to leave
  them alone is labelled `maintenance`, and its Compare results check must
  pass.
- Coding agents never write or edit tests unless the user explicitly asks
  for that test. Where a change makes a test critical or sensible by the
  criteria in `tests/AGENTS.md`, the agent proposes it instead: the decision
  it pins, the suite it belongs in, and how its expected value is derived
  independently of the implementation. A human decides.
- A user-visible change in behaviour updates the reference manual and the
  changelog.

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
  invariants and the naming conventions inside `navigate/`. Read it before
  changing code there.
- `CODESTYLE.md` — the conventions the tooling cannot check.
- `.ruff.toml` — this repository's lint rules and ruff settings. They are
  owned here and changed here.
- `CONTRIBUTING.md` — how a change gets in: an issue first for large
  features, what a pull request must carry, provenance for assumption
  changes.
- `tests/AGENTS.md` — which suite a check belongs in, the rules every test
  change follows, and what a test change touches. Read it before changing
  anything under `tests/`.
- `docs/` — the user manual, published as the documentation site.
  `docs/reference_manual/` describes the DSL and the model behaviour as
  users see it; it is written by hand, nothing generates it. Codebase
  internals never go there; they belong in the root files and the folder
  READMEs.
- `CHANGELOG.md` — Keep a Changelog format; user-facing changes only.
- `make help` — the list of targets.

## Layout

- `navigate/` — the package. `navigate` is the command-line entry point;
  `ARCHITECTURE.md` maps the inside.
- `tests/` — four pytest suites, shared helpers in `tests/helpers/`, and the
  small decks the suites run.
- `assumptions/` — the model inputs, written in the DSL: `defaults/` holds
  the default nodes, one file per node, and `modules/` the default modules,
  `.inc` files shared across decks. Each has an `installation/` branch that
  ships with Navigate and a `user/` branch, searched first, for one's own
  definitions. By file count this is most of the repository. It is model
  content under CC-BY-4.0, not code.
- `simulations/` — `scenarios/` are the reference runs, about 25 minutes
  each; they are not tests. `examples/` are small decks that CI smoke-runs.
- `tutorials/` — teaching decks with example solutions, also smoke-run in
  CI.
- `docs/` — the Sphinx/MyST source of the user manual. It publishes to
  `gh-pages`; `dev` publishes to `/staging/`.
- `syntax/` — editor syntax highlighting for the DSL, including a committed
  VS Code `.vsix`.

A run writes its output next to its deck: `plots*/`, `*.pkl`, `*.xlsx` and
`*.log`. All of it is gitignored. Two runs of one deck at the same time
overwrite each other's files, and the test suites run decks too.

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
- The test targets are `test-unit`, `test-attribute`, `test-guardrails`,
  `test-regression`, `test-tutorials`, `test-examples` and `test-all`. What
  each suite answers, how long it takes and its conventions are documented
  under `tests/`. `test-guardrails` is suspended and is not part of
  `test-all`; the status note in `tests/guardrails/README.md` has the
  detail.
- `make docs` builds the user manual.
- CI runs on every pull request: Lint, Build package, and Run tests with the
  unit, attribute, regression, tutorial and example suites.

## Rules for every change

- No pull request targets `main`; it is the release branch. The base is
  `dev`, or the integration branch of the larger effort the work belongs
  to. Pull requests are squash-merged, so the title becomes the commit
  subject: one imperative sentence stating the outcome, no prefix.
- Every new file carries a licence header: Apache-2.0 for code, tests and
  tooling; CC-BY-4.0 for decks, assumptions, documentation and figures. A
  file that cannot carry a header gets an annotation in `REUSE.toml`.
  `reuse lint` catches a missing header, not a wrong licence.
- The ratchet regions in `.ruff.toml` and `mypy.ini` list files that predate
  the tooling, and `tools/ratchet.py` generates and prunes them. Entries are
  only ever removed. When lint fails in a listed file, clean the whole file
  in a style-only commit and delete its entry; a new file never gets one.
  Never answer a ratchet entry by loosening the rule it waives: the entry
  exists to be deleted once the file is clean, not to be made unnecessary by
  weakening the rule for every other file.
- No lint or type suppressions in code: no `noqa`, no `type: ignore`. The
  configuration catches only the blanket forms, through `PGH`; a targeted
  suppression passes `make lint` and is still not written. Fix the code, or
  change the rule for everyone in the configuration.
- `CHANGELOG.md` records user-facing changes only: deck behaviour, results,
  the CLI, the output. Navigate is not a library, so a change to what
  Python code can import gets no entry of its own. A breaking one is still
  called out, in its own entry or in the entry for the change that caused
  it: `**Breaking** for code importing navigate as a library:`, then the
  symbols that moved and their new spelling, then what it does to results,
  which is usually nothing.
- A change to an assumption value carries references or a justification.

## Filing an issue

The issue forms in `.github/ISSUE_TEMPLATE/` apply a label and set the
body's sections, but `gh issue create` and the API bypass them. An issue
filed that way therefore carries the label of the matching form,
passed as `--label` with `gh issue create` or the `labels` field of an
API request: `bug`, `enhancement`, `documentation`, `maintenance`, or
`performance`. It uses that form's section headings.

## What a change touches

- A DSL attribute or command lives in four places: the setter on the node
  class, with a docstring; the parser table in
  `navigate/parser/_attributes.py` or `_commands.py`, which also lists the
  attribute as required when every deck must assign it; the node's page in
  `docs/reference_manual/`; and the attribute coverage test. The first two
  are checked against each other, and the manual page is checked against
  the registries in both directions by
  `tests/attribute/test_reference_manual_coverage.py`; the report-property
  appendix of `docs/reference_manual/report.md` is checked against the
  profile getters the same way by `test_report_property_docs.py`. Nothing
  checks the coverage deck against the registries.
- A change that moves simulation results explains the difference in the
  pull request and regenerates the regression baselines with
  `make regen-regression` in a commit of their own. Baselines are never
  edited by hand.
- A new non-trivial calculation gets a unit test whose expected value is
  derived independently of the implementation; `tests/unit/README.md` has
  the conventions.
- A user-visible change in behaviour updates the reference manual, the
  docstrings and the changelog.

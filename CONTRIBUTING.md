<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Contributing to Navigate

Thank you for your interest in improving Navigate. In principle anything can
be contributed: bug fixes, features, new policies, assumptions, documentation,
and tutorials. Contributions arrive as pull requests, from a fork or, for the
maintainers, from a branch of the repository itself.

## Getting started

1. Fork the repository and clone your fork.
2. Set up a development environment as the README says under "For
   development".
3. Create a branch from `dev` for your change.
4. Verify your setup with `make check`, which runs the linters and the unit
   suite.
5. Skim [ARCHITECTURE.md](ARCHITECTURE.md) for the package map and the
   data-flow invariants contributions must respect.

## What to contribute

Any valuable contribution is welcome.

**Bug fixes** can be submitted directly as a pull request. Describe the bug
and how the fix addresses it. If you have found a bug but do not plan to fix
it yourself, please open an issue instead.

**Changes to what the model represents**, such as a new policy, node type or
mechanism, should start as an issue. This lets us align on scope and design
before you invest significant effort. Smaller features can be submitted
directly as a pull request, and so can a rework of existing code that your
change needs; a rework beyond what it needs gets an issue of its own.

**Assumption changes** must include references or a justification for the new
values, so that the provenance of the model inputs stays traceable.

## Pull request expectations

- Target `dev`, or the integration branch of the larger effort the change
  belongs to; never `main`, the release branch, except for a patch release
  (Versions and releases).
- Keep each pull request one reviewable change: the rework the change needs
  belongs in it, unrelated fixes and refactors in pull requests of their own.
- Fill in the pull request template.
- Title the pull request with one imperative sentence stating the outcome:
  no prefix, no "(#N)", under about 65 characters.
- Follow the code style: `ruff` and `mypy` enforce the mechanical rules
  (`make lint`), [`CODESTYLE.md`](CODESTYLE.md) carries the conventions the
  tooling cannot check.
- Update documentation when behavior changes: the reference manual
  (`docs/reference_manual/`) for user-facing changes and docstrings for code changes.

### Changelog

`CHANGELOG.md` records what a deck author or a reader of the output would
notice: a DSL attribute, command, keyword or result added, renamed, removed or
changed in meaning; a change in simulation results beyond rounding (see
Testing); a deck that used to run and now fails, or the reverse; the CLI and
installation requirements; and the results file, console and log output, error
messages a deck author sees included. It also records bugs in any of these,
including errors in the reference manual. The format is Keep a Changelog, in
the version the head of `CHANGELOG.md` cites.

Nothing else gets an entry: no refactor, move, rename or removal inside
`navigate/`, and no change to what Python code can import. Typing, test,
lint, CI, `make` and tooling changes get none either, and neither does a
results-neutral change with no DSL or output effect. A pull request states
its user-visible effect in its description.

An entry is one to three lines; related entries may share one bullet with a
sub-list, each item one to three lines. It states what the user sees and, for
a rename or removal, what to write instead, and it ends with the issue number
if there is one. It goes under one of Keep a Changelog's headings and carries
no "Breaking" label or heading, because Navigate keeps no backward
compatibility: no shims and no deprecation periods; a breaking change is made
outright, and any minor release may break old decks (Versions and releases).
How the change works belongs in the pull request, not the changelog.

## Testing

All tests must pass before a pull request can be merged. Run the full suite
with `make test-all`, or the individual suites during development.

The suite is kept small on purpose, so new code does not by default get a
test: `tests/AGENTS.md` says when a change earns one and which suite it
belongs in, and that coding agents propose tests rather than write them.

Changes that alter simulation results should explain the difference in the
pull request description. A pull request labelled `maintenance` promises to
leave them alone; CI then runs a fixed set of decks on the pull request merged
into its base and on that base, and fails on any difference beyond rounding,
the tolerance the `writing-pull-requests` skill names. Run the same
comparison locally against the newest `dev` with `make compare-results`.

## Horizon and Lantern

The companion tools [Horizon](https://github.com/zerocarbonshipping/horizon-zcs)
and [Lantern](https://github.com/zerocarbonshipping/lantern-zcs) keep no guide
of their own: this guide and [`CODESTYLE.md`](CODESTYLE.md) are theirs, read
for their repository.

- Their README names the checks a pull request passes, in place of
  `make check` and the test suites; their package docstring or README maps
  their code, in place of `ARCHITECTURE.md`.
- Their README states what their suite tests, in place of the Scope of
  `tests/AGENTS.md`, whose rules on proposing a test and on a failing test
  hold for them.
- Their `CHANGELOG.md` records what a user of the tool would notice: a
  command-line argument, a key of the files it reads, what it writes or
  prints, and its installation requirements. The rest of Changelog holds as
  written.
- Of `CODESTYLE.md`, the sections Nodes and the DSL, Dynamic state and
  results, and Validation and dynamic access are Navigate's alone, as is any
  rule naming a Navigate module (`RunLog`, `RELATIVE_TOLERANCE`).
- Their `pyproject.toml` configures ruff with Navigate's rule set at a line
  length of 128, and mypy as Navigate's `mypy.ini` does.
- They have no issue forms, no pull request template, no `AGENTS.md` and no
  results comparison. Their labels are Navigate's: an issue or pull request
  takes the label of the Navigate form it fits.

## Versions and releases

Navigate, Horizon and Lantern release on their own. They share three
contracts, each versioned by the tool that writes it:

| Contract | Written by | Read by | Version |
| --- | --- | --- | --- |
| Results file | Navigate | Horizon, Lantern | `schema_version`, see [Results file](docs/reference_manual/results_file.md#schema-version) |
| Study file | Horizon | Lantern | `study_schema_version` |
| Command line: `--set`, `--name`, `--output-dir`, `--version`, the `parquets` subfolder and the exit codes | Navigate | Horizon | the oldest Navigate Horizon runs |

A version is `MAJOR.MINOR.PATCH`:

- A patch release fixes. It changes no contract, and every deck the release
  before it ran still runs.
- A minor release adds: a result, a key, an option, or a reader for a new
  contract version. Any minor release of Navigate may break old decks.
- A major release is a tool's own redesign.

A change that breaks a contract raises its version and reaches users readers
first. The readers release a version that reads both the old and the new
number, then the writer releases one that writes the new number, and the
readers drop the old number in a later minor release. The writer's pull request
links an issue and a pull request in each reader's repository.

Each tool checks a contract version before it relies on it: Horizon runs
`navigate --version` before it starts a run, and a reader checks the version of
each file it opens. A mismatch stops with a message naming the version found,
the versions supported and the tool to upgrade.

A release is a tagged GitHub release, which publishes the package to PyPI. The
owners make it:

1. Set the version in `pyproject.toml` and `CITATION.cff`, for Navigate also in
   `docs/_static/switcher.json`, and date the `CHANGELOG.md` section. Its first
   line names the contract versions: "Writes results schema 1." for Navigate,
   "Runs Navigate 1.1 or later; reads results schema 1; writes study schema 1."
   for Horizon, "Reads results schema 1 and study schema 1." for Lantern.
2. Merge into `main`: `dev` for a minor or major release, or for a patch, a
   branch from `main` that holds only the fix.
3. Tag the merge `vX.Y.Z` and publish a GitHub release from the tag, with the
   changelog section as its notes.
4. Merge `main` back into `dev`.

## Questions

Issues are the preferred way to ask. Whether you are unsure if a change needs
an issue first, want to discuss a design, or have a question about the
model, open an issue and we will get back to you.

## AI tools

The maintainers develop Navigate with coding agents, which work from the same
documents as everyone else: `AGENTS.md` at the root, the `AGENTS.md` files in
`tests/`, `docs/` and `assumptions/`, and the Agent Skills for issues, pull
requests and code in `.agents/skills/`. Whether you use such tools is your
choice; either way you answer for what you submit, so please do not add code or
inputs you do not fully understand.

Do not add a `CLAUDE.md` or `CLAUDE.local.md`: where either exists, Claude Code
stops reading the `AGENTS.md` files.

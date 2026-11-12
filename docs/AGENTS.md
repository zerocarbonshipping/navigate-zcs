<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Working on the user manual

`docs/` is the source of the user manual, built with Sphinx and MyST and
published as the documentation site. Its readers are deck authors and readers
of the results file. This file is excluded from the build (`exclude_patterns`
in `docs/conf.py`).

## What belongs in it

- `reference_manual/` describes the DSL and the model's behaviour as users
  see them: each node's attributes and commands with their units, limits,
  defaults and examples, the results file, the IDs. It is written by hand;
  nothing generates it.
- What the model computes is described by what it means to a user, not by how
  it is derived; the manual carries no modelling derivations.
- Codebase internals never go here; they belong in the root documents and the
  nested `AGENTS.md` files.
- A change a deck author or a reader of the output would notice updates the
  manual in the same pull request; whether it also gets a changelog entry is
  under Changelog in `CONTRIBUTING.md`.

## What holds it to the code

- `tests/unit/docs/test_node_pages.py`: one page per node and general-node
  type, whose `## Attributes` and `## Commands` headings match the
  `deck_attribute` and `deck_command` marks on its class, both ways; any
  other page in `reference_manual/` is one of the extras the test lists, so a
  new page of another kind needs the owners to extend that list.
- `tests/unit/docs/test_results_page.py`: `reference_manual/results_file.md`
  matches the result fields and their units.

Nothing else is checked: prose, examples and links are held by review.

## Tutorials and notebooks

- `tutorials/` holds each tutorial's page and, next to it, a folder of
  starting files; the build zips the folder's `.nav` and `.inc` files into the
  page's download. The example solution is written into the page.
- `notebooks/` holds each workshop notebook in a folder of its own, next to
  the case it runs. The notebook keeps the outputs of one run, which its page
  shows; `docs/check_notebooks.py` checks that they come from one clean run
  and prints how to refresh them.
- Nothing reruns the tutorials or refreshes the notebooks' outputs when the
  code or the assumptions change.

## Building and publishing

- `make docs` builds the site into `docs/_build/html`. It needs the packages
  in `docs/requirements.txt`, which the dev extras do not include: in a
  worktree, `.venv/bin/pip install -r docs/requirements.txt` first.
- The build also packages the VS Code extension from `syntax/vscode/` for the
  getting-started page.
- The Documentation workflow runs `docs/check_notebooks.py` and the build on
  every pull request; Sphinx warnings do not fail it. A push to `main` or a
  release tag publishes the site, a push to `dev` publishes it under
  `/staging/`.

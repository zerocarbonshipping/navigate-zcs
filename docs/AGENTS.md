<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Working on the user manual

`docs/` is the source of the user manual. Its readers are deck authors and
readers of the results file. This file is excluded from the build
(`exclude_patterns` in `docs/conf.py`).

## What belongs in it

- `reference_manual/` describes the DSL and the model's behaviour as users see
  them: each node's attributes and commands with their units, limits, defaults
  and examples, the results file, the IDs. Nothing generates it.
- What the model computes is described by what it means to a user, not by how
  it is derived; the manual carries no modelling derivations.
- Codebase internals never go here; they belong in the root documents and the
  nested `AGENTS.md` files.
- A change a deck author or a reader of the output would notice updates the
  manual in the same pull request; the changelog rule is in `CONTRIBUTING.md`.

## What holds it to the code

`tests/unit/docs/test_node_pages.py` holds the page of each node and
general-node type to the marks on its class, and `test_results_page.py` holds
`results_file.md` to the result fields and their units, both ways. Any other
page in `reference_manual/` must be on the first test's list of extras, which
only the owners extend. Nothing else is checked: prose, examples and links are
held by review.

Nothing reruns the tutorials or refreshes the notebooks' outputs when the code
or the assumptions change; `docs/check_notebooks.py` checks that a notebook's
outputs come from one clean run.

## Building

`make docs` needs `docs/requirements.txt`, which the dev extras do not include:
in a worktree, `.venv/bin/pip install -r docs/requirements.txt` first.

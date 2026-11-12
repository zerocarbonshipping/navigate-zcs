<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Working on the assumptions

`assumptions/` is the default library: the model's inputs, written in the DSL.
It is model content under CC-BY-4.0, not code.

- `defaults/<NodeType>/<name>.inc` holds the default node
  `<NodeType>("<name>")`, one node per file: the parser looks for a node a
  deck references but does not declare at exactly that path, so the file
  name is the node's name. `modules/<module>.inc` holds a module a deck loads
  with `Load`, its name in snake_case (`DefaultFleet` is
  `default_fleet.inc`).
- Attributes and keywords are spelled as on the node's page in
  `docs/reference_manual/` (`Capex`, not `CAPEX`).
- A value changes only with its reference or a justification, which the
  pull request gives under Why; a new default node needs the same for each of
  its values.
- Every deck that reads a changed file moves with it, the examples, test
  decks, tutorials and notebook case among them: the pull request explains
  the movement under Results. Nothing reruns the tutorials or refreshes the
  notebook's outputs (`docs/AGENTS.md`).

<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# Plots

One figure per module, rendered at the end of a run from the manager's
profiles. This is the only package that imports `matplotlib`.

- A plot is a function `plot_<label>(manager, directory)`; the label is the
  function name without its prefix and is what a `Plot` node selects. The
  ordered catalogue is `PLOTS` in `_registry.py`: to add a plot, import it
  there and append it, then list the label in the appendix of
  `docs/reference_manual/plot.md`.
- Colours, labels, units and fonts come from the private helpers (`_colors`,
  `_labels`, `_units`, `_fonts`); `_units` is pure numeric and stays free of
  matplotlib.
- Import a plot function from its module, not from the package.

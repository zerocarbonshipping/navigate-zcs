<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# Filing a performance issue

- **Description** names the deck and the phase that is slow or memory-heavy.
  Prefer a small deck that shows the problem: the reference runs in
  `simulations/scenarios/` take about 25 minutes each.
- **Measurement** gives the setting and the numbers:
  - the deck, the solver, the commit and the machine;
  - wall time with the number of runs, a profile excerpt trimmed to the top
    entries, or peak memory;
  - or, in place of a measurement, an asymptotic argument: how the cost
    grows with vessels, ports, fuels or years.
- **Proposed resolution** names the remedy and the benchmark to rerun to
  confirm it: the same deck, solver and machine.
- A fix leaves results unchanged. A remedy that would move them says so and
  why.

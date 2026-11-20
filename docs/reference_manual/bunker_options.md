<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# BunkerOptions

The `BunkerOptions` general node provides configurations for the bunkering model.
It helps define various tolerances and iteration limits that guide how the model operates.

Example:

```python
BunkerOptions {
    Solver = HIGHS
    SolutionTolerance = 1e-6
    FairShareMaximumIterations = 10
    FairShareTolerance = 1e-2
}
```

## Equally cheap solutions

A bunkering problem often has several solutions of the same cost, such as a fuel that costs the same in two ports of a route. Navigate chooses one of them, with its prices, by the names of the vessels, ports, fuels, converters and regulations involved, and not by the solver backend, its version, its method or the order the problem is built in: the choice is arbitrary but fixed, and renaming a node can change the results.

The choice has limits. Whether two solutions are equally cheap is judged within the [SolutionTolerance](#solutiontolerance), and where their costs differ by about that tolerance, which of them a run returns can depend on the solver. Where the solver cannot carry the choice through, it returns one of the equally cheap solutions by its own rules. The results of a deck can therefore still differ between solver backends, versions and methods.

## Attributes

### Solver

This attribute selects the solver backend for the bunker algorithm. AUTOMATIC uses Gurobi when a license is available and HiGHS otherwise. GUROBI also falls back to HiGHS, with a warning, when no Gurobi license is available. HIGHS uses HiGHS without trying Gurobi. It can also be set from the command line with `--solver`, which accepts lowercase values (`auto`, `gurobi`, `highs`) and takes precedence over the deck setting.

* **Data type**: `ID`
* **Legal values**: [SolverBackendID](appendix_ids.md#solverbackendid)
* **Default**: AUTOMATIC

### SolverMethod

This attribute selects the LP solution method. It is passed to Gurobi as its `Method` parameter; the HiGHS backend ignores it. It changes how fast a bunkering problem is solved and, apart from the limits described under [Equally cheap solutions](#equally-cheap-solutions), not which solution is returned.

* **Data type**: `ID`
* **Legal values**: [SolverMethodID](appendix_ids.md#solvermethodid)
* **Default**: DETERMINISTIC

### SolutionTolerance

This attribute sets the tolerance of the solution for the bunker algorithm. The SolutionTolerance defines the lower tolerance for what to consider in results, i.e., if a fuel is bunkered in an amount smaller than the SolutionTolerance, it is rounded to 0 and thus not brought into reports and plots. The same value is passed to the LP solver as its feasibility and optimality tolerance, so it also affects how the solver converges.

* **Data type**: `Float`
* **Example value**: `1e-6`
* **Minimum value**: >0
* **Default**: 1e-6

### Threads

This attribute sets the number of threads used by the LP solver to solve the bunker algorithm.

Notice that '0' lets the solver choose the number of threads automatically.

* **Data type**: `Integer`
* **Example value**: `2`
* **Minimum value**: 0
* **Default**: 0

### FairShareMaximumIterations

This attribute sets the maximum iterations of the fair-share sequential LP of the bunker algorithm.

* **Data type**: `Integer`
* **Example value**: `10`
* **Minimum value**: 1
* **Default**: 50

### FairShareTolerance

This attribute sets the fair-share tolerance of the bunker algorithm. The fair share tolerance is the tolerance related to how ‘fair’ the solution must be to be considered ‘fair’. It must be greater than zero; a very small tolerance can make the fair-share iteration numerically unstable.

* **Data type**: `Float`
* **Example value**: `1e-2`
* **Minimum value**: >0
* **Default**: 1e-1

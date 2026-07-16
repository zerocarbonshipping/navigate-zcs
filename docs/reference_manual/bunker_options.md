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

## Attributes

### Solver

This attribute selects the solver backend for the bunker algorithm. It can also be set from the command line with `--solver`, which accepts lowercase values (`auto`, `gurobi`, `highs`) and takes precedence over the deck setting.

* **Data type**: `ID`
* **Legal values**: [SolverBackendID](appendix_ids.md#solverbackendid)
* **Default**: AUTOMATIC

### SolverMethod

This attribute selects the LP solution method used by the solver backend.

* **Data type**: `ID`
* **Legal values**: [SolverMethodID](appendix_ids.md#solvermethodid)
* **Default**: DETERMINISTIC

### SolutionTolerance

This attribute sets the tolerance of the solution for the bunker algorithm. The SolutionTolerance defines the lower tolerance for what to consider in results, i.e., if a fuel is bunkered in an amount smaller than the SolutionTolerance, it is rounded to 0 and thus not brought into reports and plots.

* **Data type**: `Float`
* **Example value**: `1e-6`
* **Minimum value**: 0
* **Default**: 1e-6

### Threads

This attribute sets the number of threads used by the LP solver to solve the bunker algorithm.

Notice that '0' corresponds to the solver's default setting.

* **Data type**: `Float`
* **Example value**: `2`
* **Minimum value**: 0
* **Default**: 2

### FairShareMaximumIterations

This attribute sets the maximum iterations of the fair-share sequential LP of the bunker algorithm.

* **Data type**: `Integer`
* Example value: `10`
* **Minimum value**: 1
* **Default**: 10

### FairShareTolerance

This attribute sets the fair-share tolerance of the bunker algorithm. The fair share tolerance is the tolerance related to how ‘fair’ the solution must be to be considered ‘fair’. Setting this to zero is not recommended due to potential numerical instability issues.

* **Data type**: `Float`
* **Example value**: `1e-2`
* **Minimum value**: 0
* **Default**: 1e-2

### FlexibilityMaximumIterations

This attribute sets the maximum iterations for the bisection search algorithm that calculates the flexibility compliance unit value of flexible regulations.

* **Data type**: `Integer`
* Example value: `10`
* **Minimum value**: 1
* **Default**: 10

### FlexibilityToleranceX

This attribute sets the tolerance for the convergence of the bisection search algorithm that calculates the flexibility compliance unit value of a flexible regulation. The tolerance determines when the change in the estimate is sufficiently small to be considered converged. Setting this to zero is not recommended due to potential numerical instability issues.

* **Data type**: `Float`
* **Example value**: `0.1`
* **Minimum value**: 0
* **Default**: 1

### FlexibilityToleranceY

This attribute sets the tolerance for the comparison of objective function values in the bisection search algorithm that calculates the flexibility compliance unit value of a flexible regulation. The tolerance determines when the change in the estimate is sufficiently small to be considered converged. Setting this to zero is not recommended due to potential numerical instability issues.

* **Data type**: `Float`
* **Example value**: `0.1`
* **Minimum value**: 0
* **Default**: 1

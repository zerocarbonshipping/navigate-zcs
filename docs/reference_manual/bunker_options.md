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

A bunkering problem often has several solutions of the same cost, such as a fuel that costs the same in two ports of a route. Navigate chooses among them by three rules, each before the next:

1. Where the threshold of a `FLEXIBLE` `Regulation` binds and several vessel types could each cut the same emissions at the same cost, each of them takes the same share of its own room: the range between the least and the most the regulation can count for one vessel of the type at that cost. Two identical vessel types so get the same counted emissions per vessel, whatever their numbers, and a type with twice the room cuts twice as much. Where a remedial unit costs exactly what a cut costs, the vessels cut before remedial units are bought.
2. The emissions a `Regulation` counts for a vessel are as low as its fuels allow: where the regulation leaves the vessel the choice, it burns a fuel with low emissions inside the `Jurisdiction` rather than outside it.
3. The largest amount of a fuel a vessel bunkers at one stop of its route is as small as it can be. Where the fuel costs the same at several stops and nothing else limits them, the vessel so bunkers the same amount at each. Two calls at one port are two stops.

Where the second or the third rule cannot hold for every vessel, fuel and regulation at once, it holds for their total, with each vessel type counted as one vessel whatever its number. Between two fuels that cost a vessel exactly the same, the second rule takes the one with the lower counted emissions; the third rule adds up the amounts by mass, so where the emissions are the same too, the vessel takes the fuel it needs less mass of, and where it needs the same mass of both, no rule chooses between them.

The rules settle the choice by the bunkering problem alone: not by the solver backend, its version or its method, nor by the order of the nodes in the deck. They leave six choices open, and there a run returns whichever of the equally cheap solutions the solver ends at:

- A fuel costs the same at several stops of a route of three or more stops, and another stop takes the largest amount of it, such as a cheaper one with a limited supply: how the rest is split among the stops below that amount.
- A vessel burns two fuels in the same converters, and its regulations count the same whichever of them it burns where: which of the two it burns on which leg, in which port and in which converter. The amounts it bunkers and burns of each fuel are the same either way, and so are its reported emissions where the two fuels have the same heating value and emission factors, such as `methane_bio` and `methane_electro`.
- Two fuels cost a vessel the same at the same stops, its regulations count the same for either, and they have the same heating value, so the vessel needs the same mass of either: how much of each it bunkers and burns. Bunkering 100 t at two stops of one price, the vessel can take 50 t of one fuel at each stop or 25 t of each fuel at each, and the largest amounts at one stop add up to 50 t either way.
- The thresholds of two or more `FLEXIBLE` regulations bind at once: how a cut is split among vessel types that could each make it at the same cost, as far as the second rule leaves that open. The first rule is not applied.
- The shares of the first rule cannot all be met, because another limit stands in the way, such as the threshold of a second `FLEXIBLE` regulation that does not bind: the first rule is not applied there either.
- Two limits bind only together and, relaxed in proportion to their sizes, would allow the same amount: which of the two carries the price.

The choice has further limits. Whether two solutions are equally cheap is judged within the [SolutionTolerance](#solutiontolerance), and where their costs differ by about that tolerance, which of them a run returns can depend on the solver. Where the solver cannot carry a rule through, it returns whichever of the equally cheap solutions it ends at. The results of a deck can therefore still differ between solver backends, versions and methods.

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

This attribute sets the tolerance of the solution for the bunker algorithm. The SolutionTolerance defines the lower tolerance for what to consider in results, i.e., if a fuel is bunkered in an amount smaller than the SolutionTolerance, it is rounded to 0 and thus not brought into reports and plots. Remedial units smaller than the SolutionTolerance likewise count as none, and the `Regulation` as complied with. The same value is passed to the LP solver as its feasibility and optimality tolerance, so it also affects how the solver converges.

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

This attribute sets the fair-share tolerance of the bunker algorithm. The fair-share iterations end when the amount of each fuel a vessel bunkers at each port, in t/year and with its calls at the port taken together, changes little enough from one iteration to the next: when the square root of the sum of the squared changes over all vessels, ports and fuels is below the tolerance. It must be greater than zero; a very small tolerance can make the fair-share iteration numerically unstable.

* **Data type**: `Float`
* **Example value**: `1e-2`
* **Minimum value**: >0
* **Default**: 1e-1

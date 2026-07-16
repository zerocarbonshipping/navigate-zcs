---
sd_hide_title: true
---

<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Navigate

```{toctree}
:hidden:

tutorials/index
reference_manual/index
```

## Navigate

**Navigate** is a sectoral integrated assessment model for the maritime
industry's transition toward zero-carbon shipping. It projects how a fleet
renews itself, which fuels and technologies it adopts, where those fuels are
produced and bunkered, and how regulation reshapes those choices — year by year,
over multi-decade horizons.

Unlike a central-planner optimiser, Navigate represents long-term investment as a
discrete-choice problem: shipowners weigh costs, regulation, and availability and
pick among newbuild, retrofit, and fuel options through a multinomial logit
model. Only short-term operational decisions, such as how a voyage is actually
bunkered, are solved as a linear program. The result is a behavioural picture of
the transition rather than a least-cost ideal.

A simulation is described in a small domain-specific language: human-readable
`.nav` and `.inc` files that declare nodes — vessels, fleets, routes, ports,
fuels, plants, regulations — and a timeline of events that change them. Running a
deck produces Excel reports and plots that trace fleet composition, fuel demand,
emissions, and compliance costs through time.

## About this documentation

This site is organised into two parts. New users should start with the
tutorials and work through them in order; the reference manual is there to look
up specifics as you build your own decks.

::::{grid} 1 1 2 2
:gutter: 3

:::{grid-item-card} Tutorials
:link: tutorials/index
:link-type: doc

A guided path from installing Navigate and running your first single-vessel
simulation through to modular, multi-scenario studies.
:::

:::{grid-item-card} Reference Manual
:link: reference_manual/index
:link-type: doc

The `.nav`/`.inc` DSL syntax and a complete description of every node type and
its attributes, grouped by theme.
:::

::::

Installation instructions and the full list of command-line options live in the
project [README](https://github.com/zerocarbonshipping/navigate-zcs).

## Citing this Project

If you use Navigate in your work, please cite us:

> Lehn, F. W., Thomas, J. & Hintze, M. *Navigate* v1.0.0 (Fonden Mærsk
> Mc-Kinney Møller Center for Zero Carbon Shipping, 2026);
> https://github.com/zerocarbonshipping/navigate-zcs

::::{tab-set}

:::{tab-item} BibTeX
```bibtex
@software{Navigate-2026,
    author = {Lehn, Frederik Winkel and Thomas, Julius and Hintze, Mathias},
    organization = {Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping},
    license = {Apache-2.0},
    month = jul,
    title = {{Navigate}},
    url = {https://github.com/zerocarbonshipping/navigate-zcs},
    version = {1.0.0},
    year = {2026}
}
```
:::

:::{tab-item} RIS
```text
TY  - COMP
AU  - Lehn, Frederik Winkel
AU  - Thomas, Julius
AU  - Hintze, Mathias
TI  - Navigate
PB  - Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
PY  - 2026
ET  - 1.0.0
UR  - https://github.com/zerocarbonshipping/navigate-zcs
ER  -
```
:::

:::{tab-item} APA
```text
Lehn, F. W., Thomas, J., & Hintze, M. (2026). Navigate (Version 1.0.0) [Computer software]. Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping. https://github.com/zerocarbonshipping/navigate-zcs
```
:::

:::{tab-item} MLA
```text
Lehn, Frederik Winkel, et al. Navigate. Version 1.0.0, Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping, 2026, github.com/zerocarbonshipping/navigate-zcs.
```
:::


::::

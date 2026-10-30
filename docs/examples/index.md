<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Examples

Cases built with Navigate, grouped by family: the family follows the shape of
the deck, and cases of the same family are built the same way. Pick a family to
see its cases. Each case has its deck, the prompt that builds it with an AI
assistant, and a notebook to run it in Colab. To build a case of your own, start
from the closest one and follow [Session 5](../workshop/05-build-your-own-case.ipynb).

The numbers in these cases illustrate the model and are not calibrated studies:
some are invented, and each page says which.

::::{grid} 1 1 3 3
:gutter: 3

:::{grid-item-card} Specific trades
:link: specific-trades
:link-type: doc
:img-top: ../_static/example_4_map.svg
:img-alt: Map of a trade route from Chile to Rotterdam
:class-card: example-card

One route, its named ports called in a fixed order.
+++
2 cases · 6 more prompts
:::

:::{grid-item-card} Regional networks
:link: regional-networks
:link-type: doc
:img-top: ../_static/examples/south_pacific_map.svg
:img-alt: Map of a bulk trade between five South Pacific ports
:class-card: example-card

Several routes, or trips between a region's ports in no fixed order.
+++
4 cases
:::

:::{grid-item-card} Global cases
:link: global-cases
:link-type: doc
:img-top: ../_static/reference_scenario_map.svg
:img-alt: Map of the reference scenario's five fuel-supply regions
:class-card: example-card

The world fleet, or a policy applied worldwide.
+++
1 case · 2 more prompts
:::

::::

```{toctree}
:hidden:

specific-trades
regional-networks
global-cases
```

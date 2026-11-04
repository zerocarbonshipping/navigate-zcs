<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0

The source of docs/examples/rhine.ipynb, which is both the Examples page and the
Colab notebook. Edit this file, then run
    python docs/_figures/make_example_notebooks.py rhine
Each {{ name }} line becomes cells: see make_example_notebooks.py.
-->

{{ badge }}

# Inland waterways in Germany

[Specific trades](specific-trades.md) · deck `simulations/examples/example_6/`

What e-fuel price and CO2 price lead fleet owners and operators to switch fuel?

## The case

{{ map }}

- **Ships:** 300 large Rhine motor cargo vessels, all on fuel oil in 2026. The
  library has no inland vessel, so the ship is a library general cargo ship
  resized for the Rhine (INVENTED). The owners can burn a drop-in fuel (FAME,
  e-diesel) in the ships they have, or order LNG or methanol ships.
- **Route:** one route up the Rhine, Duisburg, Cologne, Koblenz, Mainz and
  Mannheim, a quarter of the cargo discharged at each call, then back to
  Duisburg in ballast.
- **Fuels:** fuel oil at every port; LNG, FAME, e-diesel and e-methanol at
  Duisburg and Mannheim only. Every fuel is bought at the port at a set price,
  plus a handling cost (INVENTED). The prices and upstream emissions of FAME and
  the e-fuels are placeholders for your source: by default what the library's
  own plants would cost, FAME 45 USD/GJ and e-diesel 103 USD/GJ in 2026 to 71 by
  2050, against about 12 for fuel oil.
- **Policy:** Germany's national CO2 price, 65 USD/t in 2026 to 150 in 2050
  (INVENTED), as a copy of the library's EU ETS on the five ports; the
  CO2_PRICE lever below changes it, and 0 removes it. EU ETS and FuelEU do not
  cover inland waterways.
- **Horizon:** 2026 to 2050, yearly.

## Results

{{ setup }}

{{ run }}

{{ levers }}

## The deck

{{ deck }}

## Build it with an AI assistant

This deck was built from the prompt below by an assistant that saw only the
prompt. A trade under a national policy starts from it.
[Session 5](../workshop/05-build-your-own-case.ipynb) shows how to use it.

{{ prompt rhine: Full prompt for this case }}

### Variant

{{ prompt norway: Coastal shipping in Norway: two ship classes under a national CO2 tax }}

## Run it yourself

In Colab: the badge at the top of this page opens it as a notebook, which runs
the deck and lets you move the levers. Nothing to install.

On your machine, install Navigate first: follow the [installation steps in the README](https://github.com/zerocarbonshipping/navigate-zcs/blob/dev-workshop/README.md#installation),
or the more detailed [Getting started](../tutorials/getting_started.md) tutorial.
Then run the deck from the repository root:

```bash
python -m navigate simulations/examples/example_6/example_6.nav -d ./assumptions
```

To make a case of your own, copy the folder to `simulations/user/` and change
it, or have an AI assistant build one from the prompt above, as
[Session 5](../workshop/05-build-your-own-case.ipynb) shows.

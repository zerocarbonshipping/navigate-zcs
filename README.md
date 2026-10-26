<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Navigate

Navigate is a sectoral integrated assessment model for simulating the maritime industry's transition toward zero-carbon shipping. It models fleet investment decisions, fuel production, bunkering operations, and regulatory impacts over multi-decade timelines.

## Installation
It is recommended that Navigate is installed within an environment such as [conda](https://continuumio-docs.readthedocs-hosted.com/miniconda/) or [venv](https://docs.python.org/3/library/venv.html).

### Navigate + Assumptions & Simulations (Preferred)
- Clone the repository and run `pip install .` in the directory.
- Set the environment variable `ASSUMPTIONS_DATA_DIR` to point to the `assumptions` folder.

### Navigate PyPI Package
- `pip install navigate` Installs only Navigate.


#### Optional: Gurobi solver (commercial license)
Navigate ships with the open-source [HiGHS](https://highs.dev/) solver and uses it by default — no further setup is needed. If you have a [Gurobi](https://www.gurobi.com/) license, you can install the faster Gurobi backend as an optional extra `pip install .[gurobi]`.


## Usage
TODO

## Tutorials and Example Simulations

Detailed installation guide, step-by-step tutorials and a full reference manual are available in the [documentation](https://zerocarbonshipping.github.io/navigate-zcs/). Each tutorial page offers its starting files as a download.
Some simple example simulations can be found under `simulations/examples`



## Disclaimer

Navigate is an open-source analytical model intended for research and scenario analysis of maritime decarbonisation pathways. The model, its assumptions and any outputs are provided for illustrative and analytical purposes only.

Model outputs depend on the assumptions selected by the user and should not be interpreted as forecasts, benchmarks, recommendations or commercially optimal outcomes, nor as legal, financial or investment advice.

Users are responsible for selecting and adapting assumptions appropriate to their own circumstances and for exercising their own independent judgement when interpreting or relying on any model outputs.


## License

Copyright 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping.

Navigate is licensed under two licenses, depending on the type of content:

- The software — the `navigate` package, tests, and all build, tooling, and editor-support files — is licensed under the [Apache License 2.0](LICENSES/Apache-2.0.txt) (see also the root [LICENSE](LICENSE) file).
- The model content — assumptions, simulation and input files written in the Navigate DSL, tutorials, documentation, and figures — is licensed under [Creative Commons Attribution 4.0 International](LICENSES/CC-BY-4.0.txt) (CC-BY-4.0).

Every file declares its license through an `SPDX-License-Identifier` header or through the metadata in [REUSE.toml](REUSE.toml), following the [REUSE specification](https://reuse.software/). The full license texts are in the [LICENSES](LICENSES/) directory.

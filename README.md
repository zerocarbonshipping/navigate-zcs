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
- `pip install navigate-zcs` Installs only Navigate.


#### Optional: Gurobi solver (commercial license)
Navigate ships with the open-source [HiGHS](https://highs.dev/) solver and uses it by default — no further setup is needed. If you have a [Gurobi](https://www.gurobi.com/) license, you can install the faster Gurobi backend as an optional extra `pip install .[gurobi]`.


## Usage
The following options are available when running Navigate. See them in the command line by typing `navigate --help`.

| Flag                            | Description                                                                                                                                                                                                                                                       |
|---------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `-d DIR`, `--data-dir DIR`      | Folder location for assumptions that may be imported. Can also be set with the environment variable `ASSUMPTIONS_DATA_DIR`. <br/> The Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping supplies assumptions in the `assumptions` folder of this repository. |
| `--set NAME=VALUE`              | Replace each `%NAME%` in the deck and the files it reads with `VALUE`, as text, before they are read; repeat for each name. A `%NAME%` left without a value outside a comment is an error. A run with `--set` writes its log into the `logs` and its results file into the `parquets` subfolder of the output folder. See [Placeholders](docs/reference_manual/dsl_reference.md#placeholders). |
| `--name NAME`                   | Name of the run, the stem of its log, results, profile and infeasible-LP files. Default: the deck's file name without extension.                                                                                                                          |
| `--output-dir DIR`              | Folder the log, results, profile and infeasible-LP files are written to, created if missing. Default: the deck's folder.                                                                  |
| `-l LEVEL`, `--log-level LEVEL` | Set the log level for the `.log` file. With `DEBUG`, a failed run also prints the full traceback to the console.                                                                                                                                                  |
| `--solver {auto,gurobi,highs}`  | Solver backend. `auto` tries Gurobi then falls back to HiGHS. Without the flag, the deck's `BunkerOptions` `Solver` applies.                                                                                                                                      |
| `-p`, `--profile`               | Profile the run, write the statistics to the file `<name>.prof` in the output folder and print the 100 functions with the highest cumulative time. A profiled run prints no warning count.                                                   |

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

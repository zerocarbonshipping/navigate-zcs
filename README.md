<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Navigate

Navigate is a sectoral integrated assessment model for simulating the maritime industry's transition toward zero-carbon shipping. It models fleet investment decisions, fuel production, bunkering operations, and regulatory impacts over multi-decade timelines.

## Installation

Navigate needs Python 3.13 or newer; it is tested on Python 3.13.
It is recommended that Navigate is installed within an environment such as [conda](https://continuumio-docs.readthedocs-hosted.com/miniconda/) or [venv](https://docs.python.org/3/library/venv.html).

### Navigate + Assumptions & Simulations (Preferred)
- Clone the repository and run `pip install .` in the directory.
- Set the environment variable `ASSUMPTIONS_DATA_DIR` to point to the `assumptions` folder.

### Navigate PyPI Package
- `pip install navigate-zcs` Installs only Navigate.


#### Optional: Gurobi solver (commercial license)
Navigate ships with the open-source [HiGHS](https://highs.dev/) solver and uses it by default — no further setup is needed. If you have a [Gurobi](https://www.gurobi.com/) license, you can install the faster Gurobi backend as an optional extra `pip install .[gurobi]`.

### For development
- Clone the repository and run `make pip-setup` in it, with `python3.13` on the path: it creates a `.venv` in the checkout with Navigate installed in editable mode and the development tools. `make conda-setup` does the same in a conda environment named `nav`.
- [CONTRIBUTING.md](CONTRIBUTING.md) describes how a change gets in; [AGENTS.md](AGENTS.md) is the entry point for the coding agents that develop Navigate.


## Usage

Navigate is a command-line tool that is run from the terminal:

```bash
navigate my_simulation.nav
```

A run writes two files next to the deck:

- `my_simulation.parquet`: every result of the run, one row per series and date, with the unit of each series in its metadata. See [Results file](docs/reference_manual/results_file.md).
- `my_simulation.log`: the run's log, with every warning and error. The terminal shows the progress and the number of warnings.

`--name` and `--output-dir` change their names and folder.

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


## Horizon and Lantern

Two companion tools work with Navigate's runs:

- [Horizon](https://github.com/zerocarbonshipping/horizon-zcs/tree/dev) runs uncertainty studies. It samples the `%NAME%` placeholders of a deck over their ranges (Latin hypercube or Monte Carlo), starts one Navigate run per sample, on this machine or through a queue such as pueue or slurm, and gathers the results into one file per study. It runs the `navigate` command, so it is installed in the same environment.
- [Lantern](https://github.com/zerocarbonshipping/lantern-zcs/tree/dev) plots Navigate's results files. It opens one run or many, a Horizon study included, as interactive plots in the browser, or writes the plots as HTML pages and the rows as CSV.


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

<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Navigate

Navigate is a sectoral integrated assessment model for simulating the maritime industry's transition toward zero-carbon shipping. It models fleet investment decisions, fuel production, bunkering operations, and regulatory impacts over multi-decade timelines.

## Disclaimer

Navigate is an open-source analytical model intended for research and scenario analysis of maritime decarbonisation pathways. The model, its assumptions and any outputs are provided for illustrative and analytical purposes only.

Model outputs depend on the assumptions selected by the user and should not be interpreted as forecasts, benchmarks, recommendations or commercially optimal outcomes, nor as legal, financial or investment advice.

Users are responsible for selecting and adapting assumptions appropriate to their own circumstances and for exercising their own independent judgement when interpreting or relying on any model outputs.

## Tutorials and Example Simulations

Detailed installation guide, step-by-step tutorials and a full reference manual are available in the [documentation](https://zerocarbonshipping.github.io/navigate-zcs/). The tutorial project files live in the `tutorials/` folder.
Some simple example simulations can be found under `simulations/examples`

## Installation

Navigate is built on Python version 3.12. You can download Navigate by cloning it to your local machine or by downloading one of the releases.
We recommend using an environment manager such as [conda](https://www.anaconda.com/docs/getting-started/miniconda) or [venv](https://docs.python.org/3/library/venv.html) to avoid conflicts with other packages and versions.

### Setting up an environment (optional but recommended)
```bash
# Using venv (bundled with Python)
python3.12 -m venv .venv
source .venv/bin/activate
# Using conda (https://www.anaconda.com/docs/getting-started/miniconda/install)
conda create -n nav python=3.12 pip
conda activate nav
```

### Installing Navigate

Install navigate using pip from within the Navigate folder after cloning the repository:
```bash
pip install .
```

### Optional: Gurobi solver (commercial license)

Navigate ships with the open-source [HiGHS](https://highs.dev/) solver and uses it by default — no further setup is needed. If you have a [Gurobi](https://www.gurobi.com/) license, you can install the faster Gurobi backend as an optional extra:

```bash
pip install .[gurobi]
```

The default `--solver auto` then detects the license and uses Gurobi automatically. Note that installing `gurobipy` from pip only includes a size-limited trial license that cannot solve full Navigate scenarios — without a full Gurobi license, skip this extra (or run with `--solver highs`).

## Running Navigate

Navigate is run from the command line using the following command:

```bash
navigate my_nav_file.nav
```

For example, to run the basecase scenario with the included assumptions:

```bash
navigate simulations/scenarios/basecase_mid_regulation/basecase_mid_regulation.nav -d ./assumptions
```

Expect a full scenario run to take roughly 25 minutes on the bundled open-source HiGHS solver. The four reference scenarios are described in [`simulations/scenarios/README.md`](simulations/scenarios/README.md).

### Arguments

The following options are available when running Navigate. See them in the command line by typing `navigate --help`.

| Flag                            | Description                                                                                                                                                                                                                                                       |
|---------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `-d DIR`, `--data-dir DIR`      | Folder location for assumptions that may be imported. Can also be set with the environment variable `ASSUMPTIONS_DATA_DIR`. <br/> The Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping supplies assumptions in the `assumptions` folder of this repository. |
| `-s`, `--suppress-plots`        | Suppress the generation of plots at the end of the simulation. Excel reports will still be generated.                                                                                                                                                             |
| `-l LEVEL`, `--log-level LEVEL` | Set the log level for the `.log` file. With `DEBUG`, a failed run also prints the full traceback to the console.                                                                                                                                                  |
| `-r PATH`, `--replot PATH`      | Regenerate plots from previously exported plot data. Provide path to directory containing `plot_data.pkl` or to the file directly. Skips simulation. Optionally pass a `.inc` file with `Plot` node(s) as the trailing argument to use those instead of the plot nodes stored in the plot data.  |
| `--solver {auto,gurobi,highs}`  | Solver backend. `auto` tries Gurobi then falls back to HiGHS. Default: `auto`.                                                                                                                                                                                    |
| `-p`, `--profile`               | Profile the computational performance of the simulation. Note that this suppresses all output that is not directly related to the simulation.                                                                                                                    |

## License

Copyright 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping.

Navigate is licensed under two licenses, depending on the type of content:

- The software — the `navigate` package, tests, and all build, tooling, and editor-support files — is licensed under the [Apache License 2.0](LICENSES/Apache-2.0.txt) (see also the root [LICENSE](LICENSE) file).
- The model content — assumptions, simulation and input files written in the Navigate DSL, tutorials, documentation, and figures — is licensed under [Creative Commons Attribution 4.0 International](LICENSES/CC-BY-4.0.txt) (CC-BY-4.0).

Every file declares its license through an `SPDX-License-Identifier` header or through the metadata in [REUSE.toml](REUSE.toml), following the [REUSE specification](https://reuse.software/). The full license texts are in the [LICENSES](LICENSES/) directory.

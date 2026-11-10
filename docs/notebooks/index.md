<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Notebooks

Workshop sessions that run a case end to end in a Jupyter notebook, on Google
Colab or on your own machine. Each page shows the notebook with the results of
a run, so it can be read without running it.

```{toctree}
:titlesonly:

notebook_1/notebook_1
```

## Running a notebook on your own machine

Colab needs nothing installed. To run a notebook locally instead, you need:

- **The notebook file.** Download it from its folder under
  [`docs/notebooks/`](https://github.com/zerocarbonshipping/navigate-zcs/tree/dev/docs/notebooks)
  on GitHub (*Download raw file*), or open it in a clone of the repository.
- **Python 3.13.** Navigate runs on 3.13 only.
- **A fresh environment** with that Python, for example
  `conda create -n navigate-notebook python=3.13` or
  `python3.13 -m venv .venv`. The setup cell installs Navigate, Horizon and
  Lantern into it and replaces any Navigate already there, an editable
  install included.
- **A Jupyter kernel in that environment**, `pip install ipykernel`, and a
  front end to run it: VS Code with its Jupyter extension, choosing the
  environment as the kernel, or JupyterLab (`pip install jupyterlab`)
  started from the activated environment. The `!navigate`, `!horizon` and
  `!lantern` lines are shell commands, and they find the programs only when
  the kernel runs with the environment active.
- **Git**, which the setup cell clones the repository with, and an internet
  connection for that clone and the installs; together they take a few
  minutes. No solver to install: HiGHS comes with Navigate.
- **`ROOT` set to a folder of your own** in the setup cell before you run it,
  such as `"/home/you/notebook"` or `"C:/notebook"`, with no spaces in its
  path; the default, `/content`, exists only on Colab. The cell clones
  Navigate into `ROOT/navigate-zcs`, copies the case into `ROOT/<case>` and
  moves there, so the results and plots land in that folder.

Running the setup cell again keeps the first clone, and git reports that the
folder already exists. It overwrites the copy of the case, edits to its files
included, and keeps the results of earlier runs. To start over with the latest
version, delete `ROOT/navigate-zcs` and `ROOT/<case>` first.

<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Introduction

Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping

This document is the user manual for the simulation model Navigate that is being developed by the Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping.

The goal of this document is to provide the reader with information that will allow them to create the files necessary to run a simulation using Navigate. We recommend using a text editor with syntax highlighting for creating and viewing these files. A VS Code extension and Notepad++ user defined language (UDL) files are included in the `syntax/` directory of the Navigate repository.

The input to Navigate is provided through a set of simulation files which follow a basic hierarchy. The main file which is passed to Navigate is called an `.nav` file. This file will contain paths to other files which are included in the simulation, known as `.inc` files.

Navigate is a node-based simulator. This introduction will explain how to define nodes and general nodes.

## Writing an `.nav` file

There are two file types needed for running a Navigate simulation: An `.nav` file and an `.inc` file. This section explains what a `.nav` file is and how to write one.

In the `.nav` file, i.e. "Navigate"-file, the user defines which `.inc` files (and the respective assumptions contained in the files) are included in a simulation.

The `.nav` file is split into two sections:

* `DEFINE`: All nodes must be defined here,
* `EVENTS`: Timeline (including changes to node attributes) is defined here.

The `DEFINE` section is initiated by the keyword:

`DEFINE {`

In the lines after the brackets, the different `.inc` files are referenced and included like the example below. When including a file the folder location must be defined. This can be done by setting the directory either using the absolute directory or a relative directory (in relation to the file location of the `.nav` file itself). An example of a relative path/directory is shown below:

`Include "../FolderA/file_name.inc"`

The user can also load pre-defined defaults, called modules, like this:

`Load ModuleName`

Notice that both the `DEFINE` and `EVENTS` section are terminated with a "}". The `EVENTS` section is initiated by the keyword:
`EVENTS {`.


```python
DEFINE {
    # load the default model configuration module
    Load DefaultModelDefinition

    # include files with nodes
    Include "includes/vessels.inc"
    Include "includes/ports.inc"
    Include "includes/fuels.inc"

    # load the default emission module
    Load DefaultEmission
}

EVENTS {
    # load a module which defines a yearly timeline
    Load DefaultTimeStepYearly
}
```
The purpose of the `EVENTS` section is to define the simulation timeline and introduce possible changes to node attributes. See [Default modules](dsl_reference.md#default-modules) for the available `Load` modules.



## Writing an `.inc` file

A `.inc` file contains information about nodes and if included in the `EVENTS` section also the timeline. As mentioned previously, all nodes must be defined in the `DEFINE` section while all references to the timeline must occur in the `EVENTS` section. For this reason, the `.inc` files in either section are also structured differently.

This section will illustrate syntax for defining and altering nodes and general nodes. How to interpret this syntax is explained in the subsequent sections [Defining a node](dsl_reference.md#defining-a-node) and [Defining a general node](dsl_reference.md#defining-a-general-node).

### DEFINE section:

An `.inc` file in the `DEFINE` section is made up entirely of a collection of nodes and general nodes.

```python
# define a general node
ModelDefinition {
    StartDate = "01-01-2024"
}

# define a node
Fuel "methanol_electro"{
    FuelType = METHANOL

    LowerHeatingValue = Variable("lower_heating_value_methanol")
    MassDensity = 0.791
    
    set_ttw("carbon_dioxide", 1.38)
}

# define another node
Plant "plant_methanol_electro"{
    Fuel = Fuel("methanol_electro")
    Capacity = 300
}

# reassign an attribute on an already defined node
Plant "plant_methanol_electro"{
    Capacity = 500
}
```


As can be seen different attributes require different types of values. This will be further introduced in the section [Assigning attributes](dsl_reference.md#assigning-attributes) and [Assigning commands](dsl_reference.md#assigning-commands).

### EVENTS section:

Simulations in Navigate are predicting certain outcomes over time based on a set of assumptions. For every Navigate simulation, a start date is defined in the [ModelDefinition](model_definition.md) general node.

When the user wants Navigate to run simulations until 2050 (or another time in the future), intermediate time steps until 2050 must be defined separately that the model runs through. Annual time steps are used in the production version of Navigate, but the user could also decide on defining monthly, quarterly, or 5-year time steps, for example.

A time step is written as a date:

`Date "dd-mm-yyyy"`, `Date "dd/mm/yyyy"` or `Date "yyyy-mm-dd"`.

For convenience the keyword `Start` stands for the `StartDate` defined in the `ModelDefinition`. Every `Start` and `Date` read in the `EVENTS` section becomes a time step of the simulation; the start date is always one, whether or not a file names it.

Changes to nodes apply at the last date read before them in the file, so a node block must follow a `Start` or a `Date`. There is no order to keep: the dates of all `EVENTS` files are collected and sorted, and a file may name its dates in any order. Where two files change the same attribute at the same date, the file included later wins, and a block under `Start` runs before a block dated on the start date. A date earlier than the start date is an error.

A file typically opens with `Start`, or with the `Date` from which its assumptions apply, e.g. a policy introduced on the 1st January 2030, followed by the dates and node blocks. The `End` keyword of earlier versions is still accepted but has no effect.

Below is an example of an `.inc` file included in the `EVENTS` section that complements the definition of the start date "01-01-2024" in the `ModelDefinition` introduced previously.

```python
# start the timeline at "01-01-2024" as defined in ModelDefinition
Start

Date "01-01-2025"
Date "01-01-2026"
Date "01-01-2027"
Date "01-01-2028"
Date "01-01-2029"
Date "01-01-2030"

# reassign an attribute on a node which was defined in the DEFINE section
Plant "plant_methanol_electro"{
    Capacity = 1000
}

Date "01-01-2031"
Date "01-01-2032"
Date "01-01-2033"
Date "01-01-2034"
Date "01-01-2035"
Date "01-01-2036"
Date "01-01-2037"
Date "01-01-2038"
Date "01-01-2039"
Date "01-01-2040"
Date "01-01-2041"
Date "01-01-2042"
Date "01-01-2043"
Date "01-01-2044"
Date "01-01-2045"
Date "01-01-2046"
Date "01-01-2047"
Date "01-01-2048"
Date "01-01-2049"
Date "01-01-2050"
```

This example defines that the simulation should take yearly time-steps from "01-01-2024" (`Start`) and until "01-01-2050". At the date "01-01-2030" the plant capacity of a node that was already defined in the `DEFINE` section is reassigned.

## Reading the `.log` file

A simulation with Navigate always produces a log file with the extension `.log`, written next to the `.nav` file with the same base name (e.g., running `basecase.nav` produces `basecase.log`). The verbosity of the log is controlled with the `-l`/`--log-level` command line option. The file includes information about how the simulation is progressing. It includes information about three main aspects:

1. Reading the simulation deck
2. Initialization of the model
3. Time-step procedure

Information is provided in four levels, namely:

1. `DEBUG`
2. `INFO`
3. `WARNING`
4. `ERROR`

`DEBUG` is the most verbose level and adds diagnostic detail that is mainly useful when investigating a problem. Running with `-l DEBUG` also prints the full Python traceback to the console if the run fails, instead of only the error message.

`INFO` stands for information and refers to general information such as which solver backend is used or that plot rendering finished:

```
14:29:15 [INFO] navigate.simulation.bunker.solver_backend: Gurobi not available -- using HiGHS solver backend.
14:29:16 [INFO] navigate.simulation.bunker.bunker_algorithm: Fair-share bunkering convergence status: Successful.
14:29:47 [INFO] navigate.output.plots.render: Plots generated successfully.
```

`WARNING` refers to information that has an impact on results. This could be if the code makes automated adjustments to the simulation deck or things that will impact the results in different ways:

```
14:29:16 [WARNING] navigate.simulation.fleet.speed: Vessel("bulk_carrier_handysize"): Does not have convex load functions which may lead to suboptimal speed management results.
```

`ERROR` means a problem was encountered which was detrimental to the continuation of the simulation. This will occur if there is a spurious formulation in the simulation deck which is not recognized by Navigate. Deck errors state the deck file, the include file, and the line at which the problem occurred:

```
14:29:16 [ERROR] navigate.app.cli: Fatal error: Error in deck file, line 2, include file '/home/user/sim/includes/fuels.inc', line 14: Nodes of type 'Fuel' has no command 'set_wtw'.
```

If an ERROR occurs the simulation stops: the console shows the error message on its own (run with `-l DEBUG` to also see the full Python traceback there), and the `.log` file records the error together with its full traceback regardless of the chosen log level.

At the end of a successful run the log closes with a summary table counting the messages of each level, followed by the unique warnings with how often each was logged. When warnings were logged, the console also prints their count with a pointer to the `.log` file.

Besides the log file, a run may also produce artifacts in the deck directory: plots when the deck contains a [Plot](plot.md) node, unless suppressed with the `-s`/`--suppress-plots` flag, and Excel or CSV reports when the deck contains [Report](report.md) nodes.

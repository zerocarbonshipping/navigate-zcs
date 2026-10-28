<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# DSL reference

## Defining a node

To define a node, use the following syntax:

```python
NodeType "node_name" {
}
```

When specified in `.inc` files, a node is referred to by its name: `NodeType "node_name"`.

To reference a node in other nodes, use the following syntax:

```python
NodeType("node_name")
```

An example of a node’s general structure is included below:

```python
NodeType "node_name" {
    Attribute = ValueA
    set_command("key", ValueB)
}
```

The first time the node syntax is encountered in an `.inc` file is when it is defined. It is possible to access the node again using the same syntax to change the attributes of the node. This can be done both during the `DEFINE` section and the `EVENTS` section. However, certain attributes do not allow change during the `EVENTS` section and will throw an error if attempted. A calculator node, such as a `Variable` or a `Forecast`, assigned to such an attribute, or to a command that does not allow change during the `EVENTS` section, is fixed with it, whether assigned directly, in a list or through an expression: none of its own attributes can be changed during the `EVENTS` section either, and the deck is rejected when it is read if one is. This holds even when a later `DEFINE` command rewrites the same entry with another value. A calculator held only by attributes that allow change in `EVENTS` can still be changed there. Notice that redefinition of attributes occurs in the order they are read. Meaning if an attribute is redefined further down in an `.inc` file or in a later `.inc` file it is the last read instance that will be the final value; a reference the earlier assignment made is then never looked up.

## Defining a general node

A general node differs from a node in that there is only one instance of a general node and in that it cannot be referenced in other nodes. Currently, there are only few general nodes used in Navigate. For example, the `ModelDefinition` is a general node that only occurs once.

To define a general node, use the following syntax:

```python
NodeType {
}
```

An example of a general node’s structure is included below:

```python
NodeType {
    Attribute = ValueA
}
```

General nodes carry attributes only — they do not support commands — and can only be defined in the `DEFINE` section.

## Assigning attributes

Attributes are assigned on nodes and general nodes. An assignment to an attribute has the following syntax:

```
Attribute = x
```

Where `x` depends on the specific attribute. Attributes are written in upper camel case, e.g., `MinimumOfftakeDuration` and `Capex`. The syntax of the value assigned to the attribute depends on the specific attribute but the different options are listed below.

**Float:**  
  ```python
  Attribute = 3.2
  ```
  `INF` and `-INF` are accepted only where infinity has a meaning: by `set_bunkering_limit`, `set_feed_constraint` and `MaximumSpeedChange`, where `INF` means no limit, by `UpperBound` (`INF`) and `LowerBound` (`-INF`), and by the values that define a calculator (`Value`, `Below`, `Above`, `Outside` and the values of a table), which are checked against each attribute using the calculator, as described under node references. Every other attribute rejects them when the deck is loaded. The coordinates of a table must be finite, and no table cell may be `nan`; the values of the tables of `set_existing_pipeline` and `InitialAgeDistribution`, which are read as tables rather than evaluated, must be finite too.

**Node reference:**  
  ```python
  Attribute = NodeType("node_name")
  ```
  Where the attribute has a minimum or maximum value, it also holds for the value a referenced Curve, Forecast, Surface, Timetable, or Variable returns, and for the value of an expression, each time it is evaluated. An inclusive minimum or maximum clamps the value to it. A value that reaches an exclusive one, such as `0` where the minimum value is 0 (exclusive), stops the run with an error naming the node, just as the same number written as a float is rejected when the deck is loaded. An attribute that rejects `INF` and `-INF` treats a side without a minimum or maximum as an exclusive bound at infinity: a value reaching infinity there stops the run the same way, while on a side with an inclusive minimum or maximum it is clamped, so a Forecast at `INF` assigned to `Uptime` evaluates to 1. A calculator referenced by several attributes is held to the strictest bound among them, so a Variable used both in `set_bunkering_limit` and by an attribute that rejects `INF` cannot be `INF`.

**ID:**  
  ```python
  Attribute = SPECIFIC_ID
  ```
  Notice that IDs are capitalized and potentially separated by underscores.

**Boolean:**  
  ```python
  Attribute = TRUE
  ```
**List:**  
  ```python
  Attribute = [0, 1, NodeType("node_name")]
  ```
  A list can be defined over several lines:
  ```python
  Attribute = [
      0,
      1,
      NodeType("node_name"),
  ]
  ```

  For list attributes that accept a single element, the brackets may be omitted:
  ```python
  Attribute = NodeType("node_name")
  ```
  is equivalent to:
  ```python
  Attribute = [NodeType("node_name")]
  ```
  Multi-element assignments still require brackets.

## Assigning commands

Commands are used when an attribute may hold different values based on other nodes. An example is that a fuel may have a tank-to-wake (TTW) emission per emission included in the simulation files. Commands may either take one or two keys and a value. The syntax is:

**Single key command:**  
  ```python
  set_single_command("node_name", 3.2)
  ```
**Double key command:**  
  ```python
  set_double_command("node_name", SPECIFIC_ID, 3.2)
  ```

The assignment options via commands are limited to floats, node references, and boolean values.

## Assigning tables

A specific category of nodes allows assignment of tables to the node. The list of nodes includes:

- `Curve`
- `Forecast`
- `Surface`
- `Timetable`

A table is written as rows of cells between `Table = [` and `]`. The cells of a row are separated by commas, and every row ends with a `;`. A cell is a number, `INF` or `-INF`, or a date, written `"dd-mm-yyyy"`, `"dd/mm/yyyy"` or `yyyy-mm-dd`. Comment lines are allowed inside the table. A row that misses its `;` runs into the next, which is a syntax error at the next row's first cell.

Dependent on the node, the table is defined in different ways:

### Curve

The syntax for defining a table on a curve is as follows:

```python
Curve "node_name" {
    Table = [
        # x y
        0.0, 1.0;
        0.5, 2.0;
        1.0, 4.0;
    ]
}
```

### Forecast

The syntax for defining a table on a forecast is as follows:

```python
Forecast "node_name" {
    Table = [
        # x y
        "01-01-2024", 1.0;
        "01-01-2030", 2.0;
        "01-01-2050", 4.0;
    ]
}
```

The x-axis of a forecast may also be defined by floats, which should be interpreted as "days since start of simulation." For example, if the simulation start date is `01-01-2024`, then the date `01-01-2025` would be `366` (leap years are accounted for). In this case, it follows the syntax of a curve but with the node type being forecast.

### Surface

A surface is a two-dimensional curve and has the syntax:

```python
Surface "node_name" {
    Table = [
        # y-axis (header row)
        # x-axis (first cell of every subsequent row)
        0, 1, 2;
        0, 0, 1, 2;
        10, 3, 4, 12;
        20, 20, 21, 22;
    ]
}
```

Here, the header row is the y-axis and is defined by `ny` entries corresponding to the number of points along the y-axis. Every subsequent row is defined by `ny+1` entries, with the first value being the x-axis value and all subsequent values the z-values for that x-value and all y-values. The number of points along the x-axis, `nx`, is given by the number of rows below the header.

### Timetable

A timetable is a two-dimensional mixture of a curve and a forecast and has the syntax:

```python
Timetable "node_name" {
    Table = [
        # y-axis (header row)
        # x-axis (first cell of every subsequent row)
        0, 1, 2;
        "01-01-2024", 0, 1, 2;
        "01-01-2030", 3, 4, 12;
        "01-01-2050", 20, 21, 22;
    ]
}
```

Similar to the forecast, the x-axis of a timetable may be defined by floats rather than dates.

## Expressions

An expression is a syntax that allows the use of arithmetic when assigning values to attributes and commands. The syntax is:

```python
Attribute = <a + b - c / d>
set_command("key", <a + b - c / d>)
```

An example could be separating values to better comment and explain an assumption in the simulation file:

```python
Attribute = <0.05 * 1e6>
set_command("key", <0.05 * 1e6>)
```

It is also possible to include Curves, Forecasts, Surfaces, Timetables, and Values in an expression. However, the node used must align the data type allowed by the attribute:

```python
Attribute = <0.5 * Forecast("name_1") + Forecast("name_2")>
set_command("key", <0.5 * Forecast("name_1") + Forecast("name_2")>)
```

An expression's value is held to the attribute's minimum and maximum value the way a referenced node's is (see [Assigning attributes](#assigning-attributes)).

An expression is accepted only where the value is used as a number: an attribute or command that accepts scalars, or one accepting a Curve, Forecast, Surface, Timetable, or Variable that it evaluates. Where a node is expected as such — a `Port` in `Jurisdiction`, a `Fuel` on a `Plant`, the Curves of `InitialAgeDistribution`, or the Forecast of `set_existing_pipeline`, which are read as tables — an expression is rejected when the deck is loaded, even one that only names the node:

```python
Jurisdiction = <Port("name")>    # rejected; write Jurisdiction = Port("name")
```

Expressions are restricted arithmetic, not general Python. The only accepted syntax is: numeric literals (including scientific notation such as `1e6`) and `INF`, the operators `+`, `-`, `*`, `/`, and `**`, unary plus and minus, parentheses for grouping, and node references of the form `Type("name")` with a single string argument. Anything else — names, comparisons, other function calls, and so on — is a syntax error at its line when the deck is loaded. In particular, expressions cannot execute code or access the file system.


## Unreachable nodes

A defined node only participates in the simulation when a chain of node references connects it to a top-level node: `Fleet`, `Producer`, `Levy`, `Regulation`, `Emission`, or `Fuel`. For example, a `Converter` participates when it is assigned to a `Vessel` that is itself assigned to a `Fleet`.

Once the deck is read, Navigate keeps the nodes with such a chain and no others, and logs one warning listing the nodes it declared but did not use. An unused node produces no results and its attribute values are not checked. A reference it makes is looked up in the default library like any other reference, but one found nowhere is not an error. `EVENTS` blocks targeting only unused nodes are dropped with a warning; a block naming a node the deck never declared is an error. A node referenced only from an `EVENTS` block is kept, provided the block's target is itself part of the simulation. A node used only as the source of a `Copy` is not reported — its copies carry its role.

Only node references count. Plain name strings in commands (e.g. `set_export_distribution("port_name", ...)`) do not, and a command naming an unused node raises an error.

A `Port` is part of the simulation only through a `Route`'s `Ports` attribute, since only routed ports can be bunkered in. A `Levy`/`Regulation` `Jurisdiction` selects among routed ports and does not keep a port alive: a port on no route is left out even when a jurisdiction names it, and is dropped from the `Jurisdiction` list with a warning, while `Jurisdiction = Port("*")` selects the routed ports. A port named in a `Jurisdiction` must still exist in the deck or the default library. A `Jurisdiction` emptied this way fails with the unassigned-attribute error.

## Default nodes

Navigate comes with a substantial library of default nodes which may be included in the simulation model.

If a node is assigned to another node’s attribute, then the assigned node must be defined somewhere else in the simulation files. A node must not reference itself, directly, through a wildcard or inside an expression; Navigate rejects the deck at the line of such a reference. If the assigned node is not assigned elsewhere, Navigate will search for the node in the default library and throw an error if no match is found.

The default node folder can be found in:

`<data_dir>/defaults/<NodeType>/`

where `<data_dir>` is the assumptions directory given with `-d`/`--data-dir` on the command line, or with the `ASSUMPTIONS_DATA_DIR` environment variable, and `<NodeType>` is the node's type, e.g. `Fuel` or `Route`.

Technically speaking default node files can contain more than one node, however, it is best practice to separate into individual files. Default files may import or copy other default nodes, but not in a cycle: a default file that pulls, directly or through other default files, the node it is read for is rejected.

To change a default for one simulation, import it in the deck and reassign the attributes to change, as described in "Importing a node". To change defaults for every simulation, keep your own copy of the assumptions directory and pass it with `-d`.

## Default modules

Similar to default nodes, it is possible to define default modules. A module is the same as a normal `.inc` file included in the `.nav` file but is a convenient way of storing these if it is an `.inc` file that is used often across multiple simulation decks.

The default module folder can be found in:

`<data_dir>/modules/`

where `<data_dir>` is the same assumptions directory as for default nodes.

## Importing a node

It is possible to import nodes directly from the default folders using the syntax:

```python
Import NodeType "node_name"
```
This defines the node. Subsequent to this it is possible reassign a subset of attributes on the node as described in "Defining a node".

## Copying a node

It is possible to copy a node either from a node already defined in the simulation files or directly from the default folders using the syntax:

```python
Copy NodeType "node_copy_from" "node_copy_to"
```

The copy takes the definition of `"node_copy_from"` as it stands at the `Copy`, so a later reassignment of `"node_copy_from"` is not reflected in `"node_copy_to"`: they are two separate nodes.
Only the copied node itself is duplicated: the nodes it references are shared, so a reassignment to one of those is seen by both.

If the node being copied from does not already exist in the simulation then it is removed after the import and only the node of the name "node_copy_to" remains.
This can be used to import nodes with a different name than default name.

This removal only undoes the pull the `Copy` itself made. If a separate `Type("node_copy_from")` reference appears anywhere else in the deck, that reference pulls the source from the default library again as its own, independent node, so both `"node_copy_from"` and `"node_copy_to"` end up registered as separate nodes.

A general node, such as `ModelDefinition` or `BunkerOptions`, cannot be copied: a deck holds exactly one instance of each, so there is never a second name for a copy to take. A `Copy` naming one of these is rejected when the deck is read.

## Wildcards

Navigate accepts glob-style wildcards in node names and in the string keys of commands, letting a single pattern stand in for many concrete values, matched as Python's `fnmatch` does:

* `*` matches zero or more characters.
* `?` matches exactly one character.
* `[abc]` matches one character of the set, `[!abc]` one character outside it.

A pattern may be the bare wildcard `"*"` (matches every value) or a partial pattern that combines wildcards with literal characters, e.g. `"bio_*"`, `"port_?"`, or `"*_2030"`. Wildcards are written inside the quotes.

Wildcards are resolved at the point of use, against what the construct they are written in matches. A wildcard node reference is expanded against every node of that type in the simulation, those pulled from the default library included, once the whole deck is read and before the value reaches the attribute, so the attribute is given the matched nodes themselves and treats them exactly as it would the same nodes written out by name. A wildcard node name on a declaration, `Vessel "bulk_*" { ... }`, matches the nodes declared before it in the deck. A wildcard in a command's string key is resolved against the existing keys of the dictionary the command writes. The expanded pattern must match at least one value; otherwise an error is raised.

The following constructs accept wildcards:

* **List attribute assignments.** A wildcard node reference expands to every registered node of that type whose name matches the pattern. It may be written inside the list or as the whole value of the attribute: `Fuels = [Fuel("bio_*")]` and `Fuels = Fuel("bio_*")` are equivalent. For example, `Ports = [Port("*")]` on a Route assigns every Port in the simulation, and `Fuels = Fuel("bio_*")` on a Regulation assigns every Fuel whose name begins with `bio_`. A wildcard is only valid where a list of nodes is accepted: an attribute holding a single node, such as `Route` on a Vessel, rejects it, as does a command argument — the wildcards a command accepts are the string-key form below.

* **Commands with string arguments.** Wildcards in a command's string key(s) expand against the existing entries of the dictionary the command writes to. For example, `set_initial_technology_share("*", "hull_painting", Curve("..."))` applies the assignment to every existing vessel key, and `set_fuel_conversion_cost("*ice_oil*", "*ice_methanol*", 13.4e6)` matches every from/to vessel pair whose names contain the substrings.

## Placeholders

A `%NAME%` in a deck or in any file it reads, `NAME` being letters, digits and underscores not starting with a digit, is a placeholder for a value given on the command line with `--set NAME=VALUE`. Before a file is read, each placeholder is replaced by its value as text, so a placeholder may stand anywhere the value could be written: a number, part of an expression, a table cell, the items of a list, or part of an `Include` path in the deck.

```python
DEFINE {
    Include "policy/policy_%policy%.inc"
}
```

```python
Forecast "ammonia_blue_plant_capacity" {
    Multiplier = %plant_capacity_multiplier%
}

Plant "*blue*" {
    CostOfCapital = <Forecast("cost_of_capital_plant_blue") * %wacc_multiplier%>
}
```

Placeholders in comments are left as written. A placeholder outside a comment without a `--set` value is an error at its file and line, and a `--set` value no file uses is logged as a warning. The values are recorded in the [results file](results_file.md#metadata). A run with `--set` is one of many of its deck, so it writes its log into the `logs` and its results file into the `parquets` subfolder of the output folder. A deck written with placeholders, as Horizon reads it, may end in `.unc` instead of `.nav`.

## Reading the node description

Each node type in Navigate is listed and explained in the node index, including the attributes that a user
can set for the nodes.

Every section contains a short explanation of the node type, how it can be defined in the input files as well
as an example of a defined node.

For each attribute, a number of relevant characteristics are listed:

* Data type
* Unit
* Legal values
* Example values
* Minimum value
* Maximum value
* Default

Some attributes must be defined by the user because they are mandatory for the node and no default is assigned.

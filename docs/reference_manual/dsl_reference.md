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

The first time the node syntax is encountered in an `.inc` file is when it is defined. It is possible to access the node again using the same syntax to change the attributes of the node. This can be done both during the `DEFINE` section and the `EVENTS` section. However, certain attributes do not allow change during the `EVENTS` section and will throw an error if attempted. Notice that redefinition of attributes occurs in the order they are read. Meaning if an attribute is redefined further down in an `.inc` file or in a later `.inc` file it is the last read instance that will be the final value.

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

Where `x` depends on the specific attribute. Attributes are written in upper camel case, e.g., `MinimumOfftakeDuration` and `CAPEX`. The syntax of the value assigned to the attribute depends on the specific attribute but the different options are listed below.

**Float:**  
  ```python
  Attribute = 3.2
  ```
**Node reference:**  
  ```python
  Attribute = NodeType("node_name")
  ```
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

Dependent on the node, the table is defined in different ways:

### Curve

The syntax for defining a table on a curve is as follows:

```python
Curve "node_name" {
    Table = [
        # x y
        0.0 1.0
        0.5 2.0
        1.0 4.0
    ]
}
```

### Forecast

The syntax for defining a table on a forecast is as follows:

```python
Forecast "node_name" {
    Table = [
        # x y
        "01-01-2024" 1.0
        "01-01-2030" 2.0
        "01-01-2050" 4.0
    ]
}
```

The x-axis of a forecast may also be defined by floats, which should be interpreted as "days since start of simulation." For example, if the simulation start date is `01-01-2024`, then the date `01-01-2025` would be `366` (leap years are accounted for). In this case, it follows the syntax of a curve but with the node type being forecast.

### Surface

A surface is a two-dimensional curve and has the syntax:

```python
Surface "node_name" {
    Table = [
        # x-axis (top line)
        # y-axis (first in rows)
        0 1 2
        0 0 1 2
        10 3 4 12
        20 20 21 22
    ]
}
```

Here, the first line is the x-axis and is defined by `nx` entries corresponding to the number of points along the x-axis. Every subsequent row is defined by `nx+1` entries, with the first value being the y-axis value and all subsequent values corresponding to the interior values for that y-value and all x-values. The number of points along the y-axis, `ny`, is given by the number of lines in the table (excluding the first).

### Timetable

A timetable is a two-dimensional mixture of a curve and a forecast and has the syntax:

```python
Timetable "node_name" {
    Table = [
        # x-axis (top line)
        # y-axis (first in rows)
        0 1 2
        "01-01-2024" 0 1 2
        "01-01-2030" 3 4 12
        "01-01-2050" 20 21 22
    ]
}
```

Similar to the forecast, a timetable may be defined by floats in the y-axis, which are interpreted as "days since start of simulation."

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

Expressions are restricted arithmetic, not general Python. The only accepted syntax is: numeric literals (including scientific notation such as `1e6`), the operators `+`, `-`, `*`, `/`, and `**`, unary minus, parentheses for grouping, and node references of the form `Type("name")` with a single string argument. Anything else — names, comparisons, other function calls, and so on — is rejected with an error when the deck is loaded. In particular, expressions cannot execute code or access the file system.


## Unreachable nodes

A defined node only participates in the simulation when a chain of node references connects it to a top-level node: `Fleet`, `Producer`, `Levy`, `Regulation`, `Emission`, `Fuel`, `Report`, or `Plot`. For example, a `Converter` participates when a `PowerSystem` referencing it is assigned to a `Vessel` that is itself assigned to a `Fleet`.

After the `DEFINE` section is processed, Navigate removes every node without such a chain and logs one warning listing them. Removed nodes produce no results, and `EVENTS` re-assignments targeting only removed nodes are dropped. A node referenced only from an `EVENTS` re-assignment is kept, provided the re-assignment's target is itself reachable. A node used only as the source of a `Copy` is removed silently — its copies carry its role.

Only node references count towards reachability. Plain name strings do not — neither in commands (e.g. `set_export_distribution("port_name", ...)`) nor in `Report` property requests. A command naming a removed node raises an error; a `Report` property request matching no node logs a warning at export and is skipped.

## Default nodes

Navigate comes with a substantial library of default nodes which may be included in the simulation model.

If a node is assigned to another node’s attribute, then the assigned node must be defined somewhere else in the simulation files. If the assigned node is not assigned elsewhere, Navigate will search for the node in the default library. The default library is split into two branches, a "user" branch and an "installation" branch. The user branch allows others to define their own default nodes without mixing them with the default nodes provided by the Navigate installation which are found in the installation branch. Navigate will first search in the user branch for defaults before going to the installation branch and ultimately throw an error if no match is found.

The default node folder can be found in:

`<your_installation_path>/Navigate/navigate/defaults/`

Technically speaking default node files can contain more than one node, however, it is best practice to separate into individual files.

## Default modules

Similar to default nodes, it is possible to define default modules. A module is the same as a normal `.inc` file included in the `.nav` file but is a convenient way of storing these if it is an `.inc` file that is used often across multiple simulation decks.

Like the default nodes, the default modules have a user and an installation branch.

The default module folder can be found in:

`<your_installation_path>/Navigate/navigate/modules/`

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

After copying any reassignment of attributes done to `"node_copy_from"` will not be reflected in `"node_copy_to"` as they are now two separate nodes.

If the node being copied from does not already exist in the simulation then it is removed after the import and only the node of the name "node_copy_to" remains.
This can be used to import nodes with a different name than default name.

## Wildcards

Navigate accepts glob-style wildcards in node names and identifiers, letting a single pattern stand in for many concrete values. Two wildcard characters are supported:

* `*` matches zero or more characters.
* `?` matches exactly one character.

A pattern may be the bare wildcard `"*"` (matches every value) or a partial pattern that combines wildcards with literal characters, e.g. `"bio_*"`, `"port_?"`, or `"*_2030"`. Wildcards are written inside the quoted node name; for enum identifiers in commands they are written inline without quotes (e.g. `M*`).

Wildcards are resolved at the point of use against the set of registered nodes, the relevant enum members, the existing keys of a target dictionary, or the file names in the default-node folders — depending on the construct. The expanded pattern must match at least one value; otherwise an error is raised.

The following constructs accept wildcards:

* **List attribute assignments.** A wildcard node reference inside a list expands to every registered node of that type whose name matches the pattern. For example, `Ports = [Port("*")]` on a Route assigns every Port in the simulation, and `Fuels = [Fuel("bio_*")]` on a Regulation assigns every Fuel whose name begins with `bio_`.

* **Commands with string arguments.** Wildcards in a command's string key(s) expand against the existing entries of the dictionary the command writes to. For example, `set_initial_technology_share("*", "hull_painting", Curve("..."))` applies the assignment to every existing vessel key, and `set_fuel_conversion_cost("*ice_oil*", "*ice_methanol*", 13.4e6)` matches every from/to vessel pair whose names contain the substrings.

* **Commands with enum arguments.** Wildcards in an enum-typed argument (written inline, without quotes) expand against the enum's member names. For example, `set_slip_fraction(M*, 0.03)` applies the assignment to both the `METHANE` and `METHANOL` members of `FuelTypeID`.

* **Import statements.** Wildcards in an `Import` directive match the file names of `.inc` files in the user and installation default folders. For example, `Import Converter "electrical_ice_methane_*"` imports every default Converter whose file name begins with `electrical_ice_methane_`.

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

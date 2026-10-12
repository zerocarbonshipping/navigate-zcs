<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: CC-BY-4.0
-->

# Results file

Every run writes its full results to one Parquet file, `<deck>.parquet` next to
the deck, or to the path given with `-o`/`--results`. Open it with
[Lantern](https://github.com/zerocarbonshipping/lantern-zcs) to browse the
plots, or read it with any Parquet reader, for example polars, pandas or DuckDB:

```python
import polars as pl

results = pl.read_parquet("my_deck.parquet")
emissions = results.filter(pl.col("attribute") == "total_equivalent_wtw", pl.col("kind") == "global")
```

Unlike a [Report](report.md), which writes the properties a deck asks for, the
results file holds every result of every node with a profile: the same values
the report properties give, and nothing else. Node inputs, such as a fuel's
fuel type or a fleet's trade target, are not in it. A Report remains the way to
get a spreadsheet laid out for reading.

## Table

The table is long: one row per series and date. A series whose values are all
below 1e-5 in magnitude or missing is left out.

| Column | Type | Content |
|---|---|---|
| `kind` | string | `global`, `fleet`, `vessel`, `port`, `plant`, `producer`, `regulation` or `levy` |
| `node` | string | Node name; empty for `global` |
| `attribute` | string | Result name, e.g. `consumed_energy`, `total_equivalent_wtw`, `is_active` |
| `key1` | string or missing | First key of a result kept per fuel, fuel type, vessel, ... |
| `key2` | string or missing | Second key of a result kept per pair, e.g. (fuel, emission) |
| `date` | date | Date of the time step |
| `value` | float or missing | Value; `true`/`false` results are 1 and 0. Missing marks a value that is not set or has no bound, such as a feed constraint without limit |

Keys that are identifiers, such as fuel types or energy demand types, are
written by name (`OIL`, `PROPULSION`, see [Appendix: IDs](appendix_ids.md)). The
result names are those of the report properties in snake case: the report
property `TotalEquivalentWtw` is the attribute `total_equivalent_wtw`.

Values are per year where the unit says so. The results that count what
happened in a time step, `newbuilds`, `scrap`, `fuel_conversions`,
`newbuild_power`, `scrapped_power`, `fuel_converted_power` and `development`,
are divided by the length of the step in years of 365.25 days, the first step
counting as one year. The report gives them per step instead: with yearly time
steps the two differ only by the length of the calendar year. The `cumulative_`
results are the totals before each date, as in the report: a step's flow counts
from the next date on.

## Metadata

The Parquet key-value metadata holds a JSON document under the key `navigate`:

| Key | Content |
|---|---|
| `schema_version` | Version of this layout, currently `2`. It changes when a reader has to change. |
| `navigate_version` | Navigate version that wrote the file |
| `deck` | Name of the deck |
| `created` | Time the file was written, UTC, ISO 8601 |
| `units` | Unit of each attribute, e.g. `"consumed_energy": "GJ/year"`. `measure` means the unit of the regulation's measure. |

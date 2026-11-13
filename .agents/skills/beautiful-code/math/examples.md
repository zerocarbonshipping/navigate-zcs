<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# Mathematical examples

## Use mathematical notation

### Residuals of a linear system

#### Beautiful

```python
def calculate_residuals(A, b, x):
    r = b - A * x
    return r
```

What makes it good:
- For a subject matter expert in linear algebra `A` is instantly understood as the
  system matrix, `b` as the right-hand side, `x` as the variable vector and `r` as the
  residuals. This makes the code similar to mathematical notation and easy to
  understand

#### Ugly but correct

```python
def calculate_residuals(system_matrix, rhs, variables):
    residuals = rhs - system_matrix.multiply(variables)
    return residuals
```

What makes it bad:
- Even for such a small function the reader actually needs to read the lines and follow
  the logic rather than just scan it with the eyes to understand it

#### Preferred over a reasonable alternative

Missing examples.

#### Borderline

Missing examples.

## Keep plumbing out of the mathematics

### Iterating over nested collections

#### Beautiful

```python
sources = _get_conversion_sources(fleet, idx)

for (vessel, increment) in fleet.iterate_increments(reverse=True):

    if sources[vessel] is None:
        continue

    age = increment.age
    span = increment.span
    mult = increment.multiplier

    if not is_retrofit_cycle(age, frequency, dt):
        continue

    age_mid = age + span / 2.0
    lifetime = vessel.lifetime.get() - age_mid

    if lifetime <= 0.0:
        continue

    if mult <= 0.0:
        continue
```

What makes it good:
- The indexing is hidden inside `fleet.iterate_increments(reverse=True)`, so the code
  iterates over the objects themselves
- Frequently used attributes are hoisted into short local names of roughly equal
  length: `age`, `span`, `mult`. This shortens the code below, and a reader easily sees
  that, for example, `age` is `increment.age`
- Names are short but still descriptive: `dt` (known mathematical notation) instead of
  `time_step`, and `frequency` instead of `retrofit_frequency`

#### Ugly but correct

```python
for v, vessel_from in enumerate(fleet.vessels):
    source = _extract_conversion_source(fleet, vessel_from, idx)
    if source is None:
        continue

    increments = fleet.increments[v]
    for increment_idx in reversed(range(len(increments))):
        increment = increments[increment_idx]

        if not is_retrofit_cycle(
            increment.age, retrofit_frequency, time_step_years
        ):
            continue

        avg_age = round(increment.age + increment.age_span / 2.0, ROUND_OFF)
        if avg_age < minimum_age:
            continue

        remaining_lifetime_from = round(
            vessel_from.lifetime.get() - avg_age, ROUND_OFF
        )
        if remaining_lifetime_from <= 0.0:
            continue

        multiplier = increment.multiplier
        if multiplier <= 0:
            continue
```

What makes it bad:
- Indexing is mixed in with the mathematical logic. The reader has to track both the
  mathematical operations and the indexing and iteration logic
- The names and attribute accesses are so long that function calls wrap onto multiple
  lines

#### Preferred over a reasonable alternative

Missing examples.

#### Borderline

Missing examples.

## Simplify before you compute

### Quantities that cancel

#### Beautiful

```python
cost_per_unit = cost_reference / units_reference
cost_total = units * cost_per_unit
```

What makes it good:
- Only the quantities the result depends on appear, so the reader sees the dependency
  at a glance
- No division by the cancelled quantity can fail where the result is well defined

#### Ugly but correct

```python
cost_per_batch = cost_reference / batches_reference
units_per_batch = units_reference / batches_reference
cost_per_unit = cost_per_batch / units_per_batch

cost_total = units * cost_per_unit
```

What makes it bad:
- `batches_reference` cancels, yet the code tells the reader the cost depends on it
- Dividing by `batches_reference` fails for a reference with no batches, although the
  cost per unit is well defined

#### Preferred over a reasonable alternative

Missing examples.

#### Borderline

Missing examples.

<!--
SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
SPDX-License-Identifier: Apache-2.0
-->

# Examples

## Visual flow

### Blocks of steps

#### Beautiful

```python
def calculate_operational_profile(vessel, speeds):
    operations = Operations()
    operations.speeds = speeds

    _calculate_trip(operations, vessel)
    _calculate_cargo(operations, vessel)

    _calculate_energy_sea(operations, vessel)
    _calculate_energy_port(operations, vessel)

    return operations
```

What makes it good:
- Each vertical block is roughly the same length
- The lines within a block match in their parts, not only in length: both lines of the
  first block start with `operations`, and every line of the next two blocks is a call
  starting with `_calculate_`
- The first block is clearly some initial configuration. The calls after it are the
  calculation itself and `operations` only carries values between them, so they group
  by what they calculate: trip and cargo, then energy
- The method names are descriptive without being verbose

#### Ugly but correct

```python
def calculate_operational_profile(vessel, speeds):
    operations = Operations()

    operations.speeds = speeds
    _calculate_distances_times_and_voyages(operations, vessel)
    _calculate_cargo_miles_per_leg(operations, vessel)
    _calculate_energy_while_at_sea_per_leg(operations, vessel)
    _calculate_energy_in_port(operations, vessel)

    return operations
```

What makes it bad:
- The middle vertical block is jagged, making the eyes run horizontally to read the
  whole thing rather than just scanning vertically
- The vertical blocks are not clearly separated. `speeds` is assigned to operations at
  the same point as methods are called. It is not clear whether those methods may need
  `speeds` or not
- `operations.speeds = speeds` sits in a block of calls to internal methods, so it
  breaks the pattern twice: it is much shorter than the lines around it, and it does not
  start with `_calculate_` as every other line in the block does
- Names are overly descriptive, making it hard to choose variable/method names that
  match well in length. The exact definition of a method can be found in the method;
  the name does not need to include all information

#### Preferred over a reasonable alternative

Preferred:

```python
def complete_season(standings):
    _complete_points(standings)
    _complete_wins(standings)
    _complete_podiums(standings)
    _complete_fastest_laps(standings)

    standings.champion = _champion(standings)
```

Over:

```python
def complete_season(standings):
    _complete_points(standings)

    _complete_wins(standings)
    _complete_podiums(standings)

    _complete_fastest_laps(standings)
    standings.champion = _champion(standings)
```

Why the first:
- The steps only record finished results into the standings; recording is their
  purpose and binds them more than what each records, so they form one block
- Blocks by topic split one step into three, two of them a single line
- The assignment has a different shape from the calls, so it stands as its own block
  after them
- It can move there only because no call reads `champion`; a value a later call reads
  keeps its place in the column, written as a call of the same shape
- In the Beautiful example above the calls are the calculation itself and `operations`
  only carries values between them, so there they group by what they calculate

#### Borderline

Option 1:

```python
load_propulsion = vessel.propulsion_load.get(speeds)
load_electrical = vessel.electrical_load_at_sea.get(speeds)
load_heat = vessel.heat_load_at_sea.get(speeds)

energy_propulsion = _load_to_energy(load_propulsion, times)
energy_electrical = _load_to_energy(load_electrical, times)
energy_heat = _load_to_energy(load_heat, times)
```

Option 2:

```python
load_prop = vessel.prop_load.get(speeds)
load_elec = vessel.elec_load_at_sea.get(speeds)
load_heat = vessel.heat_load_at_sea.get(speeds)

energy_prop = _load_to_energy(load_prop, times)
energy_elec = _load_to_energy(load_elec, times)
energy_heat = _load_to_energy(load_heat, times)
```

Option 3:

```python
load_prop = vessel.propulsion_load.get(speeds)
load_elec = vessel.electrical_load_at_sea.get(speeds)
load_heat = vessel.heat_load_at_sea.get(speeds)

energy_prop = _load_to_energy(load_prop, times)
energy_elec = _load_to_energy(load_elec, times)
energy_heat = _load_to_energy(load_heat, times)
```

Trade-offs:
- In option 1 the vertical flow when scanning with the eyes is slightly more jagged, but
  the names are descriptive: `propulsion` instead of `prop`
- In option 2 the vertical flow is perfectly aligned, but the names `prop` and `elec`
  have to be inferred from the context of the file, since they are not standard
  convention names
- Option 3 keeps the externally facing names (`*_at_sea`, and `propulsion` for the
  class's methods) but aligns the components of the lines within the method better. It
  is a compromise between options 1 and 2
- A name the class exposes is read well beyond this one method, so it should stay
  descriptive, while a local name inside a single method used downstream of the class
  serves only that method, so it may be shortened for alignment. This tips the balance
  towards option 1 or 3 over option 2

### Comments in blocks

#### Beautiful

```python
def report_stage(race, route, result):
    # the baseline every finishing time on the stage is ranked against
    record = race.course_record

    # pace over the raced distance, neutral start and stoppages excluded
    distance = route.length - route.neutral_length
    duration = result.finish - result.start - result.stoppages
    pace = duration / distance

    return StageReport(record, pace)
```

What makes it good:
- The three lines that make up the pace form one block, so the reader sees the whole
  calculation at once, ending in the value it produces
- One comment heads the block and covers all of it; no comment interrupts it
- The record plays no part in the pace, so it stands apart as its own block with its own
  comment
- Each comment fits on one line, which is all a short description needs

#### Ugly but correct

```python
def report_stage(race, route, result):
    distance = route.length - route.neutral_length
    # the baseline every finishing time on the stage is
    # ranked against
    record = race.course_record
    # time on the clock, stoppages excluded
    duration = result.finish - result.start - result.stoppages

    pace = duration / distance

    return StageReport(record, pace)
```

What makes it bad:
- The block reads code, comment, code, comment, code, so the eye cannot scan it straight
  down
- The record sits between the two inputs of the pace, splitting a calculation with a
  value that plays no part in it
- A blank line cuts the pace off from its inputs, so the block that holds them ends
  before the step they serve
- A short description wraps over two lines and reads as a paragraph wedged into the code

#### Preferred over a reasonable alternative

Preferred:

```python
# pace over the raced distance, neutral start and stoppages excluded
distance = route.length - route.neutral_length
duration = result.finish - result.start - result.stoppages
pace = duration / distance
```

Over:

```python
# distance raced, the neutral start excluded
distance = route.length - route.neutral_length

# time on the clock, stoppages excluded
duration = result.finish - result.start - result.stoppages

pace = duration / distance
```

Why the first:
- The three lines are one calculation; a commented block per input makes the reader
  assemble the pace from three blocks
- One comment says what both inputs exclude as well as two comments do
- A commented block per line stays right where the lines are independent, as with the
  record above

#### Borderline

Missing examples.

### Length of line components

#### Beautiful

```python
var1 = [x]
var2 = [y]
var3 = [z]

var1.append(a)
var2.append(b)
var3.append(c)
```

What makes it good:
- All lines in a group are close to equal in length, which makes them easy for the eyes
  to scan vertically
- Each kind of operation gets its own vertical group
- The individual components of the lines are equal in length too, not just the whole
  lines: before and after `=` in the first group, and before and after `.` in the
  second

#### Ugly but correct

```python
var1 = [x]
var1.append(a)
variable2 = [y]
variable2.append(b)
v3 = [z]
v3.append(c)
```

What makes it bad:
- The lines in the single vertical group are jagged, which makes them hard for the eyes
  to scan vertically
- The vertical group is not split by task. It does two things
- The individual components of the lines are jagged. That makes it hard to scan and to
  see what kind of operation is happening: assignment, in-place change, and so on

#### Preferred over a reasonable alternative

Missing examples.

#### Borderline

Missing examples.

### Lines that wrap

#### Beautiful

```python
def record_month(account, summary, month):
    statement = account.statement

    statement.set_opening_balance(month, summary.opening_balance)
    statement.set_closing_balance(month, summary.closing_balance)
    statement.set_interest(month, summary.interest)

    statement.fees[month] = {
        FeeKind.WITHDRAWAL: summary.withdrawal_fees_charged,
        FeeKind.TRANSFER: summary.transfer_fees_charged,
    }
```

What makes it good:
- One local for the receiver keeps every call on one line and aligned
- The shortened names are the class's own names, chosen without the qualifiers the
  context supplies: descriptive, not exhaustive
- The fees are written as one literal with every key, so the month's record is replaced
  as a whole
- A literal laid out one entry per line is a table, not a wrap

#### Ugly but correct

```python
def record_monthly_account_summary(account, summary, month):
    account.monthly_statement.set_opening_balance(month, summary.opening_balance)
    account.monthly_statement.set_closing_balance(month, summary.closing_balance)
    account.monthly_statement.set_interest_earned_on_deposits(
        month, summary.interest_earned_on_deposits
    )

    account.monthly_statement.fees[month] = {}
    account.monthly_statement.fees[month][FeeKind.WITHDRAWAL] = (
        summary.withdrawal_fees_charged
    )
    account.monthly_statement.fees[month][FeeKind.TRANSFER] = (
        summary.transfer_fees_charged
    )
```

What makes it bad:
- The wraps come from the names, not from what the lines do
- `monthly` and `earned_on_deposits` repeat what the context already says, and the
  receiver is spelled out on every line
- Per-key assignment into an empty record hides that the fees are one record
- Abbreviating `statement` to `st` or aliasing `FeeKind.WITHDRAWAL` at module level
  would also stop the wraps, but the reader must then look the alias up

#### Preferred over a reasonable alternative

Missing examples.

#### Borderline

Missing examples.

### Pass-through loops

#### Beautiful

```python
def record_day(log, readings, day):
    for key, value in readings.air_temperatures_by_height.items():
        log.set_air_temperature(day, key, value)

    for key, value in readings.mean_wind_speeds_by_height.items():
        log.set_mean_wind_speed(day, key, value)

    for key, value in readings.rainfall_totals_by_gauge.items():
        if value is not None:
            log.set_rainfall_total(day, key, value)
```

What makes it good:
- The mapping says what its entries are and the setter says where they go, so
  `key, value` loses nothing the reader needs
- Every loop has the same header and the same body, so the reader sees at once that the
  three do the same thing and reads only the mapping and the setter
- Every header fits on one line, and the calls align as `log.set_*(day, key, value)`
- The guard reads as plainly with `value`: the mapping already says it is a rainfall
  total

#### Ugly but correct

```python
def record_day(log, readings, day):
    for (
        thermometer_height,
        air_temperature,
    ) in readings.air_temperatures_by_height.items():
        log.set_air_temperature(day, thermometer_height, air_temperature)

    for (
        anemometer_height,
        mean_wind_speed,
    ) in readings.mean_wind_speeds_by_height.items():
        log.set_mean_wind_speed(day, anemometer_height, mean_wind_speed)

    for rain_gauge, rainfall_total in readings.rainfall_totals_by_gauge.items():
        if rainfall_total is not None:
            log.set_rainfall_total(day, rain_gauge, rainfall_total)
```

What makes it bad:
- The loop names repeat what the mapping and the setter already say: `height` repeats
  `by_height`, and `air_temperature` repeats `air_temperatures` and
  `set_air_temperature`
- The repetition pushes two headers past 88 columns, so each spans four lines to drive
  a body of one
- The third header fits, so the three loops that do the same thing take two shapes
- Each loop has its own pair of names, which the reader must read again in every loop
  to learn that nothing differs but the mapping and the setter

#### Preferred over a reasonable alternative

Preferred:

```python
for sensor, pressure in readings.pressures_by_sensor.items():
    drift = drift_rates[sensor] * days_since_calibration
    corrected = pressure - drift
    log.set_pressure(day, sensor, corrected)
```

Over:

```python
for key, value in readings.pressures_by_sensor.items():
    drift = drift_rates[key] * days_since_calibration
    corrected = value - drift
    log.set_pressure(day, key, corrected)
```

Why the first:
- The loop calculates with its entries, so it no longer only passes them on
- `drift_rates[sensor]` says the rate is the sensor's own, where `drift_rates[key]`
  sends the reader back to the header to learn what the key is
- `pressure - drift` says what is corrected, where `value - drift` does not

#### Borderline

Missing examples.

### Arguments bound before the call

#### Beautiful

```python
def record_summary(log, readings, day):
    high = max(readings.hourly_temperatures)
    low = min(readings.hourly_temperatures)
    rainfall = sum(readings.hourly_rainfall)
    pressure = mean(readings.hourly_pressures) / PASCALS_PER_HECTOPASCAL

    log.set_daily_high(day, high)
    log.set_daily_low(day, low)
    log.set_rainfall_total(day, rainfall)
    log.set_mean_pressure(day, pressure)
```

What makes it good:
- The computed values form one block and the calls another, so the eye reads down what
  is computed and then down where it goes
- Every call takes only names, so no call wraps and all four share one shape
- The unit conversion sits with the other computations, not inside an argument list

#### Ugly but correct

```python
def record_summary(log, readings, day):
    log.set_daily_high(day, max(readings.hourly_temperatures))
    log.set_daily_low(day, min(readings.hourly_temperatures))
    log.set_rainfall_total(day, sum(readings.hourly_rainfall))
    log.set_mean_pressure(
        day, mean(readings.hourly_pressures) / PASCALS_PER_HECTOPASCAL
    )
```

What makes it bad:
- Every call both computes a value and passes it on, so the reader parses an expression
  inside each argument list
- The call with the longest expression wraps, so a column of four similar calls takes
  two shapes

#### Preferred over a reasonable alternative

Missing examples.

#### Borderline

Missing examples.

### Comprehensions

#### Beautiful

```python
thresholds = {}

for sensor in station.sensors:
    limit = limits[(station.region, sensor)]
    thresholds[sensor] = limit.upper * safety_margin
```

What makes it good:
- The loop is read first, so the reader knows what drives each entry before reading it
- Each line is one step: look up the limit, then scale it
- The lines of the body are similar in length and each starts with what it sets
- The lookup with its compound key gets a name, `limit`
- It costs nothing measurable, since the work per key dominates either way

#### Ugly but correct

```python
thresholds = {
    sensor: limits[(station.region, sensor)].upper * safety_margin
    for sensor in station.sensors
}
```

What makes it bad:
- The element comes before the loop, so the reader holds it without knowing what
  drives it
- The lines are jagged, so the eye scans across instead of down
- The element collects the lookup, its compound key and the arithmetic in one expression
- Where the target needs a type annotation, the first line packs in more still
- Spanning lines is not the fault in itself: a literal laid out one entry per line is
  a table the eye reads straight down, while a comprehension's single entry sits
  above the loop that repeats it

#### Preferred over a reasonable alternative

Preferred:

```python
totals = {}

for region, orders in orders_by_region.items():
    paid = [order for order in orders if order.paid]
    totals[region] = sum(order.amount for order in paid)
```

Over:

```python
totals = {
    region: sum(order.amount for order in orders if order.paid)
    for region, orders in orders_by_region.items()
}
```

Why the first:
- The comprehension nests two steps, filtering and summing, in one expression spread
  over several lines
- The loop gives each step its own line and names the intermediate
- A comprehension that fits on one line and does one thing stays preferred over a loop

#### Borderline

Option 1:

```python
offsets = {s: calibrations[s].zero_offset for s in station.active_sensors}
```

Option 2:

```python
offsets = {}

for sensor in station.active_sensors:
    offsets[sensor] = calibrations[sensor].zero_offset
```

Trade-offs:
- Option 1 is one line doing one step, which favours the comprehension
- Option 1 fits on the line only because `sensor` became `s`; with the full name it
  wraps. A name shortened only to make a line fit is the abbreviation principle 1 warns
  about, which favours the loop
- A name that lives within one line is traced at a glance, which weakens that cost

## Local comprehensibility

Missing examples.

## Clarity of intent

### Branching on a concept

#### Beautiful

```python
if item.kind == MediaKind.PODCAST:
    _queue_episode(item)

elif item.kind == MediaKind.FILM:
    _queue_screening(item)
```

What makes it good:
- The condition names the concept the reader already has in mind, the kind of item, so
  each branch reads as a statement about it

#### Ugly but correct

```python
if item.episode_number is not None:
    _queue_episode(item)

elif item.runtime is not None:
    # only films have a runtime, as validation enforces
    _queue_screening(item)
```

What makes it bad:
- The reader must know which kind of item sets which field, where branching on the
  concept they already know, the kind, says it directly
- The comment defends the test by restating a guarantee enforced elsewhere
- Where a type checker needs a field narrowed, narrow it inside the branch and keep the
  condition on the concept

#### Preferred over a reasonable alternative

Missing examples.

#### Borderline

Missing examples.

## Structural consistency

Missing examples.

## Information density

### Values nobody reads

#### Beautiful

```python
@dataclass(init=False)
class FitResult:
    coefficients: list
    residuals: list
    iterations: int
    converged: bool
```

What makes it good:
- Every field is one the fitting routine assigns and a caller reads; a field left
  unassigned fails when read instead of yielding a placeholder

#### Ugly but correct

```python
@dataclass
class FitResult:
    coefficients: list = field(default_factory=list)
    residuals: list = field(default_factory=list)
    iterations: int = 0
    converged: bool = False
    elapsed: float = 0.0
```

What makes it bad:
- The fitting routine assigns every field, so the defaults are never used, yet they tell
  the reader a missing value is fine
- `elapsed` is never read, and a field nothing reads sends the reader looking for its
  use

#### Preferred over a reasonable alternative

Missing examples.

#### Borderline

Missing examples.

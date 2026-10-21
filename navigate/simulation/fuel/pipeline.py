# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Plants moving through the pipeline: delivery, and planning from the supply gap."""

from __future__ import annotations

from math import ceil
from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import UtilityID
from navigate.core.increment import PlantIncrement
from navigate.simulation.cohort import (
    calculate_share_below,
    extends_past,
    find_insertion_index,
)
from navigate.simulation.economics.decision import calculate_two_axis_uptake
from navigate.simulation.economics.metric import calculate_age_levelized_cost
from navigate.simulation.fuel.feed import calculate_constrained_uptakes
from navigate.util import YEAR, calculate_inertia, divide_nonzero

if TYPE_CHECKING:
    from navigate.core.nodes.plant import Plant
    from navigate.core.nodes.producer import Producer
    from navigate.core.types_ import ForecastInput
    from navigate.util.types_ import FloatArray, FloatLike


def perform_pipeline_delivery(producer: Producer) -> None:
    """
    Deliver plants from the pipeline that have passed their lead time.

    Pipeline increments use negative ages (time since delivery, negative = not yet
    delivered). After aging with += dt, delivered increments have age >= 0 and
    transfer directly to active production without sign-flipping.

    Parameters
    ----------
    producer
        The producer instance.
    """
    for p in range(len(producer.plants)):
        pinc = producer.pipeline[p]
        incs = producer.increments[p]
        last_idx = None

        for i in range(len(pinc)):
            pinc_i = pinc[i]
            increment = pinc_i.multiplier

            if pinc_i.age >= 0.0:
                # fully delivered: the age already counts the time since delivery
                incs.append(
                    PlantIncrement(
                        increment, pinc_i.age, pinc_i.age_span, decided=pinc_i.decided
                    )
                )

                last_idx = i

            else:
                # the ongoing increment delivers the part that has crossed zero, as
                # plants enter uniformly over a time step
                if extends_past(pinc_i, 0.0):
                    alpha = calculate_share_below(pinc_i, 0.0)
                    remaining = increment * alpha
                    delivered = increment - remaining
                    delivered_dt = pinc_i.age + pinc_i.age_span

                    # the delivered portion keeps the original 'decided', so its
                    # origin index stays that of the original increment
                    incs.append(
                        PlantIncrement(
                            delivered, 0.0, delivered_dt, decided=pinc_i.decided
                        )
                    )

                    # shrink the pipeline portion and truncate its age span, to keep
                    # the plants entering uniformly
                    pinc_i.multiplier = remaining
                    pinc_i.age_span = -pinc_i.age

        if last_idx is not None:
            producer.pipeline[p] = pinc[(last_idx + 1) :]


def perform_pipeline_planning(
    producer: Producer, timeline: FloatArray, time_step: float, idx: int
) -> None:
    """
    Plan new plant additions to the pipeline based on supply/demand gap.

    Parameters
    ----------
    producer
        The producer to plan for.
    timeline
        Simulation timeline, days.
    time_step
        Current time-step size, days.
    idx
        Current time-step index.
    """
    inertia_increments = calculate_inertia_increments(producer, time_step, idx)

    # the production just added through inertia already covers part of the
    # supply/demand gap. get_fair_share_demand returns the stored arrays, so the
    # dict is copied here and subtraction stays out of place, leaving the stored
    # demand untouched
    demand = dict(producer.expectation.get_fair_share_demand())

    for p, plant in enumerate(producer.plants):
        production = plant.expectation.get_production(idx) * inertia_increments[p]
        fuel_name = plant.fuel.name
        demand[fuel_name] = demand[fuel_name] - production

    export_distribution = producer.expectation.get_export_distribution(idx=idx)

    # the inter metric also checks that there is sufficient future offtake to
    # merit building plants
    for plant in producer.plants:
        _calculate_uptake_inter_metric(
            plant, demand, producer.minimum_offtake_duration, timeline, idx
        )
        _calculate_uptake_intra_metric(plant, export_distribution, idx)

    demand_multipliers = np.array(
        [
            plant.expectation.get_demand_newbuilds()
            if producer.allow_plant[plant.name]
            else 0.0
            for plant in producer.plants
        ]
    )

    model_increments = np.zeros_like(inertia_increments)
    maximum_development = producer.maximum_development.get() * time_step / YEAR

    ramp_up = producer.maximum_ramp_up.get()
    maximum_increase = min(producer.current_utilization + ramp_up, 1.0)
    maximum_development *= maximum_increase

    # the inertia-based increments already count against the development limit
    maximum_development -= np.sum(inertia_increments)

    if maximum_development > 0.0:
        modelled_uptakes = calculate_modelled_uptake(producer)
        demand_limits = np.array(
            [
                min(multiplier / maximum_development, 1.0)
                for multiplier in demand_multipliers
            ]
        )
        constrained_uptakes = calculate_constrained_uptakes(
            producer, modelled_uptakes, maximum_development, demand_limits, idx
        )
        model_increments = maximum_development * constrained_uptakes

    increments = np.add(inertia_increments, model_increments)

    # the utilization carries into the next time step's ramp-up constraint
    producer.current_utilization = float(
        divide_nonzero(
            np.sum(increments), producer.maximum_development.get() * time_step / YEAR
        )
    )

    dt = time_step / YEAR

    for p, plant in enumerate(producer.plants):
        if increments[p] == 0.0:
            continue

        lead_time = plant.lead_time.get()
        pinc = producer.pipeline[p]
        new_age = -lead_time
        i = find_insertion_index(pinc, new_age)

        pinc.insert(i, PlantIncrement(increments[p], new_age, dt, decided=0.0))

    total_increments = np.sum(increments)
    producer.results.development[idx] = total_increments

    producer.current_uptake = divide_nonzero(
        increments, total_increments, default=1.0 / increments.size
    )


def calculate_inertia_increments(
    producer: Producer, time_step: float, idx: int
) -> FloatArray:
    """
    Calculate the increments being built due to inertia from previous uptake.

    Parameters
    ----------
    producer
        The producer.
    time_step
        Current time-step size, days.
    idx
        Current time-step index.

    Returns
    -------
    FloatArray
        Inertia-based increments per plant type, number of plants.
    """
    # the uptake shares decay by the inertia here, before the inertia-related
    # newbuilds, so the decay happens at every time step
    producer.current_uptake *= calculate_inertia(producer.inertia.get(), time_step)

    for p, plant in enumerate(producer.plants):
        if not producer.allow_plant[plant.name]:
            producer.current_uptake[p] = 0.0

    # inertia only happens if the producer is development constrained
    increments = np.zeros((len(producer.plants),))

    # the current utilization is the previous time step's, as this step's
    # planning has not run yet
    maximum_development = (
        producer.current_utilization
        * producer.maximum_development.get()
        * time_step
        / YEAR
    )

    if maximum_development > 0.0:
        demand_multipliers = np.array(
            [
                plant.expectation.get_demand_newbuilds()
                if producer.allow_plant[plant.name]
                else 0.0
                for plant in producer.plants
            ]
        )
        demand_limits = np.array(
            [
                min(multiplier / maximum_development, 1.0)
                for multiplier in demand_multipliers
            ]
        )

        uptake = producer.current_uptake
        constrained_uptake = calculate_constrained_uptakes(
            producer, uptake, maximum_development, demand_limits, idx
        )
        increments = constrained_uptake * maximum_development

        for feed_name, constraint in producer.feed_constraints.items():
            if constraint is None:
                continue

            added_consumption = 0.0

            for p, plant in enumerate(producer.plants):
                consumption = producer.expectation.get_plant_feed_consumption(
                    plant.name, feed_name
                )
                added_consumption += consumption * increments[p]

            original_gap = producer.expectation.get_feed_gap(feed_name, idx)
            new_gap = original_gap - added_consumption
            producer.expectation.set_feed_gap(idx, feed_name, new_gap)

    return increments


def _calculate_uptake_inter_metric(
    plant: Plant,
    demand: dict[str, FloatArray],
    minimum_offtake_duration: ForecastInput,
    timeline: FloatArray,
    idx: int,
) -> None:
    """
    Calculate the business-case metric used to choose a fuel pathway.

    This is based on the expected future gap between supply and demand and the number of
    plants required to satisfy that gap.

    Parameters
    ----------
    plant
        Plant for which inter uptake metric is being calculated.
    demand
        The expected demand per fuel pathway that is not satisfied by current supply,
        tons/year.
    minimum_offtake_duration
        The minimum duration of offtake to justify building a plant, years.
    timeline
        Simulation timeline, days.
    idx
        Current time-step index.
    """
    expectation = plant.expectation

    # the plant's discount rate discounts the future multipliers: dwindling
    # demand is worth less than immediate demand, since the production can be
    # sold to other industries later on
    discount_rate = plant.cost_of_capital.get()

    evaluation_timeline = _get_plant_evaluation_timeline(plant, timeline, idx)
    production = expectation.get_production(idx)

    fuel = plant.fuel
    lhv = fuel.lower_heating_value.get()

    # the fair-share demand is re-sampled onto the plant's business cash-flow
    # horizon, its operating years after the lead time
    demand_int = np.interp(evaluation_timeline, timeline, demand[fuel.name], left=0.0)
    demand_multipliers = demand_int / production

    lifetime = plant.lifetime.get()
    minimum_duration = minimum_offtake_duration.get()

    # the lowest equivalent multiplier within the sufficient offtake duration is
    # the most plants it makes sense to sanction
    to_ = min(ceil(minimum_duration), ceil(lifetime), demand_int.size)
    demand_newbuilds = max(np.amin(demand_multipliers[:to_]), 0)

    demand_energy = demand_int * lhv
    metric = calculate_age_levelized_cost(demand_energy, lifetime, discount_rate)

    expectation.set_demand_newbuilds(demand_newbuilds)
    expectation.set_inter_fuel_metric(metric)


def _get_plant_evaluation_timeline(
    plant: Plant, timeline: FloatArray, idx: int
) -> FloatArray:
    """
    Build the timeline at which cash flows should be evaluated.

    Parameters
    ----------
    plant
        Plant for which evaluation timeline is built.
    timeline
        Simulation timeline, days.
    idx
        Current time-step index.

    Returns
    -------
    FloatArray
        Evaluation timeline, days.
    """
    lifetime = plant.lifetime.get()
    lead_time = plant.lead_time.get()

    evaluation_timeline: FloatArray = (
        np.arange(ceil(lead_time), ceil(lifetime + lead_time), dtype=np.float64) * YEAR
        + timeline[idx]
    )

    return evaluation_timeline


def _calculate_uptake_intra_metric(
    plant: Plant, export_distribution: dict[str, FloatLike], idx: int
) -> None:
    """
    Calculate the business-case metric used to choose a plant within a fuel pathway.

    This is based on the average delivered levelized cost of fuel for a given plant.

    Parameters
    ----------
    plant
        Plant for which intra uptake metric is being calculated.
    export_distribution
        Fraction of fuel production that is exported to each port at the time step.
    idx
        Current time-step index.
    """
    expectation = plant.expectation
    production_cost = expectation.get_levelized_production_cost(idx)
    metric = 0.0

    for port_name, export in export_distribution.items():
        delivery_cost = expectation.get_levelized_delivery_cost(port_name, idx)
        lcof = float(production_cost + delivery_cost)
        metric += float(export) * lcof

    expectation.set_intra_fuel_metric(metric)


def calculate_modelled_uptake(producer: Producer) -> FloatArray:
    """
    Calculate each plant type's relative uptake share.

    Uses a two-axis discrete choice model grouped by fuel pathway.

    Parameters
    ----------
    producer
        The producer.

    Returns
    -------
    FloatArray
        Uptake shares per plant type.
    """
    index: list[int] = []
    plants: list[Plant] = []

    for p, plant in enumerate(producer.plants):
        is_in_demand = plant.expectation.get_inter_fuel_metric() > 0.0

        if producer.allow_plant[plant.name] and is_in_demand:
            index.append(p)
            plants.append(plant)

    if not plants:
        return np.zeros((len(producer.plants),))

    group_keys = [plant.fuel.name for plant in plants]
    metrics_intra = [plant.expectation.get_intra_fuel_metric() for plant in plants]
    metrics_inter = [plant.expectation.get_inter_fuel_metric() for plant in plants]

    uptake = calculate_two_axis_uptake(
        group_keys=group_keys,
        metrics_intra=metrics_intra,
        metrics_inter=metrics_inter,
        intra_utility=UtilityID.LOWER_LOG_RATIO,
        inter_utility=UtilityID.HIGHER_LOG_RATIO,
        intra_odds=producer.fuel_cost_sensitivity.get(),
        inter_odds=producer.fuel_demand_sensitivity.get(),
        context=str(producer),
    )

    uptake_padded = np.zeros(len(producer.plants))

    for i, p in enumerate(index):
        uptake_padded[p] = uptake[i]

    return uptake_padded

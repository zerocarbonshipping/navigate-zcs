# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Per-step expectations of ports and producers over the remaining timeline."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.util import MWH_TO_GJ, divide_nonzero

if TYPE_CHECKING:
    from navigate.core.nodes.port import Port
    from navigate.core.nodes.producer import Producer
    from navigate.util.types_ import FloatArray


def calculate_port_expectations(
    ports: dict[str, Port], timeline: FloatArray, idx: int
) -> None:
    """
    Calculate each port's bunkering, handling, overwrite and shore-power expectations.

    Parameters
    ----------
    ports
        All ports in the simulation.
    timeline
        Simulation timeline, days.
    idx
        Current time-step index.
    """
    times = timeline[idx:]

    for port in ports.values():
        _calculate_port_expectation(port, times, idx)


def calculate_export_expectations(
    producers: dict[str, Producer], timeline: FloatArray, idx: int
) -> None:
    """
    Calculate each producer's expected export distribution over the ports.

    Parameters
    ----------
    producers
        All producers in the simulation.
    timeline
        Simulation timeline, days.
    idx
        Current time-step index.
    """
    times = timeline[idx:]

    for producer in producers.values():
        _calculate_export_expectation(producer, times, idx)


def _calculate_port_expectation(port: Port, times: FloatArray, idx: int) -> None:
    """Set the port's limits, costs, overwrites and shore-power terms."""
    expectation = port.expectation

    for key, value in port.bunkering_limit.items():
        if value is not None:
            expectation.set_bunkering_limit(idx, key, value.get(times))

    for key, value in port.handling_cost.items():
        expectation.set_handling_cost(idx, key, value.get(times))

    for key, value in port.bunker_price_overwrite.items():
        if value is not None:
            expectation.set_bunker_price_overwrite(idx, key, value.get(times))

    for key, value in port.bunker_wtt_overwrite.items():
        if value is not None:
            expectation.set_bunker_wtt_overwrite(idx, *key, value.get(times))

    # shore power (convert from USD/MWh to USD/GJ, and ton/MWh to ton/GJ)
    cost = port.shore_power_cost.get(times) / MWH_TO_GJ
    share = port.shore_power_connection_share.get(times)
    expectation.set_shore_power_cost(idx, cost)
    expectation.set_shore_power_connection_share(idx, share)

    for key, value in port.shore_power_emission_factor.items():
        factor = value.get(times) / MWH_TO_GJ
        expectation.set_shore_power_emission_factor(idx, key, factor)


def _calculate_export_expectation(
    producer: Producer, times: FloatArray, idx: int
) -> None:
    """Set the producer's expected export distribution."""
    if not producer.export_distribution:
        return

    exports: dict[str, FloatArray] = {}
    for key, value in producer.export_distribution.items():
        exports[key] = value.get(times)

    total = sum(exports.values())

    # at steps where the total is not positive, ports share exports equally
    default = 1.0 / len(exports)

    expectation = producer.expectation

    for port_name, export in exports.items():
        share = divide_nonzero(export, total, default=default)
        expectation.set_export_distribution(idx, port_name, share)

# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The allowances and spend coefficients each regulation gives the bunkering LP."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import RegulationMeasureID
from navigate.util import TON_TO_KG, unique_list

if TYPE_CHECKING:
    from navigate.core.nodes.regulation import Regulation
    from navigate.core.nodes.vessel import Vessel
    from navigate.util.types_ import FloatLike


def calculate_regulation_bunkering_inputs(
    regulations: dict[str, Regulation], vessels: dict[str, Vessel], idx: int
) -> None:
    """
    Calculate the inputs each active regulation gives the bunkering LP.

    Every vessel gets the spend coefficients its threshold constraints weigh, and
    every policed vessel its allowance, from the current time step on.

    Parameters
    ----------
    regulations
        All regulations in the simulation.
    vessels
        All vessels in the simulation.
    idx
        Current time-step index.
    """
    horizon = np.s_[idx:]

    for regulation in regulations.values():
        if not regulation.active:
            continue

        expectation = regulation.expectation

        for vessel_name, vessel in vessels.items():
            threshold = expectation.get_vessel_threshold(vessel_name, horizon)

            calculate_vessel_spend_coefficients(regulation, vessel, threshold, horizon)

            if regulation.vessel_is_policed(vessel_name):
                calculate_vessel_allowance(regulation, vessel_name, threshold, horizon)


def calculate_vessel_allowance(
    regulation: Regulation, vessel_name: str, threshold: FloatLike, idx: int | slice
) -> None:
    """
    Calculate a policed vessel's allowance under a regulation.

    The allowance, the threshold times the measure, is the right-hand side the vessel
    contributes to its threshold constraint in the bunkering LP. Under INTENSITY the
    measure is zero, and so is the allowance: the threshold enters the spend
    coefficients instead.

    Parameters
    ----------
    regulation
        Regulation policing the vessel.
    vessel_name
        Name of the vessel.
    threshold
        Threshold the vessel is held to at the steps of `idx`.
    idx
        Time-step index, or the slice of the steps, the allowance is written at.
    """
    expectation = regulation.expectation

    measure = expectation.get_vessel_measure(vessel_name, idx)
    expectation.set_vessel_allowance(idx, vessel_name, threshold * measure)


def calculate_vessel_spend_coefficients(
    regulation: Regulation, vessel: Vessel, threshold: FloatLike, idx: int | slice
) -> None:
    """
    Calculate the spend coefficients a regulation's bunkering constraints weigh.

    Under an INTENSITY measure, a spend coefficient is the emission coefficient net of
    the vessel's threshold, converted from kg emission/GJ by the effective LHV, so the
    constraint compares the weighted spend with zero; shore power is in GJ, so its
    effective LHV is 1. Under any other measure the threshold enters the right-hand
    side instead, and the spend coefficient is the emission coefficient. Every fuel a
    converter can burn gets one, as the constraints weigh all spend: an untargeted
    fuel, without an emission coefficient, nets out the threshold alone.

    Parameters
    ----------
    regulation
        Regulation whose constraints weigh the spend.
    vessel
        Vessel spending the fuel and shore power.
    threshold
        Threshold the spend is netted against at the steps of `idx`.
    idx
        Time-step index, or the slice of the steps, the coefficients are written at.
    """
    vessel_name = vessel.name
    expectation = regulation.expectation
    vessel_expectation = vessel.expectation
    is_intensity = regulation.measure == RegulationMeasureID.INTENSITY

    # in ton emission/GJ; zero where the threshold enters the right-hand side
    threshold_term = threshold / TON_TO_KG if is_intensity else 0.0

    for converter_name, burned in vessel.fuels_per_converter.items():
        for fuel_name in burned:
            fuel_key = (vessel_name, converter_name, fuel_name)
            lhv = vessel_expectation.get_effective_lhv(converter_name, fuel_name)
            emission = expectation.get_emission_coefficient(fuel_key, idx)

            spend = emission - threshold_term * lhv
            expectation.set_spend_coefficient(idx, fuel_key, spend)

    for port in unique_list(vessel.route.ports):
        port_key = (vessel_name, port.name)
        emission = expectation.get_shore_power_emission_coefficient(port.name, idx)

        spend = emission - threshold_term
        expectation.set_shore_power_spend_coefficient(idx, port_key, spend)

# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core import (
    Scalar,
    as_scalar,
    assign_id,
    assign_value,
    command_assignment_to_tuple_dict,
)
from navigate.core.assign import command_assignment_to_dict
from navigate.core.enum_ import EnergyDemandTypeID
from navigate.core.node_type import CURVE, TECHNOLOGY, VARIABLE
from navigate.core.nodes._machinery import _Machinery

if TYPE_CHECKING:
    from navigate.core.nodes.curve import Curve
    from navigate.core.nodes.input_kinds import CurveInput, ScalarInput
    from navigate.core.nodes.variable import Variable

PROPULSION, ELECTRICAL, HEAT = (
    EnergyDemandTypeID.PROPULSION,
    EnergyDemandTypeID.ELECTRICAL,
    EnergyDemandTypeID.HEAT,
)


class Technology(_Machinery):
    """
    Represent a technology installable on vessels.

    It is an energy-efficiency device, an alternative power source, or an
    emission-reduction measure.
    """

    def __init__(self, name: str) -> None:
        super().__init__(name, TECHNOLOGY)

        # external variables -----------------------------------------------------------
        self.shore_power_capacity: ScalarInput = Scalar(0.0)

        # energy efficiency
        self.energy_saving: dict[EnergyDemandTypeID, ScalarInput] = {
            d: Scalar(0.0) for d in EnergyDemandTypeID
        }
        self.external_power: dict[EnergyDemandTypeID, ScalarInput] = {
            d: Scalar(0.0) for d in EnergyDemandTypeID
        }

        # external power
        self.power_transfer: dict[
            tuple[EnergyDemandTypeID, EnergyDemandTypeID], CurveInput
        ] = {
            (src, dst): Scalar(0.0)
            for src in EnergyDemandTypeID
            for dst in EnergyDemandTypeID
        }

    # external methods (DSL attributes) ------------------------------------------------
    def set_shore_power_capacity(self, capacity):
        """
        Set the vessel-side shore power connection capacity in MW.

        Examples
        --------
        - 4.0
        - Forecast("name")

        Parameters
        ----------
        capacity : float | Node
            Vessel-side shore power connection rating in MW.
        """
        self.shore_power_capacity = assign_value(
            as_scalar(capacity), type_=VARIABLE, lower=0.0
        )

    # external methods (DSL commands) --------------------------------------------------
    def set_energy_saving(self, energy_type: str, saving):
        """
        Set the energy saving for the given energy demand type.

        Parameters
        ----------
        energy_type
            Energy demand type the saving applies to.
        saving
            Fraction of energy saved for that demand type.
        """
        id_ = assign_id(energy_type, EnergyDemandTypeID)
        command_assignment_to_dict(
            id_, saving, self.energy_saving, type_=VARIABLE, lower=0.0
        )

    def set_external_power(self, energy_type: str, power):
        """
        Set the external power for the given energy demand type.

        Parameters
        ----------
        energy_type
            Energy demand type the external power supplies.
        power
            External power supplied for that demand type, in MW.
        """
        id_ = assign_id(energy_type, EnergyDemandTypeID)
        command_assignment_to_dict(
            id_, power, self.external_power, type_=VARIABLE, lower=0.0
        )

    def set_power_transfer(
        self, power_system_id: str, energy_id: str, transfer: Variable | Curve
    ):

        power_system_id_ = assign_id(power_system_id, EnergyDemandTypeID)
        energy_id_ = assign_id(energy_id, EnergyDemandTypeID)

        command_assignment_to_tuple_dict(
            (power_system_id_, energy_id_),
            transfer,
            self.power_transfer,
            type_=(CURVE, VARIABLE),
            lower=0.0,
            upper=1.0,
        )

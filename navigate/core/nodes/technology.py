# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.core import Scalar, as_scalar, assign_id, assign_value, command_assignment_to_tuple_dict
from navigate.core.assign import command_assignment_to_dict
from navigate.core.enum_ import EnergyDemandTypeID
from navigate.core.node_type import CURVE, TECHNOLOGY, VARIABLE
from navigate.core.nodes._machinery import _Machinery
from navigate.core.nodes.curve import Curve
from navigate.core.nodes.variable import Variable

PROPULSION, ELECTRICAL, HEAT = EnergyDemandTypeID.PROPULSION, EnergyDemandTypeID.ELECTRICAL, EnergyDemandTypeID.HEAT


class Technology(_Machinery):
    """
    A technology installable on vessels: an energy-efficiency device, an
    alternative power source, or an emission-reduction measure.
    """
    def __init__(self, name):
        super().__init__(name)

        self.type = TECHNOLOGY

        self.shore_power_capacity: Scalar | None = None

        # energy efficiency
        self.energy_saving: dict[EnergyDemandTypeID, Scalar | None] = {
            energy: None for energy in EnergyDemandTypeID
        }
        self.external_power: dict[EnergyDemandTypeID, Scalar | None] = {
            e: None for e in EnergyDemandTypeID
        }

        # external power
        self.power_transfer: dict[tuple[EnergyDemandTypeID, EnergyDemandTypeID], Curve | Scalar | None] = {
            (src, dst): None
            for src in EnergyDemandTypeID
            for dst in EnergyDemandTypeID
        }

    # external attributes set through the input deck -------------------------------------------------------------------
    def set_shore_power_capacity(self, capacity):
        """
        Set the vessel-side shore power connection capacity in MW.

        Examples
        --------
        - 4.0
        - Forecast("name")

        Parameters
        ----------
        capacity : float | NodeReference
            Vessel-side shore power connection rating in MW.
        """

        self.shore_power_capacity = assign_value(as_scalar(capacity), type_=VARIABLE, lower=0.)

    # external commands set through the input deck ---------------------------------------------------------------------
    def set_energy_saving(self, energy_type: str, saving):
        """

        Parameters
        ----------
        energy_type
        saving

        Returns
        -------

        """
        id_ = assign_id(energy_type, EnergyDemandTypeID)
        command_assignment_to_dict(id_, saving, self.energy_saving, type_=VARIABLE, lower=0.)

    def set_external_power(self, energy_type: str, power):
        """

        Parameters
        ----------
        energy_type
        power

        Returns
        -------

        """
        id_ = assign_id(energy_type, EnergyDemandTypeID)
        command_assignment_to_dict(id_, power, self.external_power, type_=VARIABLE, lower=0.)

    def set_power_transfer(self,
                           power_system_id: str,
                           energy_id: str,
                           transfer: Variable | Curve):

        power_system_id_ = assign_id(power_system_id, EnergyDemandTypeID)
        energy_id_ = assign_id(energy_id, EnergyDemandTypeID)

        command_assignment_to_tuple_dict((power_system_id_, energy_id_),
                                         transfer,
                                         self.power_transfer,
                                         type_=(CURVE, VARIABLE),
                                         lower=0., upper=1.)

    # internal methods -------------------------------------------------------------------------------------------------
    def initialize(self):
        if self.shore_power_capacity is None:
            self.shore_power_capacity = Scalar(0.)

        for energy_id in EnergyDemandTypeID:
            if self.energy_saving[energy_id] is None:
                self.energy_saving[energy_id] = Scalar(0)

            if self.external_power[energy_id] is None:
                self.external_power[energy_id] = Scalar(0)

            for power_system_id in EnergyDemandTypeID:
                if self.power_transfer[(power_system_id, energy_id)] is None:
                    self.power_transfer[(power_system_id, energy_id)] = Scalar(0)

        self._initialize_machinery()

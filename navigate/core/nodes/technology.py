# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Technology node, a device or measure installable on a vessel."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core import (
    Scalar,
    as_scalar,
    assign_id,
    assign_value,
    write_matching_key_pairs,
    write_matching_keys,
)
from navigate.core.enum_ import EnergyDemandTypeID
from navigate.core.node_type import CURVE, TECHNOLOGY, VARIABLE
from navigate.core.nodes._machinery import _Machinery

if TYPE_CHECKING:
    from navigate.core.types_ import (
        CurveArgument,
        CurveInput,
        ScalarArgument,
        ScalarInput,
    )

PROPULSION, ELECTRICAL, HEAT = (
    EnergyDemandTypeID.PROPULSION,
    EnergyDemandTypeID.ELECTRICAL,
    EnergyDemandTypeID.HEAT,
)


class Technology(_Machinery):
    """An energy saving, external power or power transfer installable on a vessel."""

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
    def set_shore_power_capacity(self, capacity: ScalarArgument) -> None:
        """
        Set the vessel-side shore power connection capacity in MW.

        A vessel's shore power use in a port is capped at the combined capacity of its
        technologies over its time in port, or at the port's shore power connection
        share of its electrical demand in port if that is lower.

        Examples
        --------
        - 4.0
        - Variable("name")

        Parameters
        ----------
        capacity
            Vessel-side shore power connection rating in MW.
        """
        self.shore_power_capacity = assign_value(
            as_scalar(capacity), type_=VARIABLE, lower=0.0
        )

    # external methods (DSL commands) --------------------------------------------------
    def set_energy_saving(self, energy_type: str, saving: ScalarArgument) -> None:
        """
        Set the fraction of the raw energy demand the technology saves.

        The saving scales the raw demand of the energy type before any external power
        is subtracted: the residual energy is raw * (1 - saving) - external, floored at
        zero. The savings of the technologies in one package compound as
        1 - prod(1 - saving).

        Examples
        --------
        - PROPULSION, 0.04
        - HEAT, Variable("name")

        Parameters
        ----------
        energy_type
            Energy demand type the saving applies to.
        saving
            Fraction of the raw energy demand saved.
        """
        value_ = assign_value(as_scalar(saving), type_=VARIABLE, lower=0.0)

        id_ = assign_id(energy_type, EnergyDemandTypeID)
        write_matching_keys(id_, value_, self.energy_saving)

    def set_external_power(self, energy_type: str, power: ScalarArgument) -> None:
        """
        Set the external power the technology supplies to an energy demand type, in MW.

        The power is converted to energy over the duration of each leg or port stay and
        subtracted from the demand left after the energy savings, floored at zero. The
        external powers of the technologies in one package add up.

        Examples
        --------
        - PROPULSION, 1.25
        - HEAT, Variable("name")

        Parameters
        ----------
        energy_type
            Energy demand type the external power supplies.
        power
            External power supplied, in MW.
        """
        value_ = assign_value(as_scalar(power), type_=VARIABLE, lower=0.0)

        id_ = assign_id(energy_type, EnergyDemandTypeID)
        write_matching_keys(id_, value_, self.external_power)

    def set_power_transfer(
        self, power_system_id: str, energy_id: str, transfer: CurveArgument
    ) -> None:
        """
        Set the power transferred from a source energy type to a sink energy type.

        The transfer is evaluated at the load of the source converter: the residual
        power of the source energy type divided by that converter's power capacity. A
        Curve therefore maps the load (-) to the transferred power (MW); a number is a
        constant power. The power is converted to energy over the duration of each leg
        or port stay and subtracted from the residual demand of the sink energy type,
        floored at zero.

        Examples
        --------
        - PROPULSION, ELECTRICAL, Curve("name")
        - PROPULSION, ELECTRICAL, 0.5

        Parameters
        ----------
        power_system_id
            Energy demand type whose converter supplies the transferred power.
        energy_id
            Energy demand type receiving the transferred power.
        transfer
            Power transferred, in MW, as a function of the source converter load.
        """
        value_ = assign_value(
            as_scalar(transfer), type_=(CURVE, VARIABLE), lower=0.0, upper=1.0
        )

        power_system_id_ = assign_id(power_system_id, EnergyDemandTypeID)
        energy_id_ = assign_id(energy_id, EnergyDemandTypeID)

        write_matching_key_pairs(
            (power_system_id_, energy_id_), value_, self.power_transfer
        )

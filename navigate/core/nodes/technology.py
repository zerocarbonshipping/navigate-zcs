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
from navigate.core.enum_ import EnergyDemandID
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
    EnergyDemandID.PROPULSION,
    EnergyDemandID.ELECTRICAL,
    EnergyDemandID.HEAT,
)


class Technology(_Machinery):
    """An energy saving, external power or power transfer installable on a vessel."""

    def __init__(self, name: str) -> None:
        super().__init__(name, TECHNOLOGY)

        # external variables -----------------------------------------------------------
        self.shore_power_capacity: ScalarInput = Scalar(0.0)

        # energy efficiency
        self.energy_saving: dict[EnergyDemandID, ScalarInput] = {
            d: Scalar(0.0) for d in EnergyDemandID
        }
        self.external_power: dict[EnergyDemandID, ScalarInput] = {
            d: Scalar(0.0) for d in EnergyDemandID
        }

        # external power
        self.power_transfer: dict[tuple[EnergyDemandID, EnergyDemandID], CurveInput] = {
            (src, dst): Scalar(0.0) for src in EnergyDemandID for dst in EnergyDemandID
        }

    # external methods (DSL attributes) ------------------------------------------------
    def set_shore_power_capacity(self, capacity: ScalarArgument) -> None:
        """Set the vessel-side shore power connection capacity."""
        self.shore_power_capacity = assign_value(
            as_scalar(capacity), type_=VARIABLE, lower=0.0
        )

    # external methods (DSL commands) --------------------------------------------------
    def set_energy_saving(self, energy_type: str, saving: ScalarArgument) -> None:
        """Set the fraction of the raw energy demand the technology saves."""
        value_ = assign_value(as_scalar(saving), type_=VARIABLE, lower=0.0)

        id_ = assign_id(energy_type, EnergyDemandID)
        write_matching_keys(id_, value_, self.energy_saving)

    def set_external_power(self, energy_type: str, power: ScalarArgument) -> None:
        """Set the external power the technology supplies to an energy demand type."""
        value_ = assign_value(as_scalar(power), type_=VARIABLE, lower=0.0)

        id_ = assign_id(energy_type, EnergyDemandID)
        write_matching_keys(id_, value_, self.external_power)

    def set_power_transfer(
        self, power_system_id: str, energy_id: str, transfer: CurveArgument
    ) -> None:
        """Set the power transferred from a source energy type to a sink energy type."""
        value_ = assign_value(as_scalar(transfer), type_=(CURVE, VARIABLE), lower=0.0)

        power_system_id_ = assign_id(power_system_id, EnergyDemandID)
        energy_id_ = assign_id(energy_id, EnergyDemandID)

        write_matching_key_pairs(
            (power_system_id_, energy_id_), value_, self.power_transfer
        )

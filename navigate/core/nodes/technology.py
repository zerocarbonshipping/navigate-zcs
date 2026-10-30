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
    deck_attribute,
    deck_command,
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


class Technology(_Machinery):
    """An energy saving, external power or power transfer installable on a vessel."""

    type = TECHNOLOGY

    def __init__(self, name: str) -> None:
        super().__init__(name)

        # external variables -----------------------------------------------------------
        self.shore_power_capacity: ScalarInput = Scalar(0.0)

        self.energy_savings: dict[EnergyDemandID, ScalarInput] = {
            demand: Scalar(0.0) for demand in EnergyDemandID
        }
        self.external_power: dict[EnergyDemandID, ScalarInput] = {
            demand: Scalar(0.0) for demand in EnergyDemandID
        }

        self.power_transfers: dict[
            tuple[EnergyDemandID, EnergyDemandID], CurveInput
        ] = {
            (source, sink): Scalar(0.0)
            for source in EnergyDemandID
            for sink in EnergyDemandID
        }

    # external methods (DSL attributes) ------------------------------------------------
    @deck_attribute()
    def set_shore_power_capacity(self, value: ScalarArgument) -> None:
        """Set the vessel-side shore power connection capacity."""
        self.shore_power_capacity = assign_value(
            as_scalar(value), type_=VARIABLE, lower=0.0
        )

    # external methods (DSL commands) --------------------------------------------------
    @deck_command()
    def set_energy_saving(self, key: str, value: ScalarArgument) -> None:
        """Set the fraction of the raw energy demand the technology saves."""
        energy_type = assign_id(key, EnergyDemandID)
        saving = assign_value(as_scalar(value), type_=VARIABLE, lower=0.0)

        write_matching_keys(energy_type, saving, self.energy_savings)

    @deck_command()
    def set_external_power(self, key: str, value: ScalarArgument) -> None:
        """Set the external power the technology supplies to an energy demand type."""
        energy_type = assign_id(key, EnergyDemandID)
        power = assign_value(as_scalar(value), type_=VARIABLE, lower=0.0)

        write_matching_keys(energy_type, power, self.external_power)

    @deck_command()
    def set_power_transfer(self, key1: str, key2: str, value: CurveArgument) -> None:
        """Set the power transferred from a source energy type to a sink energy type."""
        source = assign_id(key1, EnergyDemandID)
        sink = assign_id(key2, EnergyDemandID)
        transfer = assign_value(as_scalar(value), type_=(CURVE, VARIABLE), lower=0.0)

        write_matching_key_pairs((source, sink), transfer, self.power_transfers)

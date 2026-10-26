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

        self.energy_saving: dict[EnergyDemandID, ScalarInput] = {
            demand: Scalar(0.0) for demand in EnergyDemandID
        }
        self.external_power: dict[EnergyDemandID, ScalarInput] = {
            demand: Scalar(0.0) for demand in EnergyDemandID
        }

        self.power_transfer: dict[tuple[EnergyDemandID, EnergyDemandID], CurveInput] = {
            (source, sink): Scalar(0.0)
            for source in EnergyDemandID
            for sink in EnergyDemandID
        }

    # external methods (DSL attributes) ------------------------------------------------
    @deck_attribute()
    def set_shore_power_capacity(self, shore_power_capacity: ScalarArgument) -> None:
        """Set the vessel-side shore power connection capacity."""
        self.shore_power_capacity = assign_value(
            as_scalar(shore_power_capacity), type_=VARIABLE, lower=0.0
        )

    # external methods (DSL commands) --------------------------------------------------
    @deck_command()
    def set_energy_saving(self, energy_type: str, saving: ScalarArgument) -> None:
        """Set the fraction of the raw energy demand the technology saves."""
        id_ = assign_id(energy_type, EnergyDemandID)
        value_ = assign_value(as_scalar(saving), type_=VARIABLE, lower=0.0)

        write_matching_keys(id_, value_, self.energy_saving)

    @deck_command()
    def set_external_power(self, energy_type: str, power: ScalarArgument) -> None:
        """Set the external power the technology supplies to an energy demand type."""
        id_ = assign_id(energy_type, EnergyDemandID)
        value_ = assign_value(as_scalar(power), type_=VARIABLE, lower=0.0)

        write_matching_keys(id_, value_, self.external_power)

    @deck_command()
    def set_power_transfer(
        self, source_id: str, sink_id: str, transfer: CurveArgument
    ) -> None:
        """Set the power transferred from a source energy type to a sink energy type."""
        source = assign_id(source_id, EnergyDemandID)
        sink = assign_id(sink_id, EnergyDemandID)
        value_ = assign_value(as_scalar(transfer), type_=(CURVE, VARIABLE), lower=0.0)

        write_matching_key_pairs((source, sink), value_, self.power_transfer)

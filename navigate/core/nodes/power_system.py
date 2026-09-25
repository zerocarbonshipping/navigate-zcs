# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the PowerSystem node, the converters meeting a vessel's energy demand."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core import assign_value
from navigate.core.enum_ import EnergyDemandTypeID
from navigate.core.node_type import CONVERTER, POWER_SYSTEM
from navigate.core.nodes._machinery import _Machinery
from navigate.util import list_is_unique

if TYPE_CHECKING:
    from navigate.core.nodes.converter import Converter


class PowerSystem(_Machinery):
    """The propulsion, electrical and heat converters of a vessel."""

    def __init__(self, name: str) -> None:
        super().__init__(name, POWER_SYSTEM)

        # external variables -----------------------------------------------------------
        # converters
        self.propulsion: Converter
        self.electrical: Converter
        self.heat: Converter

    # external methods (DSL attributes) ------------------------------------------------
    def set_propulsion(self, propulsion: Converter) -> None:
        """
        Set the converter used to satisfy the propulsion demand.

        Examples
        --------
        - Converter("name")

        Parameters
        ----------
        propulsion
            A converter used to satisfy the propulsion demand.
        """
        self.propulsion = assign_value(propulsion, scalar=False, type_=CONVERTER)

    def set_electrical(self, electrical: Converter) -> None:
        """
        Set the converter used to satisfy the electrical demand.

        Examples
        --------
        - Converter("name")

        Parameters
        ----------
        electrical
            A converter used to satisfy the electrical demand.
        """
        self.electrical = assign_value(electrical, scalar=False, type_=CONVERTER)

    def set_heat(self, heat: Converter) -> None:
        """
        Set the converter used to satisfy the heat demand.

        Examples
        --------
        - Converter("name")

        Parameters
        ----------
        heat
            A converter used to satisfy the heat demand.
        """
        self.heat = assign_value(heat, scalar=False, type_=CONVERTER)

    # internal methods -----------------------------------------------------------------
    def check_consistency(self) -> None:
        # downstream code sums over the converters (installed power, cost, fuel demand);
        # a shared one would double-count
        names = (self.propulsion.name, self.electrical.name, self.heat.name)
        if not list_is_unique(names):
            raise ValueError(
                f"{self}: 'Propulsion', 'Electrical' and 'Heat' must be three distinct"
                f" converters, got {names}."
            )

    def get_converters(self) -> tuple[Converter, Converter, Converter]:
        return self.propulsion, self.electrical, self.heat

    def get_converter_by_energy_type(
        self, demand_type: EnergyDemandTypeID
    ) -> Converter:
        match demand_type:
            case EnergyDemandTypeID.PROPULSION:
                return self.propulsion
            case EnergyDemandTypeID.ELECTRICAL:
                return self.electrical
            case EnergyDemandTypeID.HEAT:
                return self.heat

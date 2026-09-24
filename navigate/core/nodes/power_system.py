# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core import assign_value
from navigate.core.enum_ import EnergyDemandTypeID
from navigate.core.node_type import CONVERTER, POWER_SYSTEM
from navigate.core.nodes._machinery import _Machinery
from navigate.exceptions import no_value_assigned_error
from navigate.util import list_is_unique

if TYPE_CHECKING:
    from navigate.core.nodes.converter import Converter


class PowerSystem(_Machinery):
    def __init__(self, name: str) -> None:
        super().__init__(name, POWER_SYSTEM)

        # external variables -----------------------------------------------------------
        # converters
        self.propulsion: Converter | None = None
        self.electrical: Converter | None = None
        self.heat: Converter | None = None

    # external methods (DSL attributes) ------------------------------------------------
    def set_propulsion(self, propulsion):
        """
        Set the converter used to satisfy the propulsion demand.

        Examples
        --------
        - Converter("name")

        Parameters
        ----------
        propulsion : Node
            A converter used to satisfy the propulsion demand.
        """
        self.propulsion = assign_value(propulsion, scalar=False, type_=CONVERTER)

    def set_electrical(self, electrical):
        """
        Set the converter used to satisfy the electrical demand.

        Examples
        --------
        - Converter("name")

        Parameters
        ----------
        electrical : Node
            A converter used to satisfy the electrical demand.
        """
        self.electrical = assign_value(electrical, scalar=False, type_=CONVERTER)

    def set_heat(self, heat):
        """
        Set the converter used to satisfy the heat demand.

        Examples
        --------
        - Converter("name")

        Parameters
        ----------
        heat : Node
            A converter used to satisfy the heat demand.
        """
        self.heat = assign_value(heat, scalar=False, type_=CONVERTER)

    # internal methods -----------------------------------------------------------------
    def check_requirements(self) -> None:

        if not self.propulsion:
            no_value_assigned_error(self, "Propulsion")

        if not self.electrical:
            no_value_assigned_error(self, "Electrical")

        if not self.heat:
            no_value_assigned_error(self, "Heat")

    def check_consistency(self) -> None:
        # downstream code sums over the converters (installed power, cost, fuel demand);
        # a shared one would double-count
        names = (self.propulsion.name, self.electrical.name, self.heat.name)
        if not list_is_unique(names):
            raise ValueError(
                f"{self}: 'Propulsion', 'Electrical' and 'Heat' must be three distinct"
                f" converters, got {names}."
            )

    def get_converters(self):
        return self.propulsion, self.electrical, self.heat

    def get_converter_by_energy_type(self, demand_type):
        match demand_type:
            case EnergyDemandTypeID.PROPULSION:
                converter = self.propulsion
            case EnergyDemandTypeID.ELECTRICAL:
                converter = self.electrical
            case EnergyDemandTypeID.HEAT:
                converter = self.heat
            case _:
                converter = None

        return converter

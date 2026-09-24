# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Attribute validation logic in navigate.parser._attributes.

Also the domain exception the parser reports a rejected deck value as, the
check that belongs beside the assignment errors the validation itself raises.
"""

from __future__ import annotations

import pytest

from navigate.core.enum_ import SimulationSectionID
from navigate.exceptions import AttributeAssignmentError, CommandError
from navigate.parser._attributes import (
    check_general_node_attribute_is_allowed,
    check_node_attribute_is_allowed,
    instance_to_dsl_name,
)


class TestInstanceToDslName:
    def test_returns_the_assigning_dsl_attribute(self):
        assert instance_to_dsl_name("Levy", "jurisdiction") == "Jurisdiction"
        assert (
            instance_to_dsl_name("Fuel", "lower_heating_value") == "LowerHeatingValue"
        )

    def test_falls_back_to_the_instance_name(self):
        assert instance_to_dsl_name("Levy", "include_vessel") == "include_vessel"


class TestCheckNodeAttributeIsAllowed:
    def test_valid_attribute_both_sections(self):
        """Lifetime is allowed for Vessel in both DEFINE and EVENTS."""
        assert check_node_attribute_is_allowed(
            "Vessel", "Lifetime", SimulationSectionID.DEFINE
        )
        assert check_node_attribute_is_allowed(
            "Vessel", "Lifetime", SimulationSectionID.EVENTS
        )

    def test_valid_attribute_define_only(self):
        """FuelType is DEFINE-only for Vessel."""
        assert check_node_attribute_is_allowed(
            "Vessel", "FuelType", SimulationSectionID.DEFINE
        )

    def test_define_only_attribute_in_events_raises(self):
        """FuelType on Vessel is DEFINE-only — using it in EVENTS should raise."""
        with pytest.raises(AttributeAssignmentError, match="does not allow setting"):
            check_node_attribute_is_allowed(
                "Vessel", "FuelType", SimulationSectionID.EVENTS
            )

    def test_unknown_attribute_raises(self):
        """An attribute that doesn't exist on any node should raise."""
        with pytest.raises(AttributeAssignmentError, match="has no attribute"):
            check_node_attribute_is_allowed(
                "Vessel", "NonExistentAttribute", SimulationSectionID.DEFINE
            )


class TestCheckGeneralNodeAttributeIsAllowed:
    def test_model_definition_start_date(self):
        assert check_general_node_attribute_is_allowed(
            "ModelDefinition", "StartDate", SimulationSectionID.DEFINE
        )

    def test_model_definition_start_date_in_events_raises(self):
        with pytest.raises(AttributeAssignmentError, match="does not allow setting"):
            check_general_node_attribute_is_allowed(
                "ModelDefinition", "StartDate", SimulationSectionID.EVENTS
            )

    def test_unknown_general_node_attribute_raises(self):
        with pytest.raises(AttributeAssignmentError, match="has no attribute"):
            check_general_node_attribute_is_allowed(
                "ModelDefinition", "Bogus", SimulationSectionID.DEFINE
            )


class TestRejectedValueIsADomainError:
    """
    A rejected value carries a class the CLI handler catches.

    The handler catches NavigateError, so the class the parser re-raises
    matters as much as the located sentence it carries.
    """

    def test_rejected_attribute_value(self, read_deck):
        with pytest.raises(
            AttributeAssignmentError,
            match="attribute 'Capex' only allows assignment of scalars",
        ):
            read_deck('Vessel "v" {\n    Capex = FLAT\n}\n')

    def test_rejected_command_value(self, read_deck):
        with pytest.raises(
            CommandError, match=r"'set_operational_saving_sea' must be ≤ 1\.0"
        ):
            read_deck(
                'Fleet "fleet" {\n    set_operational_saving_sea(PROPULSION, 2.0)\n}\n'
            )

    def test_rejected_table_value(self, read_deck):
        # the table is only checked once the start date can resolve its dates,
        # so its rejection reaches the deck from the reference-table pass
        with pytest.raises(
            AttributeAssignmentError, match="'x' must be strictly increasing"
        ):
            read_deck(
                'Forecast "f" {\n'
                "    Table = [\n"
                "        2.0 1.0\n"
                "        1.0 2.0\n"
                "    ]\n"
                "}\n"
            )

# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for navigate.parser._attributes — attribute validation logic."""
import pytest

from navigate.core.enum_ import SimulationSectionID
from navigate.exceptions import AttributeAssignmentError
from navigate.parser._attributes import (
    GENERAL_NODE_ATTRIBUTE_SECTIONS,
    NODE_ATTRIBUTE_SECTIONS,
    check_general_node_attribute_is_allowed,
    check_node_attribute_is_allowed,
    instance_to_dsl_name,
)


class TestInstanceToDslName:

    def test_returns_the_assigning_dsl_attribute(self):
        assert instance_to_dsl_name("Levy", "jurisdiction") == "Jurisdiction"
        assert instance_to_dsl_name("Fuel", "lower_heating_value") == "LowerHeatingValue"

    def test_falls_back_to_the_instance_name(self):
        assert instance_to_dsl_name("Levy", "include_vessel") == "include_vessel"


class TestCheckNodeAttributeIsAllowed:

    def test_valid_attribute_both_sections(self):
        """Lifetime is allowed for Vessel in both DEFINE and EVENTS."""
        assert check_node_attribute_is_allowed("Vessel", "Lifetime", SimulationSectionID.DEFINE)
        assert check_node_attribute_is_allowed("Vessel", "Lifetime", SimulationSectionID.EVENTS)

    def test_valid_attribute_define_only(self):
        """FuelType is DEFINE-only for Vessel."""
        assert check_node_attribute_is_allowed("Vessel", "FuelType", SimulationSectionID.DEFINE)

    def test_define_only_attribute_in_events_raises(self):
        """FuelType on Vessel is DEFINE-only — using it in EVENTS should raise."""
        with pytest.raises(AttributeAssignmentError, match="does not allow setting"):
            check_node_attribute_is_allowed("Vessel", "FuelType", SimulationSectionID.EVENTS)

    def test_unknown_attribute_raises(self):
        """An attribute that doesn't exist on any node should raise."""
        with pytest.raises(AttributeAssignmentError, match="has no attribute"):
            check_node_attribute_is_allowed("Vessel", "NonExistentAttribute", SimulationSectionID.DEFINE)

    @pytest.mark.parametrize("node_type", list(NODE_ATTRIBUTE_SECTIONS.keys()))
    def test_all_node_types_have_dict(self, node_type):
        """Every registered node type should have a dict (possibly empty)."""
        assert isinstance(NODE_ATTRIBUTE_SECTIONS[node_type], dict)


class TestCheckGeneralNodeAttributeIsAllowed:

    def test_model_definition_start_date(self):
        assert check_general_node_attribute_is_allowed("ModelDefinition", "StartDate", SimulationSectionID.DEFINE)

    def test_model_definition_start_date_in_events_raises(self):
        with pytest.raises(AttributeAssignmentError, match="does not allow setting"):
            check_general_node_attribute_is_allowed("ModelDefinition", "StartDate", SimulationSectionID.EVENTS)

    def test_unknown_general_node_attribute_raises(self):
        with pytest.raises(AttributeAssignmentError, match="has no attribute"):
            check_general_node_attribute_is_allowed("ModelDefinition", "Bogus", SimulationSectionID.DEFINE)

    @pytest.mark.parametrize("node_type", list(GENERAL_NODE_ATTRIBUTE_SECTIONS.keys()))
    def test_all_general_node_types_have_dict(self, node_type):
        assert isinstance(GENERAL_NODE_ATTRIBUTE_SECTIONS[node_type], dict)

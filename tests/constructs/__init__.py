# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Tests for constructs package __init__.py exports."""

import pytest


class TestConstructsExports:
    """Test that all expected classes and functions are exported."""

    def test_base_construct_exported(self) -> None:
        """Test BaseConstruct is exported."""
        from aws_api_factory.constructs import BaseConstruct

        assert BaseConstruct is not None

    def test_apply_global_tags_exported(self) -> None:
        """Test apply_global_tags is exported."""
        from aws_api_factory.constructs import apply_global_tags

        assert callable(apply_global_tags)

    def test_sanitize_resource_id_exported(self) -> None:
        """Test sanitize_resource_id is exported."""
        from aws_api_factory.constructs import sanitize_resource_id

        assert callable(sanitize_resource_id)

    def test_factory_stack_exported(self) -> None:
        """Test FactoryStack is exported."""
        from aws_api_factory.constructs import FactoryStack

        assert FactoryStack is not None

    def test_create_factory_stack_exported(self) -> None:
        """Test create_factory_stack is exported."""
        from aws_api_factory.constructs import create_factory_stack

        assert callable(create_factory_stack)

    def test_construct_registry_exported(self) -> None:
        """Test ConstructRegistry is exported."""
        from aws_api_factory.constructs import ConstructRegistry

        assert ConstructRegistry is not None

    def test_construct_registration_exported(self) -> None:
        """Test ConstructRegistration is exported."""
        from aws_api_factory.constructs import ConstructRegistration

        assert ConstructRegistration is not None

    def test_get_default_registry_exported(self) -> None:
        """Test get_default_registry is exported."""
        from aws_api_factory.constructs import get_default_registry

        assert callable(get_default_registry)

    def test_register_construct_exported(self) -> None:
        """Test register_construct is exported."""
        from aws_api_factory.constructs import register_construct

        assert callable(register_construct)

    def test_output_manager_exported(self) -> None:
        """Test OutputManager is exported."""
        from aws_api_factory.constructs import OutputManager

        assert OutputManager is not None

    def test_output_entry_exported(self) -> None:
        """Test OutputEntry is exported."""
        from aws_api_factory.constructs import OutputEntry

        assert OutputEntry is not None

    def test_all_exports_in_dunder_all(self) -> None:
        """Test __all__ contains expected exports."""
        from aws_api_factory import constructs

        expected = [
            "BaseConstruct",
            "apply_global_tags",
            "sanitize_resource_id",
            "FactoryStack",
            "create_factory_stack",
            "ConstructRegistry",
            "ConstructRegistration",
            "get_default_registry",
            "register_construct",
            "OutputManager",
            "OutputEntry",
        ]
        for name in expected:
            assert name in constructs.__all__, f"{name} not in __all__"

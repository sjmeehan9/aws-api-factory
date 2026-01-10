# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Tests for FactoryStack, ConstructRegistry, and related classes."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from aws_cdk import App, Stack
from aws_cdk import assertions as assertions_module
from constructs import Construct

from aws_api_factory.config.defaults import get_defaults
from aws_api_factory.config.models import FactoryConfig, ProfileEnum
from aws_api_factory.constructs.base import (
    BaseConstruct,
    apply_global_tags,
    sanitize_resource_id,
)
from aws_api_factory.constructs.factory_stack import (
    ConstructRegistration,
    ConstructRegistry,
    FactoryStack,
    create_factory_stack,
    get_default_registry,
)
from aws_api_factory.constructs.outputs import OutputEntry, OutputManager

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def app() -> App:
    """Create a CDK App for testing."""
    return App()


@pytest.fixture
def minimal_config() -> FactoryConfig:
    """Create a minimal valid configuration."""
    return FactoryConfig.model_validate(
        {
            "project": {"name": "test-api", "envs": ["dev", "prod"]},
            "profile": "minimal",
            "apis": {
                "rest": {
                    "enabled": True,
                    "routes": [
                        {
                            "path": "/hello",
                            "methods": ["GET"],
                            "service": "hello",
                            "auth": "none",
                        }
                    ],
                }
            },
            "compute": {
                "lambda": {
                    "enabled": True,
                    "services": {
                        "hello": {"entry": "src/services/hello/handler.py:handler"}
                    },
                }
            },
        }
    )


@pytest.fixture
def scalable_config() -> FactoryConfig:
    """Create a scalable profile configuration."""
    return FactoryConfig.model_validate(
        {
            "project": {"name": "prod-api", "envs": ["dev", "staging", "prod"]},
            "profile": "scalable",
            "apis": {
                "rest": {
                    "enabled": True,
                    "routes": [
                        {
                            "path": "/orders",
                            "methods": ["GET", "POST"],
                            "service": "orders",
                            "auth": "api_key",
                        }
                    ],
                }
            },
            "compute": {
                "lambda": {
                    "enabled": True,
                    "services": {
                        "orders": {"entry": "src/services/orders/handler.py:handler"}
                    },
                }
            },
            "observability": {"level": "enhanced"},
        }
    )


# =============================================================================
# OutputEntry Tests
# =============================================================================


class TestOutputEntry:
    """Tests for OutputEntry dataclass."""

    def test_create_basic_entry(self) -> None:
        """Test creating a basic output entry."""
        entry = OutputEntry(
            key="ApiEndpoint",
            value="https://api.example.com",
            description="REST API endpoint",
        )
        assert entry.key == "ApiEndpoint"
        assert entry.value == "https://api.example.com"
        assert entry.description == "REST API endpoint"
        assert entry.export_name is None
        assert entry.category == "general"

    def test_create_entry_with_export(self) -> None:
        """Test creating an entry with export name."""
        entry = OutputEntry(
            key="LambdaArn",
            value="arn:aws:lambda:us-east-1:123:function:hello",
            description="Lambda function ARN",
            export_name="test-api-dev-LambdaArn",
            category="compute",
        )
        assert entry.export_name == "test-api-dev-LambdaArn"
        assert entry.category == "compute"


# =============================================================================
# OutputManager Tests
# =============================================================================


class TestOutputManager:
    """Tests for OutputManager class."""

    def test_init(self, app: App) -> None:
        """Test OutputManager initialization."""
        stack = Stack(app, "TestStack")
        manager = OutputManager(stack, "test-api", "dev")

        assert manager.project_name == "test-api"
        assert manager.environment == "dev"
        assert len(manager) == 0

    def test_add_output(self, app: App) -> None:
        """Test adding an output."""
        stack = Stack(app, "TestStack")
        manager = OutputManager(stack, "test-api", "dev")

        manager.add(
            key="ApiEndpoint",
            value="https://api.example.com",
            description="API endpoint",
        )

        assert len(manager) == 1
        assert "ApiEndpoint" in manager

    def test_add_output_with_category(self, app: App) -> None:
        """Test adding an output with category."""
        stack = Stack(app, "TestStack")
        manager = OutputManager(stack, "test-api", "dev")

        manager.add(
            key="LambdaArn",
            value="arn:aws:lambda:...",
            description="Lambda ARN",
            category="compute",
        )

        entry = manager.get("LambdaArn")
        assert entry is not None
        assert entry.category == "compute"

    def test_add_duplicate_key_raises(self, app: App) -> None:
        """Test adding duplicate key raises ValueError."""
        stack = Stack(app, "TestStack")
        manager = OutputManager(stack, "test-api", "dev")

        manager.add(key="ApiEndpoint", value="v1", description="desc")

        with pytest.raises(ValueError, match="already exists"):
            manager.add(key="ApiEndpoint", value="v2", description="desc")

    def test_get_output(self, app: App) -> None:
        """Test retrieving an output."""
        stack = Stack(app, "TestStack")
        manager = OutputManager(stack, "test-api", "dev")

        manager.add(key="TestKey", value="TestValue", description="Test desc")

        entry = manager.get("TestKey")
        assert entry is not None
        assert entry.value == "TestValue"

    def test_get_nonexistent_returns_none(self, app: App) -> None:
        """Test retrieving nonexistent output returns None."""
        stack = Stack(app, "TestStack")
        manager = OutputManager(stack, "test-api", "dev")

        assert manager.get("NonexistentKey") is None

    def test_get_all(self, app: App) -> None:
        """Test getting all outputs."""
        stack = Stack(app, "TestStack")
        manager = OutputManager(stack, "test-api", "dev")

        manager.add(key="Key1", value="Value1", description="Desc1")
        manager.add(key="Key2", value="Value2", description="Desc2")

        all_outputs = manager.get_all()
        assert len(all_outputs) == 2
        assert "Key1" in all_outputs
        assert "Key2" in all_outputs

    def test_get_by_category(self, app: App) -> None:
        """Test filtering outputs by category."""
        stack = Stack(app, "TestStack")
        manager = OutputManager(stack, "test-api", "dev")

        manager.add(key="Api1", value="v1", description="d1", category="api")
        manager.add(key="Api2", value="v2", description="d2", category="api")
        manager.add(key="Lambda1", value="v3", description="d3", category="compute")

        api_outputs = manager.get_by_category("api")
        assert len(api_outputs) == 2

        compute_outputs = manager.get_by_category("compute")
        assert len(compute_outputs) == 1

    def test_get_categories(self, app: App) -> None:
        """Test getting unique categories."""
        stack = Stack(app, "TestStack")
        manager = OutputManager(stack, "test-api", "dev")

        manager.add(key="A", value="v", description="d", category="api")
        manager.add(key="B", value="v", description="d", category="compute")
        manager.add(key="C", value="v", description="d", category="api")

        categories = manager.get_categories()
        assert categories == ["api", "compute"]

    def test_export_to_cfn(self, app: App) -> None:
        """Test exporting outputs to CloudFormation."""
        stack = Stack(app, "TestStack")
        manager = OutputManager(stack, "test-api", "dev")

        manager.add(key="Endpoint", value="https://example.com", description="Endpoint")
        manager.export_to_cfn()

        # Synthesize and check outputs exist
        template = assertions_module.Template.from_stack(stack)
        outputs = template.find_outputs("*")
        assert len(outputs) > 0

    def test_export_to_cfn_twice_raises(self, app: App) -> None:
        """Test calling export_to_cfn twice raises error."""
        stack = Stack(app, "TestStack")
        manager = OutputManager(stack, "test-api", "dev")

        manager.add(key="Key", value="Value", description="Desc")
        manager.export_to_cfn()

        with pytest.raises(ValueError, match="already been exported"):
            manager.export_to_cfn()

    def test_add_after_export_raises(self, app: App) -> None:
        """Test adding output after export raises error."""
        stack = Stack(app, "TestStack")
        manager = OutputManager(stack, "test-api", "dev")

        manager.add(key="Key1", value="Value1", description="Desc1")
        manager.export_to_cfn()

        with pytest.raises(ValueError, match="already been exported"):
            manager.add(key="Key2", value="Value2", description="Desc2")

    def test_export_to_json(self, app: App, tmp_path: Any) -> None:
        """Test exporting outputs to JSON file."""
        stack = Stack(app, "TestStack")
        manager = OutputManager(stack, "test-api", "dev")

        manager.add(
            key="Endpoint",
            value="https://example.com",
            description="API",
            category="api",
        )

        output_file = tmp_path / "outputs.json"
        manager.export_to_json(output_file)

        assert output_file.exists()

        import json

        with open(output_file) as f:
            data = json.load(f)

        assert data["metadata"]["project"] == "test-api"
        assert data["metadata"]["environment"] == "dev"
        assert "api" in data["outputs"]

    def test_to_dict(self, app: App) -> None:
        """Test converting outputs to dictionary."""
        stack = Stack(app, "TestStack")
        manager = OutputManager(stack, "test-api", "dev")

        manager.add(key="K1", value="V1", description="D1", category="cat1")
        manager.add(key="K2", value="V2", description="D2", category="cat2")

        result = manager.to_dict()
        assert "cat1" in result
        assert "cat2" in result
        assert result["cat1"]["K1"]["value"] == "V1"

    def test_to_flat_dict(self, app: App) -> None:
        """Test converting outputs to flat dictionary."""
        stack = Stack(app, "TestStack")
        manager = OutputManager(stack, "test-api", "dev")

        manager.add(key="K1", value="V1", description="D1")
        manager.add(key="K2", value="V2", description="D2")

        result = manager.to_flat_dict()
        assert result == {"K1": "V1", "K2": "V2"}

    def test_summary(self, app: App) -> None:
        """Test generating output summary."""
        stack = Stack(app, "TestStack")
        manager = OutputManager(stack, "test-api", "dev")

        manager.add(
            key="Endpoint",
            value="https://...",
            description="API endpoint",
            category="api",
        )

        summary = manager.summary()
        assert "test-api" in summary
        assert "dev" in summary
        assert "API" in summary
        assert "Endpoint" in summary

    def test_summary_empty(self, app: App) -> None:
        """Test summary with no outputs."""
        stack = Stack(app, "TestStack")
        manager = OutputManager(stack, "test-api", "dev")

        summary = manager.summary()
        assert "No outputs" in summary


# =============================================================================
# ConstructRegistry Tests
# =============================================================================


class TestConstructRegistry:
    """Tests for ConstructRegistry class."""

    def test_init(self) -> None:
        """Test registry initialization."""
        registry = ConstructRegistry()
        assert len(registry) == 0

    def test_register_construct(self) -> None:
        """Test registering a construct."""

        class DummyConstruct(BaseConstruct):
            def _create_resources(self) -> None:
                pass

            def validate_config(self) -> list[str]:
                return []

        registry = ConstructRegistry()
        registry.register(
            DummyConstruct, "test.section", enabled_check=lambda c: True, priority=50
        )

        assert len(registry) == 1
        assert "test.section" in registry

    def test_register_duplicate_raises(self) -> None:
        """Test registering duplicate config section raises error."""

        class DummyConstruct(BaseConstruct):
            def _create_resources(self) -> None:
                pass

            def validate_config(self) -> list[str]:
                return []

        registry = ConstructRegistry()
        registry.register(DummyConstruct, "test.section")

        with pytest.raises(ValueError, match="already registered"):
            registry.register(DummyConstruct, "test.section")

    def test_unregister_construct(self) -> None:
        """Test unregistering a construct."""

        class DummyConstruct(BaseConstruct):
            def _create_resources(self) -> None:
                pass

            def validate_config(self) -> list[str]:
                return []

        registry = ConstructRegistry()
        registry.register(DummyConstruct, "test.section")
        assert registry.is_registered("test.section")

        result = registry.unregister("test.section")
        assert result is True
        assert not registry.is_registered("test.section")

    def test_unregister_nonexistent_returns_false(self) -> None:
        """Test unregistering nonexistent returns False."""
        registry = ConstructRegistry()
        result = registry.unregister("nonexistent")
        assert result is False

    def test_get_enabled_constructs(self, minimal_config: FactoryConfig) -> None:
        """Test getting enabled constructs."""

        class EnabledConstruct(BaseConstruct):
            def _create_resources(self) -> None:
                pass

            def validate_config(self) -> list[str]:
                return []

        class DisabledConstruct(BaseConstruct):
            def _create_resources(self) -> None:
                pass

            def validate_config(self) -> list[str]:
                return []

        registry = ConstructRegistry()
        registry.register(
            EnabledConstruct,
            "enabled.section",
            enabled_check=lambda c: True,
            priority=10,
        )
        registry.register(
            DisabledConstruct,
            "disabled.section",
            enabled_check=lambda c: False,
            priority=20,
        )

        enabled = registry.get_enabled_constructs(minimal_config)
        assert len(enabled) == 1
        assert enabled[0].config_section == "enabled.section"

    def test_get_enabled_constructs_sorted_by_priority(
        self, minimal_config: FactoryConfig
    ) -> None:
        """Test enabled constructs are sorted by priority."""

        class HighPriorityConstruct(BaseConstruct):
            def _create_resources(self) -> None:
                pass

            def validate_config(self) -> list[str]:
                return []

        class LowPriorityConstruct(BaseConstruct):
            def _create_resources(self) -> None:
                pass

            def validate_config(self) -> list[str]:
                return []

        registry = ConstructRegistry()
        registry.register(HighPriorityConstruct, "high", priority=100)
        registry.register(LowPriorityConstruct, "low", priority=10)

        enabled = registry.get_enabled_constructs(minimal_config)
        assert len(enabled) == 2
        assert enabled[0].config_section == "low"
        assert enabled[1].config_section == "high"


# =============================================================================
# Base Construct Tests
# =============================================================================


class TestBaseConstruct:
    """Tests for BaseConstruct class."""

    def test_generate_resource_name(
        self, app: App, minimal_config: FactoryConfig
    ) -> None:
        """Test resource name generation."""
        stack = Stack(app, "TestStack")
        output_manager = OutputManager(stack, "test-api", "dev")
        profile_defaults = get_defaults(ProfileEnum.MINIMAL)

        class TestConstruct(BaseConstruct):
            def _create_resources(self) -> None:
                pass

            def validate_config(self) -> list[str]:
                return []

        construct = TestConstruct(
            stack,
            "Test",
            config=minimal_config,
            profile_defaults=profile_defaults,
            output_manager=output_manager,
            environment="dev",
        )

        name = construct.generate_resource_name("lambda", "orders")
        assert name == "test-api-dev-lambda-orders"

    def test_generate_resource_name_without_env(
        self, app: App, minimal_config: FactoryConfig
    ) -> None:
        """Test resource name generation without environment."""
        stack = Stack(app, "TestStack")
        output_manager = OutputManager(stack, "test-api", "dev")
        profile_defaults = get_defaults(ProfileEnum.MINIMAL)

        class TestConstruct(BaseConstruct):
            def _create_resources(self) -> None:
                pass

            def validate_config(self) -> list[str]:
                return []

        construct = TestConstruct(
            stack,
            "Test",
            config=minimal_config,
            profile_defaults=profile_defaults,
            output_manager=output_manager,
            environment="dev",
        )

        name = construct.generate_resource_name("lambda", "orders", include_env=False)
        assert name == "test-api-lambda-orders"

    def test_generate_resource_name_truncation(
        self, app: App, minimal_config: FactoryConfig
    ) -> None:
        """Test resource name truncation."""
        stack = Stack(app, "TestStack")
        output_manager = OutputManager(stack, "test-api", "dev")
        profile_defaults = get_defaults(ProfileEnum.MINIMAL)

        class TestConstruct(BaseConstruct):
            def _create_resources(self) -> None:
                pass

            def validate_config(self) -> list[str]:
                return []

        construct = TestConstruct(
            stack,
            "Test",
            config=minimal_config,
            profile_defaults=profile_defaults,
            output_manager=output_manager,
            environment="dev",
        )

        name = construct.generate_resource_name(
            "lambda", "very-long-service-name-that-exceeds-limit", max_length=30
        )
        assert len(name) <= 30

    def test_add_output(self, app: App, minimal_config: FactoryConfig) -> None:
        """Test adding output through construct."""
        stack = Stack(app, "TestStack")
        output_manager = OutputManager(stack, "test-api", "dev")
        profile_defaults = get_defaults(ProfileEnum.MINIMAL)

        class TestConstruct(BaseConstruct):
            def _create_resources(self) -> None:
                self.add_output(
                    key="TestOutput",
                    value="test-value",
                    description="Test output",
                )

            def validate_config(self) -> list[str]:
                return []

        TestConstruct(
            stack,
            "Test",
            config=minimal_config,
            profile_defaults=profile_defaults,
            output_manager=output_manager,
            environment="dev",
        )

        assert "TestOutput" in output_manager

    def test_validation_failure_raises(
        self, app: App, minimal_config: FactoryConfig
    ) -> None:
        """Test that validation failure raises ValueError."""
        stack = Stack(app, "TestStack")
        output_manager = OutputManager(stack, "test-api", "dev")
        profile_defaults = get_defaults(ProfileEnum.MINIMAL)

        class FailingConstruct(BaseConstruct):
            def _create_resources(self) -> None:
                pass

            def validate_config(self) -> list[str]:
                return ["Error 1", "Error 2"]

        with pytest.raises(ValueError, match="validation failed"):
            FailingConstruct(
                stack,
                "Failing",
                config=minimal_config,
                profile_defaults=profile_defaults,
                output_manager=output_manager,
                environment="dev",
            )


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestSanitizeResourceId:
    """Tests for sanitize_resource_id function."""

    def test_simple_path(self) -> None:
        """Test sanitizing simple path."""
        result = sanitize_resource_id("/orders")
        assert result == "Orders"

    def test_path_with_parameter(self) -> None:
        """Test sanitizing path with parameter."""
        result = sanitize_resource_id("/orders/{id}")
        assert result == "OrdersId"

    def test_nested_path(self) -> None:
        """Test sanitizing nested path."""
        result = sanitize_resource_id("/orders/{orderId}/items")
        assert result == "OrdersOrderidItems"

    def test_starts_with_number(self) -> None:
        """Test sanitizing path starting with number."""
        result = sanitize_resource_id("123test")
        assert result.startswith("R") or result[0].isalpha()

    def test_empty_path(self) -> None:
        """Test sanitizing empty path."""
        result = sanitize_resource_id("")
        assert result == "Resource"

    def test_max_length(self) -> None:
        """Test max length enforcement."""
        long_path = "/very/long/path/with/many/segments/that/exceeds/limit"
        result = sanitize_resource_id(long_path, max_length=20)
        assert len(result) <= 20


class TestApplyGlobalTags:
    """Tests for apply_global_tags function."""

    def test_applies_tags(self, app: App, minimal_config: FactoryConfig) -> None:
        """Test that global tags are applied."""
        stack = Stack(app, "TestStack")
        apply_global_tags(stack, minimal_config, "dev")

        # Synthesize and check tags
        template = assertions_module.Template.from_stack(stack)
        # Tags are applied via Aspects, which are visible in resource properties


# =============================================================================
# FactoryStack Tests
# =============================================================================


class TestFactoryStack:
    """Tests for FactoryStack class."""

    def test_create_minimal_stack(
        self, app: App, minimal_config: FactoryConfig
    ) -> None:
        """Test creating a minimal stack."""
        stack = FactoryStack(app, "TestStack", config=minimal_config, environment="dev")

        assert stack.config == minimal_config
        assert stack.environment_name == "dev"
        assert stack.stack_name == "test-api-dev"

    def test_create_scalable_stack(
        self, app: App, scalable_config: FactoryConfig
    ) -> None:
        """Test creating a scalable profile stack."""
        stack = FactoryStack(
            app, "ProdStack", config=scalable_config, environment="prod"
        )

        assert stack.config.profile == ProfileEnum.SCALABLE
        assert stack.environment_name == "prod"

    def test_invalid_environment_raises(
        self, app: App, minimal_config: FactoryConfig
    ) -> None:
        """Test that invalid environment raises ValueError."""
        with pytest.raises(ValueError, match="not found in project.envs"):
            FactoryStack(app, "TestStack", config=minimal_config, environment="staging")

    def test_standard_outputs_added(
        self, app: App, minimal_config: FactoryConfig
    ) -> None:
        """Test that standard metadata outputs are added."""
        stack = FactoryStack(app, "TestStack", config=minimal_config, environment="dev")

        assert "StackName" in stack.output_manager
        assert "ProjectName" in stack.output_manager
        assert "Environment" in stack.output_manager
        assert "Profile" in stack.output_manager
        assert "Region" in stack.output_manager

    def test_get_construct_returns_none_for_unregistered(
        self, app: App, minimal_config: FactoryConfig
    ) -> None:
        """Test get_construct returns None for unregistered construct."""
        stack = FactoryStack(app, "TestStack", config=minimal_config, environment="dev")

        result = stack.get_construct("nonexistent.section")
        assert result is None

    def test_has_construct_false_for_unregistered(
        self, app: App, minimal_config: FactoryConfig
    ) -> None:
        """Test has_construct returns False for unregistered."""
        stack = FactoryStack(app, "TestStack", config=minimal_config, environment="dev")

        assert not stack.has_construct("nonexistent.section")

    def test_stack_synthesizes(self, app: App, minimal_config: FactoryConfig) -> None:
        """Test that stack synthesizes valid CloudFormation."""
        stack = FactoryStack(app, "TestStack", config=minimal_config, environment="dev")

        template = assertions_module.Template.from_stack(stack)
        # Should have outputs
        outputs = template.find_outputs("*")
        assert len(outputs) > 0

    def test_custom_registry(self, app: App, minimal_config: FactoryConfig) -> None:
        """Test using a custom registry."""
        custom_registry = ConstructRegistry()

        stack = FactoryStack(
            app,
            "TestStack",
            config=minimal_config,
            environment="dev",
            registry=custom_registry,
        )

        # With empty registry, no constructs created
        assert len(stack.constructs) == 0


class TestCreateFactoryStack:
    """Tests for create_factory_stack convenience function."""

    def test_creates_stack(self, app: App, minimal_config: FactoryConfig) -> None:
        """Test that create_factory_stack creates a valid stack."""
        stack = create_factory_stack(app, minimal_config, "dev")

        assert isinstance(stack, FactoryStack)
        assert stack.environment_name == "dev"

    def test_custom_stack_id(self, app: App, minimal_config: FactoryConfig) -> None:
        """Test custom stack ID."""
        stack = create_factory_stack(
            app, minimal_config, "dev", stack_id="CustomStackId"
        )

        # Stack was created with custom ID
        assert stack is not None


class TestDefaultRegistry:
    """Tests for default registry functions."""

    def test_get_default_registry(self) -> None:
        """Test get_default_registry returns same instance."""
        reg1 = get_default_registry()
        reg2 = get_default_registry()
        assert reg1 is reg2

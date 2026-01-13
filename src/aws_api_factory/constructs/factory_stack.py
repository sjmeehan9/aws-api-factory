# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Factory Stack for AWS API Factory.

This module provides the FactoryStack class, the main CDK stack that
composes all factory constructs based on configuration. It also provides
the ConstructRegistry for dynamic construct loading and composition.

Example:
    >>> from aws_api_factory.constructs import FactoryStack
    >>> from aws_api_factory.config import load_config, resolve_config
    >>> config = load_config("factory.yaml")
    >>> resolved = resolve_config(config)
    >>> stack = FactoryStack(app, "MyApiStack", config=resolved, environment="dev")

"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

from aws_cdk import Aws, Duration, RemovalPolicy, Stack
from constructs import Construct

from aws_api_factory.constructs.base import BaseConstruct, apply_global_tags
from aws_api_factory.constructs.outputs import OutputManager

if TYPE_CHECKING:
    from aws_cdk import Environment

    from aws_api_factory.config.defaults import ProfileDefaults
    from aws_api_factory.config.models import FactoryConfig


@dataclass
class ConstructRegistration:
    """Registration entry for a construct type.

    Attributes:
        construct_class: The construct class to instantiate.
        config_section: The config section that enables this construct.
        enabled_check: Optional callable to check if construct is enabled.
        priority: Lower priority constructs are created first (for dependencies).
    """

    construct_class: type[BaseConstruct]
    config_section: str
    enabled_check: Callable[[FactoryConfig], bool] | None = None
    priority: int = 100


class ConstructRegistry:
    """Registry for dynamic construct loading and composition.

    The ConstructRegistry manages the registration and instantiation of
    factory constructs based on configuration. Constructs are registered
    with their enabling condition, and the registry handles the creation
    order and dependency resolution.

    Constructs are created in priority order (lower numbers first) to
    handle dependencies. For example, authentication constructs might
    need to be created before API constructs that use them.

    Example:
        >>> registry = ConstructRegistry()
        >>> registry.register(
        ...     RestApiConstruct,
        ...     config_section="apis.rest",
        ...     enabled_check=lambda c: c.apis.rest.enabled,
        ...     priority=50,
        ... )
        >>> constructs = registry.instantiate_all(stack, config, defaults, ...)
    """

    def __init__(self) -> None:
        """Initialize an empty construct registry."""
        self._registrations: dict[str, ConstructRegistration] = {}

    def register(
        self,
        construct_class: type[BaseConstruct],
        config_section: str,
        *,
        enabled_check: Callable[[FactoryConfig], bool] | None = None,
        priority: int = 100,
    ) -> None:
        """Register a construct class.

        Args:
            construct_class: The construct class to register.
            config_section: The configuration section key (e.g., "apis.rest").
            enabled_check: Optional callable to check if construct is enabled.
                          If None, always enabled.
            priority: Creation priority (lower = first). Default 100.

        Raises:
            ValueError: If a construct with the same config_section is registered.
        """
        if config_section in self._registrations:
            raise ValueError(
                f"Construct for config section '{config_section}' already registered."
            )

        self._registrations[config_section] = ConstructRegistration(
            construct_class=construct_class,
            config_section=config_section,
            enabled_check=enabled_check,
            priority=priority,
        )

    def unregister(self, config_section: str) -> bool:
        """Unregister a construct.

        Args:
            config_section: The configuration section key to unregister.

        Returns:
            True if the construct was unregistered, False if not found.
        """
        if config_section in self._registrations:
            del self._registrations[config_section]
            return True
        return False

    def is_registered(self, config_section: str) -> bool:
        """Check if a construct is registered.

        Args:
            config_section: The configuration section key to check.

        Returns:
            True if registered, False otherwise.
        """
        return config_section in self._registrations

    def get_enabled_constructs(
        self, config: FactoryConfig
    ) -> list[ConstructRegistration]:
        """Get all enabled constructs for a configuration.

        Args:
            config: The factory configuration to check against.

        Returns:
            List of enabled ConstructRegistration entries, sorted by priority.
        """
        enabled = []
        for registration in self._registrations.values():
            # Check if enabled via callback or assume enabled if no check
            if registration.enabled_check is None:
                enabled.append(registration)
            elif registration.enabled_check(config):
                enabled.append(registration)

        # Sort by priority (lower first)
        return sorted(enabled, key=lambda r: r.priority)

    def instantiate_all(
        self,
        scope: Construct,
        config: FactoryConfig,
        profile_defaults: ProfileDefaults,
        output_manager: OutputManager,
        environment: str,
    ) -> dict[str, BaseConstruct]:
        """Instantiate all enabled constructs.

        Args:
            scope: The CDK construct scope (usually the Stack).
            config: The resolved factory configuration.
            profile_defaults: The profile defaults.
            output_manager: The output manager for registering outputs.
            environment: The deployment environment name.

        Returns:
            Dictionary mapping config section to instantiated construct.
        """
        constructs: dict[str, BaseConstruct] = {}

        for registration in self.get_enabled_constructs(config):
            construct_id = self._generate_construct_id(registration.config_section)
            construct = registration.construct_class(
                scope,
                construct_id,
                config=config,
                profile_defaults=profile_defaults,
                output_manager=output_manager,
                environment=environment,
            )
            constructs[registration.config_section] = construct

        return constructs

    def _generate_construct_id(self, config_section: str) -> str:
        """Generate a construct ID from config section.

        Args:
            config_section: The config section (e.g., "apis.rest").

        Returns:
            A suitable construct ID (e.g., "ApisRest").
        """
        parts = config_section.split(".")
        return "".join(part.capitalize() for part in parts)

    def __len__(self) -> int:
        """Return the number of registered constructs."""
        return len(self._registrations)

    def __contains__(self, config_section: str) -> bool:
        """Check if a config section is registered."""
        return config_section in self._registrations


# Global registry for core constructs
_default_registry = ConstructRegistry()


def get_default_registry() -> ConstructRegistry:
    """Get the default construct registry.

    Returns:
        The global default ConstructRegistry.
    """
    return _default_registry


def register_construct(
    construct_class: type[BaseConstruct],
    config_section: str,
    *,
    enabled_check: Callable[[FactoryConfig], bool] | None = None,
    priority: int = 100,
) -> None:
    """Register a construct with the default registry.

    This is a convenience function for registering constructs with
    the global default registry.

    Args:
        construct_class: The construct class to register.
        config_section: The configuration section key.
        enabled_check: Optional callable to check if construct is enabled.
        priority: Creation priority (lower = first).
    """
    _default_registry.register(
        construct_class,
        config_section,
        enabled_check=enabled_check,
        priority=priority,
    )


class FactoryStack(Stack):
    """Main CDK stack for AWS API Factory.

    FactoryStack is the primary stack class that composes all factory
    constructs based on the provided configuration. It:

    1. Applies global tags to all resources
    2. Creates an OutputManager for collecting outputs
    3. Instantiates constructs via the ConstructRegistry
    4. Exports all outputs as CloudFormation CfnOutputs

    Attributes:
        config: The resolved factory configuration.
        profile_defaults: The profile defaults for the user's profile.
        environment_name: The deployment environment name.
        output_manager: The output manager for this stack.
        constructs: Dictionary of instantiated constructs by config section.

    Example:
        >>> from aws_cdk import App
        >>> from aws_api_factory.constructs import FactoryStack
        >>> from aws_api_factory.config import load_config, resolve_config
        >>>
        >>> app = App()
        >>> config = load_config("factory.yaml")
        >>> resolved = resolve_config(config)
        >>> stack = FactoryStack(
        ...     app, "MyApiStack",
        ...     config=resolved,
        ...     environment="dev",
        ... )
        >>> app.synth()
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        config: FactoryConfig,
        environment: str,
        profile_defaults: ProfileDefaults | None = None,
        registry: ConstructRegistry | None = None,
        env: Environment | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the FactoryStack.

        Args:
            scope: The CDK app or construct scope.
            construct_id: The stack construct ID.
            config: The resolved factory configuration.
            environment: The deployment environment name (e.g., "dev", "prod").
            profile_defaults: Optional profile defaults. If not provided,
                            will be loaded based on config.profile.
            registry: Optional construct registry. If not provided, uses
                     the default registry.
            env: Optional CDK environment (account, region).
            **kwargs: Additional arguments passed to Stack.

        Raises:
            ValueError: If environment is not in config.project.envs.
        """
        # Validate environment
        if environment not in config.project.envs:
            raise ValueError(
                f"Environment '{environment}' not found in project.envs: "
                f"{config.project.envs}. Add it to factory.yaml or use a valid env."
            )

        # Generate stack name from project and environment
        stack_name = f"{config.project.name}-{environment}"

        super().__init__(
            scope,
            construct_id,
            stack_name=stack_name,
            description=f"AWS API Factory stack for {config.project.name} ({environment})",
            env=env,
            **kwargs,
        )

        self.config = config
        self.environment_name = environment

        # Load profile defaults if not provided
        if profile_defaults is None:
            from aws_api_factory.config.defaults import get_defaults

            profile_defaults = get_defaults(config.profile)
        self.profile_defaults = profile_defaults

        # Use provided registry or default
        # Note: Use 'is None' check since an empty registry is still valid
        self._registry = registry if registry is not None else get_default_registry()

        # Initialize output manager
        self.output_manager = OutputManager(
            stack=self,
            project_name=config.project.name,
            environment=environment,
        )

        # Apply global tags to all resources
        apply_global_tags(self, config, environment)

        # Add standard stack outputs
        self._add_standard_outputs()

        # Instantiate all enabled constructs
        self.constructs = self._registry.instantiate_all(
            scope=self,
            config=config,
            profile_defaults=self.profile_defaults,
            output_manager=self.output_manager,
            environment=environment,
        )

        # Export all outputs to CloudFormation
        self.output_manager.export_to_cfn()

    def _add_standard_outputs(self) -> None:
        """Add standard stack outputs (metadata, region, etc.)."""
        self.output_manager.add(
            key="StackName",
            value=self.stack_name,
            description="CloudFormation stack name",
            category="metadata",
        )
        self.output_manager.add(
            key="ProjectName",
            value=self.config.project.name,
            description="Project name",
            category="metadata",
        )
        self.output_manager.add(
            key="Environment",
            value=self.environment_name,
            description="Deployment environment",
            category="metadata",
        )
        self.output_manager.add(
            key="Profile",
            value=self.config.profile.value,
            description="Deployment profile (minimal/scalable)",
            category="metadata",
        )
        self.output_manager.add(
            key="Region",
            value=Aws.REGION,
            description="AWS region",
            category="metadata",
        )

    def get_construct(self, config_section: str) -> BaseConstruct | None:
        """Get an instantiated construct by config section.

        Args:
            config_section: The config section key (e.g., "apis.rest").

        Returns:
            The instantiated construct, or None if not found/enabled.
        """
        return self.constructs.get(config_section)

    def has_construct(self, config_section: str) -> bool:
        """Check if a construct was instantiated.

        Args:
            config_section: The config section key.

        Returns:
            True if the construct was created, False otherwise.
        """
        return config_section in self.constructs


def create_factory_stack(
    app: Construct,
    config: FactoryConfig,
    environment: str,
    *,
    stack_id: str | None = None,
    env: Environment | None = None,
) -> FactoryStack:
    """Convenience function to create a FactoryStack.

    This is a helper function that handles common setup for creating
    a FactoryStack, including resolving defaults if needed.

    Args:
        app: The CDK App.
        config: The factory configuration (resolved or unresolved).
        environment: The deployment environment name.
        stack_id: Optional stack ID. Defaults to "{project}-{env}-stack".
        env: Optional CDK environment (account, region).

    Returns:
        The created FactoryStack.

    Example:
        >>> from aws_cdk import App
        >>> from aws_api_factory.constructs import create_factory_stack
        >>> from aws_api_factory.config import load_config
        >>>
        >>> app = App()
        >>> config = load_config("factory.yaml")
        >>> stack = create_factory_stack(app, config, "dev")
        >>> app.synth()
    """
    # Resolve defaults if needed
    from aws_api_factory.config.resolver import resolve_config

    resolved_config = resolve_config(config)

    # Generate stack ID
    if stack_id is None:
        stack_id = f"{resolved_config.project.name.replace('-', '')}{environment.capitalize()}Stack"

    return FactoryStack(
        app,
        stack_id,
        config=resolved_config,
        environment=environment,
        env=env,
    )


# =============================================================================
# Register Core Constructs with Default Registry
# =============================================================================


def _register_core_constructs() -> None:
    """Register core factory constructs with the default registry.

    This function is called when the module is imported to register
    the built-in constructs. Users can register additional custom
    constructs using the register_construct() function.
    """
    from aws_api_factory.constructs.rest_api import RestLambdaConstruct

    # REST API + Lambda integration (creates both Lambda and API Gateway)
    # Priority 50 ensures it's created early for other constructs to reference
    if "apis.rest_lambda" not in _default_registry:
        _default_registry.register(
            RestLambdaConstruct,
            "apis.rest_lambda",
            enabled_check=lambda c: c.apis.rest.enabled and c.compute.lambda_.enabled,
            priority=50,
        )


# Register constructs when module is imported
_register_core_constructs()

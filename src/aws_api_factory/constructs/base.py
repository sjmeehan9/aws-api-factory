# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Base construct class for AWS API Factory.

This module provides the BaseConstruct abstract base class that all factory
constructs extend. It establishes common patterns for configuration validation,
resource naming, output registration, and tagging.

Example:
    >>> from aws_api_factory.constructs.base import BaseConstruct
    >>> class MyConstruct(BaseConstruct):
    ...     def _create_resources(self) -> None:
    ...         # Create AWS resources here
    ...         pass
    ...     def validate_config(self) -> list[str]:
    ...         # Return list of validation errors
    ...         return []

"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from aws_cdk import Tags
from aws_cdk import aws_iam as iam
from constructs import Construct

if TYPE_CHECKING:
    from aws_api_factory.config.defaults import ProfileDefaults
    from aws_api_factory.config.models import FactoryConfig
    from aws_api_factory.constructs.outputs import OutputManager


class BaseConstruct(Construct):
    """Abstract base class for all AWS API Factory constructs.

    This class provides common functionality for factory constructs including:
    - Configuration validation before resource creation
    - Consistent resource naming conventions
    - Output registration for stack outputs
    - Tagging of all resources
    - IAM policy management

    Subclasses must implement:
    - `_create_resources()`: Create the AWS CDK resources
    - `validate_config()`: Validate configuration and return errors

    Attributes:
        config: The complete factory configuration.
        profile_defaults: The resolved defaults for the user's profile.
        output_manager: The output manager for registering stack outputs.
        project_name: The project name from configuration.
        environment: The deployment environment name.

    Example:
        >>> class LambdaConstruct(BaseConstruct):
        ...     def _create_resources(self) -> None:
        ...         # Create Lambda functions
        ...         pass
        ...     def validate_config(self) -> list[str]:
        ...         errors = []
        ...         if not self.config.compute.lambda_.enabled:
        ...             errors.append("Lambda must be enabled")
        ...         return errors
    """

    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        config: FactoryConfig,
        profile_defaults: ProfileDefaults,
        output_manager: OutputManager,
        environment: str,
        **kwargs: Any,
    ) -> None:
        """Initialize the base construct.

        Args:
            scope: The CDK construct scope (parent).
            id: The construct ID, unique within the scope.
            config: The complete factory configuration.
            profile_defaults: The resolved defaults for the user's profile.
            output_manager: The output manager for registering outputs.
            environment: The deployment environment name (e.g., "dev", "prod").
            **kwargs: Additional keyword arguments passed to Construct.

        Raises:
            ValueError: If configuration validation fails.
        """
        super().__init__(scope, id, **kwargs)

        self.config = config
        self.profile_defaults = profile_defaults
        self.output_manager = output_manager
        self.project_name = config.project.name
        self.environment = environment

        # Validate configuration before creating resources
        validation_errors = self.validate_config()
        if validation_errors:
            raise ValueError(
                f"Configuration validation failed for {self.__class__.__name__}:\n"
                + "\n".join(f"  - {error}" for error in validation_errors)
            )

        # Create resources after validation
        self._create_resources()

    def _create_resources(self) -> None:
        """Create the AWS CDK resources for this construct.

        This method is called after configuration validation passes.
        Subclasses must implement this method to create their AWS resources.

        The method should:
        1. Create all necessary CDK constructs
        2. Register outputs via self.add_output()
        3. Store important resources as instance attributes for composition

        Raises:
            NotImplementedError: If subclass does not implement this method.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement _create_resources()"
        )

    def validate_config(self) -> list[str]:
        """Validate the configuration for this construct.

        Returns:
            A list of validation error messages. Empty list if valid.

        Raises:
            NotImplementedError: If subclass does not implement this method.

        Example:
            >>> def validate_config(self) -> list[str]:
            ...     errors = []
            ...     if not self.config.compute.lambda_.enabled:
            ...         errors.append("Lambda compute must be enabled")
            ...     return errors
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement validate_config()"
        )
        pass

    def generate_resource_name(
        self,
        resource_type: str,
        logical_name: str,
        *,
        max_length: int = 64,
        include_env: bool = True,
    ) -> str:
        """Generate a consistent resource name following AWS conventions.

        The naming convention is: {project}-{env}-{resource_type}-{logical_name}
        All parts are lowercased and sanitized for AWS naming rules.

        Args:
            resource_type: The type of resource (e.g., "lambda", "api", "table").
            logical_name: The logical name of the resource (e.g., "orders", "hello").
            max_length: Maximum length for the resource name (default: 64).
            include_env: Whether to include the environment in the name.

        Returns:
            A sanitized resource name following AWS naming conventions.

        Example:
            >>> name = self.generate_resource_name("lambda", "orders")
            >>> # Returns: "my-api-dev-lambda-orders"
        """
        if include_env:
            parts = [self.project_name, self.environment, resource_type, logical_name]
        else:
            parts = [self.project_name, resource_type, logical_name]

        # Join and sanitize
        name = "-".join(parts).lower()

        # Remove invalid characters (keep alphanumeric, hyphens, underscores)
        name = re.sub(r"[^a-z0-9_-]", "-", name)

        # Remove consecutive hyphens
        name = re.sub(r"-+", "-", name)

        # Trim to max length, ensuring we don't cut in the middle of a word
        if len(name) > max_length:
            name = name[:max_length].rsplit("-", 1)[0]

        # Remove leading/trailing hyphens
        name = name.strip("-")

        return name

    def generate_export_name(self, key: str) -> str:
        """Generate a CloudFormation export name.

        Export names must be unique within an AWS account/region. The format is:
        {project}-{env}-{key}

        Args:
            key: The export key (e.g., "ApiEndpoint", "LambdaArn").

        Returns:
            A sanitized export name.

        Example:
            >>> export = self.generate_export_name("ApiEndpoint")
            >>> # Returns: "my-api-dev-ApiEndpoint"
        """
        return f"{self.project_name}-{self.environment}-{key}"

    def add_output(
        self,
        key: str,
        value: str,
        description: str,
        *,
        export: bool = False,
    ) -> None:
        """Register an output to be included in stack outputs.

        Outputs are collected by the OutputManager and converted to
        CloudFormation CfnOutputs when the stack is synthesized.

        Args:
            key: The output key (e.g., "ApiEndpoint").
            value: The output value (e.g., the API URL).
            description: A human-readable description of the output.
            export: Whether to export the value for cross-stack references.

        Example:
            >>> self.add_output(
            ...     key="OrdersApiEndpoint",
            ...     value=api.url,
            ...     description="REST API endpoint for Orders service",
            ...     export=True,
            ... )
        """
        export_name = self.generate_export_name(key) if export else None
        self.output_manager.add(
            key=key,
            value=value,
            description=description,
            export_name=export_name,
        )

    def apply_tags(self, resource: Construct, **additional_tags: str) -> None:
        """Apply standard tags to a resource.

        Standard tags include:
        - Project: The project name
        - Environment: The deployment environment
        - ManagedBy: "aws-api-factory"
        - Profile: The deployment profile (minimal/scalable)

        Args:
            resource: The CDK construct to tag.
            **additional_tags: Additional tags to apply.

        Example:
            >>> self.apply_tags(lambda_function, Service="orders")
        """
        tags = {
            "Project": self.project_name,
            "Environment": self.environment,
            "ManagedBy": "aws-api-factory",
            "Profile": self.config.profile.value,
            **additional_tags,
        }
        for key, value in tags.items():
            Tags.of(resource).add(key, value)

    def create_service_role(
        self,
        role_id: str,
        assumed_by: iam.IPrincipal,
        description: str,
        *,
        managed_policies: list[iam.IManagedPolicy] | None = None,
        inline_policies: dict[str, iam.PolicyDocument] | None = None,
    ) -> iam.Role:
        """Create an IAM role with standard tags and naming.

        This is a helper method to create IAM roles with consistent naming
        and tagging conventions.

        Args:
            role_id: The construct ID for the role.
            assumed_by: The principal that can assume this role.
            description: A description of the role's purpose.
            managed_policies: Optional list of managed policies to attach.
            inline_policies: Optional dict of inline policies to attach.

        Returns:
            The created IAM Role.

        Example:
            >>> role = self.create_service_role(
            ...     "LambdaExecutionRole",
            ...     assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            ...     description="Execution role for Orders Lambda function",
            ... )
        """
        role = iam.Role(
            self,
            role_id,
            assumed_by=assumed_by,
            description=description,
            role_name=self.generate_resource_name("role", role_id.lower()),
            managed_policies=managed_policies or [],
            inline_policies=inline_policies or {},
        )
        self.apply_tags(role, RoleType=role_id)
        return role


def apply_global_tags(
    scope: Construct, config: FactoryConfig, environment: str
) -> None:
    """Apply global tags to all resources in a construct scope.

    This function uses CDK Aspects to apply tags to all resources
    created within the scope, ensuring consistent tagging across
    the entire stack.

    Args:
        scope: The CDK construct scope (usually the Stack).
        config: The factory configuration.
        environment: The deployment environment name.

    Example:
        >>> from aws_api_factory.constructs.base import apply_global_tags
        >>> apply_global_tags(stack, config, "dev")
    """
    tags = {
        "Project": config.project.name,
        "Environment": environment,
        "ManagedBy": "aws-api-factory",
        "Profile": config.profile.value,
    }
    for key, value in tags.items():
        Tags.of(scope).add(key, value)


def sanitize_resource_id(name: str, max_length: int = 64) -> str:
    """Sanitize a string for use as a CDK construct ID.

    CDK construct IDs should be alphanumeric with limited special characters.
    This function sanitizes arbitrary input to be safe for use as an ID.

    Args:
        name: The original name to sanitize.
        max_length: Maximum length for the resulting ID.

    Returns:
        A sanitized string safe for use as a construct ID.

    Example:
        >>> sanitize_resource_id("/orders/{id}")
        "OrdersId"
    """
    # Remove leading/trailing slashes and special chars
    name = name.strip("/")

    # Replace path parameters like {id} with just the param name
    name = re.sub(r"\{(\w+)\}", r"\1", name)

    # Split on non-alphanumeric, capitalize each part, and join
    parts = re.split(r"[^a-zA-Z0-9]+", name)
    result = "".join(part.capitalize() for part in parts if part)

    # Ensure it starts with a letter
    if result and not result[0].isalpha():
        result = "R" + result

    # Truncate if needed
    if len(result) > max_length:
        result = result[:max_length]

    return result or "Resource"

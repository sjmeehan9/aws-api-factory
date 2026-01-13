# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Lambda function construct for AWS API Factory.

This module implements the LambdaFunctionConstruct that creates Lambda
functions based on configuration, applying profile-specific defaults for
memory, timeout, logging, and tracing.

Example:
    >>> from aws_api_factory.constructs.compute_lambda import LambdaFunctionConstruct
    >>> construct = LambdaFunctionConstruct(
    ...     stack, "Lambdas",
    ...     config=config,
    ...     profile_defaults=defaults,
    ...     output_manager=outputs,
    ...     environment="dev",
    ... )
    >>> # Access created functions
    >>> hello_fn = construct.get_function("hello")

"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from aws_cdk import Duration, RemovalPolicy
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from constructs import Construct

from aws_api_factory.constructs.base import BaseConstruct

if TYPE_CHECKING:
    from aws_api_factory.config.defaults import ProfileDefaults
    from aws_api_factory.config.models import FactoryConfig, LambdaServiceConfig
    from aws_api_factory.constructs.outputs import OutputManager


class LambdaFunctionConstruct(BaseConstruct):
    """CDK construct for creating Lambda functions from configuration.

    This construct creates Lambda functions for each service defined in
    compute.lambda.services. It applies profile-based defaults and sets
    up proper IAM permissions, logging, and optional X-Ray tracing.

    Attributes:
        functions: Dictionary mapping service name to Lambda Function.

    Example:
        >>> construct = LambdaFunctionConstruct(
        ...     stack, "LambdaFunctions",
        ...     config=config,
        ...     profile_defaults=defaults,
        ...     output_manager=outputs,
        ...     environment="dev",
        ... )
        >>> orders_fn = construct.get_function("orders")
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
        code_path: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the Lambda function construct.

        Args:
            scope: The CDK construct scope.
            id: The construct ID.
            config: The factory configuration.
            profile_defaults: Profile defaults for Lambda settings.
            output_manager: Output manager for registering outputs.
            environment: Deployment environment name.
            code_path: Optional base path for Lambda code. Defaults to cwd.
            **kwargs: Additional arguments passed to BaseConstruct.
        """
        self._code_path = code_path or os.getcwd()
        self.functions: dict[str, lambda_.Function] = {}
        super().__init__(
            scope,
            id,
            config=config,
            profile_defaults=profile_defaults,
            output_manager=output_manager,
            environment=environment,
            **kwargs,
        )

    def validate_config(self) -> list[str]:
        """Validate Lambda configuration.

        Returns:
            List of validation error messages (empty if valid).
        """
        errors: list[str] = []

        if not self.config.compute.lambda_.enabled:
            errors.append("Lambda compute is not enabled in configuration")
            return errors

        services = self.config.compute.lambda_.services
        if not services:
            # Not an error - Lambda enabled but no services defined yet
            return errors

        for name, service_config in services.items():
            # Validate entry point format
            if ":" not in service_config.entry:
                errors.append(
                    f"Service '{name}': entry must be in format "
                    "'path/to/file.py:handler_function'"
                )
                continue

            file_path, handler_name = service_config.entry.rsplit(":", 1)
            if not file_path.endswith(".py"):
                errors.append(
                    f"Service '{name}': entry file must be a .py file, got '{file_path}'"
                )

            # Note: We don't validate file existence here as it may be in a different
            # directory during synthesis vs runtime

        return errors

    def _create_resources(self) -> None:
        """Create Lambda functions for all configured services."""
        if not self.config.compute.lambda_.enabled:
            return

        services = self.config.compute.lambda_.services
        for service_name, service_config in services.items():
            fn = self._create_function(service_name, service_config)
            self.functions[service_name] = fn

    def _create_function(
        self,
        service_name: str,
        service_config: LambdaServiceConfig,
    ) -> lambda_.Function:
        """Create a single Lambda function.

        Args:
            service_name: Name of the service (used for naming).
            service_config: Service configuration from factory.yaml.

        Returns:
            The created Lambda Function.
        """
        # Parse entry point
        file_path, handler_name = service_config.entry.rsplit(":", 1)

        # Determine the code directory (parent of the handler file)
        code_dir = str(Path(file_path).parent)
        handler_file = Path(file_path).stem  # e.g., "handler" from "handler.py"
        handler = f"{handler_file}.{handler_name}"  # e.g., "handler.handler"

        # Resolve memory and timeout from config or defaults
        memory_mb = self._resolve_memory(service_config)
        timeout_s = self._resolve_timeout(service_config)

        # Determine log retention based on profile
        log_retention = (
            logs.RetentionDays.ONE_WEEK
            if self.profile_defaults.observability.log_retention_days <= 7
            else logs.RetentionDays.ONE_MONTH
        )

        # Build resource name
        function_name = self.generate_resource_name("lambda", service_name)

        # Create execution role
        role = self._create_execution_role(service_name)

        # Determine tracing configuration
        tracing = (
            lambda_.Tracing.ACTIVE
            if self.profile_defaults.observability.tracing_enabled
            else lambda_.Tracing.DISABLED
        )

        # Build environment variables
        env_vars = {
            "ENVIRONMENT": self.environment,
            "PROJECT_NAME": self.project_name,
            "SERVICE_NAME": service_name,
            **service_config.environment,
        }

        # Create the Lambda function
        fn = lambda_.Function(
            self,
            f"Function{service_name.capitalize()}",
            function_name=function_name,
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler=handler,
            code=lambda_.Code.from_asset(
                os.path.join(self._code_path, code_dir),
            ),
            memory_size=memory_mb,
            timeout=Duration.seconds(timeout_s),
            role=role,
            tracing=tracing,
            environment=env_vars,
            log_retention=log_retention,
            description=f"AWS API Factory: {service_name} service ({self.environment})",
        )

        # Apply reserved concurrency if specified
        reserved = self._resolve_reserved_concurrency(service_config)
        if reserved is not None:
            fn.add_alias("live", provisioned_concurrent_executions=0)
            # Note: CDK doesn't have a direct property for reserved concurrency,
            # so we use the low-level CfnFunction escape hatch
            cfn_fn = fn.node.default_child
            if cfn_fn and hasattr(cfn_fn, "add_property_override"):
                cfn_fn.add_property_override("ReservedConcurrentExecutions", reserved)

        # Apply tags
        self.apply_tags(fn, Service=service_name)

        # Register outputs
        self.add_output(
            key=f"Lambda{service_name.capitalize()}Arn",
            value=fn.function_arn,
            description=f"ARN of the {service_name} Lambda function",
        )
        self.add_output(
            key=f"Lambda{service_name.capitalize()}Name",
            value=fn.function_name,
            description=f"Name of the {service_name} Lambda function",
        )

        return fn

    def _create_execution_role(self, service_name: str) -> iam.Role:
        """Create an execution role for a Lambda function.

        Args:
            service_name: Name of the service.

        Returns:
            IAM Role for Lambda execution.
        """
        role_name = self.generate_resource_name("role", f"{service_name}-exec")

        role = iam.Role(
            self,
            f"ExecutionRole{service_name.capitalize()}",
            role_name=role_name,
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description=f"Execution role for {service_name} Lambda function",
        )

        # Add basic Lambda execution permissions (CloudWatch Logs)
        role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaBasicExecutionRole"
            )
        )

        # Add X-Ray permissions if tracing is enabled
        if self.profile_defaults.observability.tracing_enabled:
            role.add_managed_policy(
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AWSXRayDaemonWriteAccess"
                )
            )

        self.apply_tags(role, Service=service_name, RoleType="LambdaExecution")

        return role

    def _resolve_memory(self, service_config: LambdaServiceConfig) -> int:
        """Resolve memory setting from config or defaults.

        Args:
            service_config: The service configuration.

        Returns:
            Memory in MB.
        """
        if service_config.memory_mb == "auto":
            return self.profile_defaults.lambda_.memory_mb
        return int(service_config.memory_mb)

    def _resolve_timeout(self, service_config: LambdaServiceConfig) -> int:
        """Resolve timeout setting from config or defaults.

        Args:
            service_config: The service configuration.

        Returns:
            Timeout in seconds.
        """
        if service_config.timeout_s == "auto":
            return self.profile_defaults.lambda_.timeout_s
        return int(service_config.timeout_s)

    def _resolve_reserved_concurrency(
        self, service_config: LambdaServiceConfig
    ) -> int | None:
        """Resolve reserved concurrency from config or defaults.

        Args:
            service_config: The service configuration.

        Returns:
            Reserved concurrency count or None.
        """
        if service_config.reserved_concurrency is not None:
            return service_config.reserved_concurrency
        return self.profile_defaults.lambda_.reserved_concurrency

    def get_function(self, service_name: str) -> lambda_.Function | None:
        """Get a Lambda function by service name.

        Args:
            service_name: The service name as defined in config.

        Returns:
            The Lambda Function or None if not found.
        """
        return self.functions.get(service_name)

    def get_all_functions(self) -> dict[str, lambda_.Function]:
        """Get all created Lambda functions.

        Returns:
            Dictionary mapping service name to Lambda Function.
        """
        return dict(self.functions)


def create_lambda_function(
    scope: Construct,
    id: str,
    *,
    config: FactoryConfig,
    profile_defaults: ProfileDefaults,
    output_manager: OutputManager,
    environment: str,
    code_path: str | None = None,
) -> LambdaFunctionConstruct:
    """Factory function to create a LambdaFunctionConstruct.

    Args:
        scope: The CDK construct scope.
        id: The construct ID.
        config: The factory configuration.
        profile_defaults: Profile defaults.
        output_manager: Output manager for registering outputs.
        environment: Deployment environment name.
        code_path: Optional base path for Lambda code.

    Returns:
        LambdaFunctionConstruct instance.
    """
    return LambdaFunctionConstruct(
        scope,
        id,
        config=config,
        profile_defaults=profile_defaults,
        output_manager=output_manager,
        environment=environment,
        code_path=code_path,
    )

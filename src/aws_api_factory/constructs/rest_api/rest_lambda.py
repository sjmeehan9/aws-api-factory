# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""REST Lambda integration construct for AWS API Factory.

This module provides a high-level construct that combines Lambda function
creation with REST API creation, handling the integration between them
automatically.

Example:
    >>> from aws_api_factory.constructs.rest_api import RestLambdaConstruct
    >>> construct = RestLambdaConstruct(
    ...     stack, "RestLambda",
    ...     config=config,
    ...     profile_defaults=defaults,
    ...     output_manager=outputs,
    ...     environment="dev",
    ... )

"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from aws_cdk import aws_lambda as lambda_
from constructs import Construct

from aws_api_factory.constructs.base import BaseConstruct
from aws_api_factory.constructs.compute_lambda import LambdaFunctionConstruct
from aws_api_factory.constructs.rest_api.api import RestApiConstruct

if TYPE_CHECKING:
    from aws_api_factory.config.defaults import ProfileDefaults
    from aws_api_factory.config.models import FactoryConfig
    from aws_api_factory.constructs.outputs import OutputManager


class RestLambdaConstruct(BaseConstruct):
    """Combined construct for REST API with Lambda backend.

    This construct creates both Lambda functions and a REST API,
    automatically wiring them together based on the route configuration.

    Attributes:
        lambda_construct: The LambdaFunctionConstruct with created functions.
        rest_api_construct: The RestApiConstruct with the API Gateway.
        functions: Shortcut to lambda_construct.functions.
        api: Shortcut to rest_api_construct.api.

    Example:
        >>> construct = RestLambdaConstruct(
        ...     stack, "RestLambda",
        ...     config=config,
        ...     profile_defaults=defaults,
        ...     output_manager=outputs,
        ...     environment="dev",
        ... )
        >>> print(construct.api.url)
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
        """Initialize the REST Lambda construct.

        Args:
            scope: The CDK construct scope.
            id: The construct ID.
            config: The factory configuration.
            profile_defaults: Profile defaults.
            output_manager: Output manager for registering outputs.
            environment: Deployment environment name.
            code_path: Optional base path for Lambda code.
            **kwargs: Additional arguments passed to BaseConstruct.
        """
        self._code_path = code_path or os.getcwd()
        self.lambda_construct: LambdaFunctionConstruct | None = None
        self.rest_api_construct: RestApiConstruct | None = None

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
        """Validate configuration for REST Lambda integration.

        Returns:
            List of validation error messages (empty if valid).
        """
        errors: list[str] = []

        # Check REST API is enabled
        if not self.config.apis.rest.enabled:
            return errors  # Not an error, just disabled

        # Check Lambda is enabled if routes reference Lambda services
        routes = self.config.apis.rest.routes
        if routes and not self.config.compute.lambda_.enabled:
            errors.append(
                "REST API routes are configured but Lambda compute is disabled. "
                "Enable Lambda in compute.lambda.enabled."
            )

        # Check that all route services have Lambda definitions
        services = self.config.compute.lambda_.services
        for route in routes:
            if route.service not in services:
                errors.append(
                    f"Route '{route.path}' references service '{route.service}' "
                    f"but no Lambda service with that name is defined in "
                    f"compute.lambda.services."
                )

        return errors

    def _create_resources(self) -> None:
        """Create Lambda functions and REST API."""
        # First create Lambda functions
        if self.config.compute.lambda_.enabled:
            self.lambda_construct = LambdaFunctionConstruct(
                self,
                "LambdaFunctions",
                config=self.config,
                profile_defaults=self.profile_defaults,
                output_manager=self.output_manager,
                environment=self.environment,
                code_path=self._code_path,
            )

        # Then create REST API with Lambda integrations
        if self.config.apis.rest.enabled:
            lambda_functions = (
                self.lambda_construct.functions if self.lambda_construct else {}
            )
            self.rest_api_construct = RestApiConstruct(
                self,
                "RestApi",
                config=self.config,
                profile_defaults=self.profile_defaults,
                output_manager=self.output_manager,
                environment=self.environment,
                lambda_functions=lambda_functions,
            )

    @property
    def functions(self) -> dict[str, lambda_.Function]:
        """Get all Lambda functions.

        Returns:
            Dictionary mapping service name to Lambda Function.
        """
        if self.lambda_construct:
            return self.lambda_construct.functions
        return {}

    @property
    def api(self):
        """Get the REST API.

        Returns:
            The RestApi or None if not created.
        """
        if self.rest_api_construct:
            return self.rest_api_construct.api
        return None

    def get_function(self, service_name: str) -> lambda_.Function | None:
        """Get a Lambda function by service name.

        Args:
            service_name: The service name.

        Returns:
            The Lambda Function or None.
        """
        if self.lambda_construct:
            return self.lambda_construct.get_function(service_name)
        return None

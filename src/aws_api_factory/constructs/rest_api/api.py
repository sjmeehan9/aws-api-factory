# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""REST API construct for AWS API Factory.

This module implements the RestApiConstruct that creates Amazon API Gateway
REST APIs with Lambda backend integrations based on configuration.

Example:
    >>> from aws_api_factory.constructs.rest_api import RestApiConstruct
    >>> construct = RestApiConstruct(
    ...     stack, "RestApi",
    ...     config=config,
    ...     profile_defaults=defaults,
    ...     output_manager=outputs,
    ...     environment="dev",
    ...     lambda_functions=lambdas.functions,
    ... )
    >>> # Access the API
    >>> api_url = construct.api.url

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from aws_cdk import Duration, RemovalPolicy
from aws_cdk import aws_apigateway as apigw
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from constructs import Construct

from aws_api_factory.constructs.base import BaseConstruct, sanitize_resource_id
from aws_api_factory.constructs.rest_api.lambda_integration import (
    create_lambda_integration,
)

if TYPE_CHECKING:
    from aws_api_factory.config.defaults import ProfileDefaults
    from aws_api_factory.config.models import FactoryConfig, RouteConfig
    from aws_api_factory.constructs.outputs import OutputManager


class RestApiConstruct(BaseConstruct):
    """CDK construct for creating API Gateway REST APIs.

    This construct creates an API Gateway REST API with routes and
    Lambda integrations as defined in the factory.yaml configuration.
    It applies profile-based defaults for logging, metrics, and throttling.

    Attributes:
        api: The API Gateway RestApi.
        resources: Dictionary mapping paths to API Gateway Resources.
        methods: Dictionary mapping "path:METHOD" to API Gateway Methods.

    Example:
        >>> construct = RestApiConstruct(
        ...     stack, "RestApi",
        ...     config=config,
        ...     profile_defaults=defaults,
        ...     output_manager=outputs,
        ...     environment="dev",
        ...     lambda_functions={"hello": hello_fn},
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
        lambda_functions: dict[str, lambda_.Function] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the REST API construct.

        Args:
            scope: The CDK construct scope.
            id: The construct ID.
            config: The factory configuration.
            profile_defaults: Profile defaults for API settings.
            output_manager: Output manager for registering outputs.
            environment: Deployment environment name.
            lambda_functions: Dictionary of Lambda functions by service name.
            **kwargs: Additional arguments passed to BaseConstruct.
        """
        self._lambda_functions = lambda_functions or {}
        self.api: apigw.RestApi | None = None
        self.resources: dict[str, apigw.IResource] = {}
        self.methods: dict[str, apigw.Method] = {}
        self._log_group: logs.LogGroup | None = None

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
        """Validate REST API configuration.

        Returns:
            List of validation error messages (empty if valid).
        """
        errors: list[str] = []

        rest_config = self.config.apis.rest
        if not rest_config.enabled:
            errors.append("REST API is not enabled in configuration")
            return errors

        # Validate each route
        for route in rest_config.routes:
            # Check that the service exists in lambda_functions if provided
            if self._lambda_functions and route.service not in self._lambda_functions:
                errors.append(
                    f"Route '{route.path}' references service '{route.service}' "
                    "which is not available in lambda_functions"
                )

            # Validate path format
            if not route.path.startswith("/"):
                errors.append(f"Route path must start with '/': {route.path}")

        return errors

    def _create_resources(self) -> None:
        """Create the REST API and all configured routes."""
        rest_config = self.config.apis.rest
        if not rest_config.enabled:
            return

        # Create the REST API
        self._create_api()

        # Create routes and integrations
        for route in rest_config.routes:
            self._create_route(route)

        # Register outputs
        self._register_outputs()

    def _create_api(self) -> None:
        """Create the API Gateway REST API with logging configuration."""
        rest_config = self.config.apis.rest
        api_name = self.generate_resource_name("api", "rest")

        # Determine logging level based on profile
        logging_level = (
            apigw.MethodLoggingLevel.INFO
            if self.profile_defaults.api_gateway.logging_level == "INFO"
            else apigw.MethodLoggingLevel.ERROR
        )

        # Determine log retention
        log_retention = (
            logs.RetentionDays.ONE_WEEK
            if self.profile_defaults.observability.log_retention_days <= 7
            else logs.RetentionDays.ONE_MONTH
        )

        # Create CloudWatch log group for access logs
        self._log_group = logs.LogGroup(
            self,
            "ApiAccessLogs",
            log_group_name=f"/aws/apigateway/{api_name}-access-logs",
            retention=log_retention,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Build deploy options
        deploy_options = apigw.StageOptions(
            stage_name=self.environment,
            logging_level=logging_level,
            data_trace_enabled=self.profile_defaults.api_gateway.metrics_enabled,
            metrics_enabled=self.profile_defaults.api_gateway.metrics_enabled,
            tracing_enabled=self.profile_defaults.api_gateway.tracing_enabled,
            access_log_destination=apigw.LogGroupLogDestination(self._log_group),
            access_log_format=apigw.AccessLogFormat.json_with_standard_fields(
                caller=True,
                http_method=True,
                ip=True,
                protocol=True,
                request_time=True,
                resource_path=True,
                response_length=True,
                status=True,
                user=True,
            ),
        )

        # Add throttling if configured
        if rest_config.throttle_rate or self.profile_defaults.api_gateway.throttle_rate:
            throttle_rate = (
                rest_config.throttle_rate
                or self.profile_defaults.api_gateway.throttle_rate
            )
            throttle_burst = (
                rest_config.throttle_burst
                or self.profile_defaults.api_gateway.throttle_burst
                or throttle_rate * 2
            )
            deploy_options = apigw.StageOptions(
                stage_name=self.environment,
                logging_level=logging_level,
                data_trace_enabled=self.profile_defaults.api_gateway.metrics_enabled,
                metrics_enabled=self.profile_defaults.api_gateway.metrics_enabled,
                tracing_enabled=self.profile_defaults.api_gateway.tracing_enabled,
                access_log_destination=apigw.LogGroupLogDestination(self._log_group),
                access_log_format=apigw.AccessLogFormat.json_with_standard_fields(
                    caller=True,
                    http_method=True,
                    ip=True,
                    protocol=True,
                    request_time=True,
                    resource_path=True,
                    response_length=True,
                    status=True,
                    user=True,
                ),
                throttling_rate_limit=throttle_rate,
                throttling_burst_limit=throttle_burst,
            )

        # Create the REST API
        self.api = apigw.RestApi(
            self,
            "Api",
            rest_api_name=api_name,
            description=f"AWS API Factory REST API for {self.project_name} ({self.environment})",
            deploy=True,
            deploy_options=deploy_options,
            endpoint_types=[apigw.EndpointType.REGIONAL],
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "Authorization", "X-Api-Key"],
            ),
        )

        # Apply tags
        self.apply_tags(self.api)
        self.apply_tags(self._log_group)

    def _create_route(self, route: RouteConfig) -> None:
        """Create an API Gateway resource and methods for a route.

        Args:
            route: The route configuration.
        """
        if not self.api:
            return

        # Get or create the resource for this path
        resource = self._get_or_create_resource(route.path)

        # Get the Lambda function for this route
        lambda_fn = self._lambda_functions.get(route.service)
        if not lambda_fn:
            # Skip if Lambda function not available (will be handled in full stack)
            return

        # Create integration
        integration = create_lambda_integration(lambda_fn)

        # Create methods for each HTTP method
        for method in route.methods:
            method_key = f"{route.path}:{method.value}"

            # Determine authorization type based on route auth config
            # Note: Full auth implementation is in Component 1.8
            auth_type = apigw.AuthorizationType.NONE
            if route.auth.value == "iam":
                auth_type = apigw.AuthorizationType.IAM
            elif route.auth.value == "api_key":
                # API key auth requires additional setup in Component 1.8
                auth_type = apigw.AuthorizationType.NONE

            api_method = resource.add_method(
                method.value,
                integration,
                authorization_type=auth_type,
                api_key_required=(route.auth.value == "api_key"),
            )

            self.methods[method_key] = api_method

    def _get_or_create_resource(self, path: str) -> apigw.IResource:
        """Get or create an API Gateway resource for a path.

        Handles nested paths like /orders/{orderId}/items by creating
        all intermediate resources.

        Args:
            path: The API path (e.g., "/orders/{orderId}").

        Returns:
            The API Gateway Resource for the path.
        """
        if not self.api:
            raise RuntimeError("API not initialized")

        # Check cache
        if path in self.resources:
            return self.resources[path]

        # Start from root
        current_resource: apigw.IResource = self.api.root

        # Split path and create/get each segment
        path = path.strip("/")
        if not path:
            return current_resource

        segments = path.split("/")
        current_path = ""

        for segment in segments:
            current_path = f"{current_path}/{segment}"

            if current_path in self.resources:
                current_resource = self.resources[current_path]
            else:
                # Create the resource
                resource_id = sanitize_resource_id(segment)
                current_resource = current_resource.add_resource(
                    segment,
                    default_cors_preflight_options=apigw.CorsOptions(
                        allow_origins=apigw.Cors.ALL_ORIGINS,
                        allow_methods=apigw.Cors.ALL_METHODS,
                    ),
                )
                self.resources[current_path] = current_resource

        return current_resource

    def _register_outputs(self) -> None:
        """Register API Gateway outputs."""
        if not self.api:
            return

        self.add_output(
            key="RestApiEndpoint",
            value=self.api.url,
            description="REST API endpoint URL",
            export=True,
        )
        self.add_output(
            key="RestApiId",
            value=self.api.rest_api_id,
            description="REST API ID",
        )
        self.add_output(
            key="RestApiStageName",
            value=self.environment,
            description="REST API stage name",
        )

    def get_api(self) -> apigw.RestApi | None:
        """Get the created REST API.

        Returns:
            The RestApi or None if not created.
        """
        return self.api

    def get_resource(self, path: str) -> apigw.IResource | None:
        """Get an API Gateway resource by path.

        Args:
            path: The API path.

        Returns:
            The Resource or None if not found.
        """
        return self.resources.get(path)

    def get_method(self, path: str, http_method: str) -> apigw.Method | None:
        """Get an API Gateway method by path and HTTP method.

        Args:
            path: The API path.
            http_method: The HTTP method (GET, POST, etc.).

        Returns:
            The Method or None if not found.
        """
        key = f"{path}:{http_method}"
        return self.methods.get(key)

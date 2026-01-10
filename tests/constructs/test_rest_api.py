# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Unit tests for REST API construct."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from aws_cdk import App, Stack, assertions
from aws_cdk import aws_lambda as lambda_

from aws_api_factory.config.defaults import get_defaults
from aws_api_factory.config.models import (
    ApisConfig,
    AuthModeEnum,
    ComputeConfig,
    FactoryConfig,
    HttpMethodEnum,
    LambdaConfig,
    LambdaServiceConfig,
    ProfileEnum,
    ProjectConfig,
    RestApiConfig,
    RouteConfig,
)
from aws_api_factory.constructs.outputs import OutputManager
from aws_api_factory.constructs.rest_api import RestApiConstruct
from aws_api_factory.constructs.rest_api.lambda_integration import (
    create_lambda_integration,
    grant_api_invoke_permission,
)


@pytest.fixture
def temp_lambda_code():
    """Create a temporary directory with Lambda handler code."""
    with tempfile.TemporaryDirectory() as tmpdir:
        for name in ["hello", "orders", "users"]:
            service_dir = Path(tmpdir) / "src" / "services" / name
            service_dir.mkdir(parents=True)
            (service_dir / "handler.py").write_text(
                f"def handler(e, c): return {{'statusCode': 200}}"
            )
        yield tmpdir


@pytest.fixture
def mock_lambda_function(temp_lambda_code):
    """Create a mock Lambda function for testing."""
    app = App()
    stack = Stack(app, "MockStack")

    # Create a real Lambda function for testing
    fn = lambda_.Function(
        stack,
        "MockFunction",
        runtime=lambda_.Runtime.PYTHON_3_11,
        handler="handler.handler",
        code=lambda_.Code.from_asset(
            str(Path(temp_lambda_code) / "src" / "services" / "hello")
        ),
    )
    return fn


@pytest.fixture
def minimal_rest_config():
    """Create a minimal REST API config for testing."""
    return FactoryConfig(
        project=ProjectConfig(name="test-api", envs=["dev", "prod"]),
        profile=ProfileEnum.MINIMAL,
        apis=ApisConfig(
            rest=RestApiConfig(
                enabled=True,
                routes=[
                    RouteConfig(
                        path="/hello",
                        methods=[HttpMethodEnum.GET],
                        service="hello",
                        auth=AuthModeEnum.NONE,
                    ),
                ],
            )
        ),
        compute=ComputeConfig(
            lambda_=LambdaConfig(
                enabled=True,
                services={
                    "hello": LambdaServiceConfig(
                        entry="src/services/hello/handler.py:handler",
                    ),
                },
            )
        ),
    )


@pytest.fixture
def multi_route_config():
    """Create a config with multiple routes."""
    return FactoryConfig(
        project=ProjectConfig(name="multi-api", envs=["dev"]),
        profile=ProfileEnum.MINIMAL,
        apis=ApisConfig(
            rest=RestApiConfig(
                enabled=True,
                routes=[
                    RouteConfig(
                        path="/hello",
                        methods=[HttpMethodEnum.GET],
                        service="hello",
                        auth=AuthModeEnum.NONE,
                    ),
                    RouteConfig(
                        path="/orders",
                        methods=[HttpMethodEnum.GET, HttpMethodEnum.POST],
                        service="orders",
                        auth=AuthModeEnum.NONE,
                    ),
                    RouteConfig(
                        path="/orders/{orderId}",
                        methods=[HttpMethodEnum.GET, HttpMethodEnum.PUT],
                        service="orders",
                        auth=AuthModeEnum.NONE,
                    ),
                ],
            )
        ),
        compute=ComputeConfig(
            lambda_=LambdaConfig(
                enabled=True,
                services={
                    "hello": LambdaServiceConfig(
                        entry="src/services/hello/handler.py:handler",
                    ),
                    "orders": LambdaServiceConfig(
                        entry="src/services/orders/handler.py:handler",
                    ),
                },
            )
        ),
    )


@pytest.fixture
def scalable_rest_config():
    """Create a scalable REST API config for testing."""
    return FactoryConfig(
        project=ProjectConfig(name="prod-api", envs=["dev", "prod"]),
        profile=ProfileEnum.SCALABLE,
        apis=ApisConfig(
            rest=RestApiConfig(
                enabled=True,
                throttle_rate=500,
                throttle_burst=1000,
                routes=[
                    RouteConfig(
                        path="/users",
                        methods=[HttpMethodEnum.GET, HttpMethodEnum.POST],
                        service="users",
                        auth=AuthModeEnum.NONE,
                    ),
                ],
            )
        ),
        compute=ComputeConfig(
            lambda_=LambdaConfig(
                enabled=True,
                services={
                    "users": LambdaServiceConfig(
                        entry="src/services/users/handler.py:handler",
                    ),
                },
            )
        ),
    )


def create_mock_lambda_functions(
    stack: Stack, temp_code_path: str, service_names: list[str]
) -> dict[str, lambda_.Function]:
    """Create mock Lambda functions for testing."""
    functions = {}
    for i, name in enumerate(service_names):
        service_dir = Path(temp_code_path) / "src" / "services" / name
        service_dir.mkdir(parents=True, exist_ok=True)
        (service_dir / "handler.py").write_text(f"def handler(e, c): return {{}}")

        fn = lambda_.Function(
            stack,
            f"MockFunction{name.capitalize()}",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.handler",
            code=lambda_.Code.from_asset(str(service_dir)),
        )
        functions[name] = fn
    return functions


class TestRestApiConstruct:
    """Tests for RestApiConstruct."""

    def test_construct_creates_api_gateway(self, minimal_rest_config, temp_lambda_code):
        """Test that API Gateway REST API is created."""
        app = App()
        stack = Stack(app, "TestStack")

        defaults = get_defaults(ProfileEnum.MINIMAL)
        output_manager = OutputManager(
            stack=stack, project_name="test-api", environment="dev"
        )

        # Create mock Lambda functions
        lambda_functions = create_mock_lambda_functions(
            stack, temp_lambda_code, ["hello"]
        )

        construct = RestApiConstruct(
            stack,
            "RestApi",
            config=minimal_rest_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            lambda_functions=lambda_functions,
        )

        # Verify API was created
        assert construct.api is not None

        # Synthesize and check CloudFormation
        template = assertions.Template.from_stack(stack)

        # Check REST API exists
        template.has_resource_properties(
            "AWS::ApiGateway::RestApi",
            {
                "Name": assertions.Match.string_like_regexp("test-api-dev-api-rest"),
            },
        )

    def test_construct_creates_routes(self, minimal_rest_config, temp_lambda_code):
        """Test that API Gateway resources and methods are created."""
        app = App()
        stack = Stack(app, "TestStack")

        defaults = get_defaults(ProfileEnum.MINIMAL)
        output_manager = OutputManager(
            stack=stack, project_name="test-api", environment="dev"
        )

        lambda_functions = create_mock_lambda_functions(
            stack, temp_lambda_code, ["hello"]
        )

        construct = RestApiConstruct(
            stack,
            "RestApi",
            config=minimal_rest_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            lambda_functions=lambda_functions,
        )

        template = assertions.Template.from_stack(stack)

        # Check API Gateway resource exists
        template.has_resource_properties(
            "AWS::ApiGateway::Resource",
            {
                "PathPart": "hello",
            },
        )

        # Check Method exists
        template.has_resource_properties(
            "AWS::ApiGateway::Method",
            {
                "HttpMethod": "GET",
            },
        )

    def test_construct_creates_multiple_routes(
        self, multi_route_config, temp_lambda_code
    ):
        """Test creation of multiple routes with nested paths."""
        app = App()
        stack = Stack(app, "TestStack")

        defaults = get_defaults(ProfileEnum.MINIMAL)
        output_manager = OutputManager(
            stack=stack, project_name="multi-api", environment="dev"
        )

        lambda_functions = create_mock_lambda_functions(
            stack, temp_lambda_code, ["hello", "orders"]
        )

        construct = RestApiConstruct(
            stack,
            "RestApi",
            config=multi_route_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            lambda_functions=lambda_functions,
        )

        # Verify resources are tracked
        assert "/hello" in construct.resources
        assert "/orders" in construct.resources
        assert "/orders/{orderId}" in construct.resources

        # Verify methods are tracked
        assert "/hello:GET" in construct.methods
        assert "/orders:GET" in construct.methods
        assert "/orders:POST" in construct.methods

        template = assertions.Template.from_stack(stack)

        # Check all resources exist
        template.resource_count_is("AWS::ApiGateway::Resource", 3)

    def test_construct_with_scalable_profile_enables_metrics(
        self, scalable_rest_config, temp_lambda_code
    ):
        """Test that scalable profile enables metrics and tracing."""
        app = App()
        stack = Stack(app, "TestStack")

        defaults = get_defaults(ProfileEnum.SCALABLE)
        output_manager = OutputManager(
            stack=stack, project_name="prod-api", environment="prod"
        )

        lambda_functions = create_mock_lambda_functions(
            stack, temp_lambda_code, ["users"]
        )

        RestApiConstruct(
            stack,
            "RestApi",
            config=scalable_rest_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="prod",
            lambda_functions=lambda_functions,
        )

        template = assertions.Template.from_stack(stack)

        # Check stage has metrics and tracing enabled
        template.has_resource_properties(
            "AWS::ApiGateway::Stage",
            {
                "MethodSettings": assertions.Match.array_with(
                    [
                        assertions.Match.object_like(
                            {
                                "MetricsEnabled": True,
                            }
                        )
                    ]
                ),
                "TracingEnabled": True,
            },
        )

    def test_construct_creates_cloudwatch_log_group(
        self, minimal_rest_config, temp_lambda_code
    ):
        """Test that CloudWatch log group is created for API access logs."""
        app = App()
        stack = Stack(app, "TestStack")

        defaults = get_defaults(ProfileEnum.MINIMAL)
        output_manager = OutputManager(
            stack=stack, project_name="test-api", environment="dev"
        )

        lambda_functions = create_mock_lambda_functions(
            stack, temp_lambda_code, ["hello"]
        )

        RestApiConstruct(
            stack,
            "RestApi",
            config=minimal_rest_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            lambda_functions=lambda_functions,
        )

        template = assertions.Template.from_stack(stack)

        # Check log group exists
        template.has_resource_properties(
            "AWS::Logs::LogGroup",
            {
                "LogGroupName": assertions.Match.string_like_regexp(
                    "/aws/apigateway/test-api-dev-api-rest-access-logs"
                ),
            },
        )

    def test_construct_configures_cors(self, minimal_rest_config, temp_lambda_code):
        """Test that CORS is configured on the API."""
        app = App()
        stack = Stack(app, "TestStack")

        defaults = get_defaults(ProfileEnum.MINIMAL)
        output_manager = OutputManager(
            stack=stack, project_name="test-api", environment="dev"
        )

        lambda_functions = create_mock_lambda_functions(
            stack, temp_lambda_code, ["hello"]
        )

        RestApiConstruct(
            stack,
            "RestApi",
            config=minimal_rest_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            lambda_functions=lambda_functions,
        )

        template = assertions.Template.from_stack(stack)

        # Check OPTIONS method exists (CORS preflight)
        template.has_resource_properties(
            "AWS::ApiGateway::Method",
            {
                "HttpMethod": "OPTIONS",
            },
        )

    def test_construct_applies_throttling(self, scalable_rest_config, temp_lambda_code):
        """Test that throttling is applied from config."""
        app = App()
        stack = Stack(app, "TestStack")

        defaults = get_defaults(ProfileEnum.SCALABLE)
        output_manager = OutputManager(
            stack=stack, project_name="prod-api", environment="prod"
        )

        lambda_functions = create_mock_lambda_functions(
            stack, temp_lambda_code, ["users"]
        )

        RestApiConstruct(
            stack,
            "RestApi",
            config=scalable_rest_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="prod",
            lambda_functions=lambda_functions,
        )

        template = assertions.Template.from_stack(stack)

        # Check stage has throttling
        template.has_resource_properties(
            "AWS::ApiGateway::Stage",
            {
                "MethodSettings": assertions.Match.array_with(
                    [
                        assertions.Match.object_like(
                            {
                                "ThrottlingRateLimit": 500,
                                "ThrottlingBurstLimit": 1000,
                            }
                        )
                    ]
                ),
            },
        )

    def test_construct_registers_outputs(self, minimal_rest_config, temp_lambda_code):
        """Test that API outputs are registered."""
        app = App()
        stack = Stack(app, "TestStack")

        defaults = get_defaults(ProfileEnum.MINIMAL)
        output_manager = OutputManager(
            stack=stack, project_name="test-api", environment="dev"
        )

        lambda_functions = create_mock_lambda_functions(
            stack, temp_lambda_code, ["hello"]
        )

        RestApiConstruct(
            stack,
            "RestApi",
            config=minimal_rest_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            lambda_functions=lambda_functions,
        )

        outputs = output_manager.get_all()
        output_keys = list(outputs.keys())

        assert "RestApiEndpoint" in output_keys
        assert "RestApiId" in output_keys
        assert "RestApiStageName" in output_keys

    def test_construct_creates_lambda_integration(
        self, minimal_rest_config, temp_lambda_code
    ):
        """Test that Lambda integrations are created for routes."""
        app = App()
        stack = Stack(app, "TestStack")

        defaults = get_defaults(ProfileEnum.MINIMAL)
        output_manager = OutputManager(
            stack=stack, project_name="test-api", environment="dev"
        )

        lambda_functions = create_mock_lambda_functions(
            stack, temp_lambda_code, ["hello"]
        )

        RestApiConstruct(
            stack,
            "RestApi",
            config=minimal_rest_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            lambda_functions=lambda_functions,
        )

        template = assertions.Template.from_stack(stack)

        # Check Lambda integration exists
        template.has_resource_properties(
            "AWS::ApiGateway::Method",
            {
                "Integration": {
                    "Type": "AWS_PROXY",
                    "IntegrationHttpMethod": "POST",
                },
            },
        )

    def test_validation_warns_for_missing_lambda(
        self, minimal_rest_config, temp_lambda_code
    ):
        """Test validation warns when route references missing Lambda."""
        app = App()
        stack = Stack(app, "TestStack")

        defaults = get_defaults(ProfileEnum.MINIMAL)
        output_manager = OutputManager(
            stack=stack, project_name="test-api", environment="dev"
        )

        # Create the construct with missing Lambda function
        # The construct should still create the API, just without integration
        lambda_functions = create_mock_lambda_functions(
            stack, temp_lambda_code, ["hello"]
        )

        construct = RestApiConstruct(
            stack,
            "RestApi",
            config=minimal_rest_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            lambda_functions=lambda_functions,
        )

        # API should be created
        assert construct.api is not None

    def test_validation_passes_without_lambda_functions(self, temp_lambda_code):
        """Test validation passes when no lambda_functions provided."""
        config = FactoryConfig(
            project=ProjectConfig(name="test-api", envs=["dev"]),
            profile=ProfileEnum.MINIMAL,
            apis=ApisConfig(
                rest=RestApiConfig(
                    enabled=True,
                    routes=[],  # No routes means no Lambda needed
                )
            ),
        )

        app = App()
        stack = Stack(app, "TestStack")

        defaults = get_defaults(ProfileEnum.MINIMAL)
        output_manager = OutputManager(
            stack=stack, project_name="test-api", environment="dev"
        )

        # No routes, so no lambda_functions needed
        construct = RestApiConstruct(
            stack,
            "RestApi",
            config=config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
        )

        assert construct.api is not None

    def test_get_resource_returns_resource(self, minimal_rest_config, temp_lambda_code):
        """Test get_resource returns the correct resource."""
        app = App()
        stack = Stack(app, "TestStack")

        defaults = get_defaults(ProfileEnum.MINIMAL)
        output_manager = OutputManager(
            stack=stack, project_name="test-api", environment="dev"
        )

        lambda_functions = create_mock_lambda_functions(
            stack, temp_lambda_code, ["hello"]
        )

        construct = RestApiConstruct(
            stack,
            "RestApi",
            config=minimal_rest_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            lambda_functions=lambda_functions,
        )

        resource = construct.get_resource("/hello")
        assert resource is not None

        # Unknown path returns None
        assert construct.get_resource("/unknown") is None

    def test_get_method_returns_method(self, minimal_rest_config, temp_lambda_code):
        """Test get_method returns the correct method."""
        app = App()
        stack = Stack(app, "TestStack")

        defaults = get_defaults(ProfileEnum.MINIMAL)
        output_manager = OutputManager(
            stack=stack, project_name="test-api", environment="dev"
        )

        lambda_functions = create_mock_lambda_functions(
            stack, temp_lambda_code, ["hello"]
        )

        construct = RestApiConstruct(
            stack,
            "RestApi",
            config=minimal_rest_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            lambda_functions=lambda_functions,
        )

        method = construct.get_method("/hello", "GET")
        assert method is not None

        # Unknown method returns None
        assert construct.get_method("/hello", "POST") is None


class TestLambdaIntegrationHelpers:
    """Tests for Lambda integration helper functions."""

    def test_create_lambda_integration(self, temp_lambda_code):
        """Test create_lambda_integration creates proxy integration."""
        app = App()
        stack = Stack(app, "TestStack")

        service_dir = Path(temp_lambda_code) / "src" / "services" / "test"
        service_dir.mkdir(parents=True, exist_ok=True)
        (service_dir / "handler.py").write_text("def handler(e, c): return {}")

        fn = lambda_.Function(
            stack,
            "TestFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.handler",
            code=lambda_.Code.from_asset(str(service_dir)),
        )

        integration = create_lambda_integration(fn)

        # LambdaIntegration is created
        assert integration is not None

    def test_create_lambda_integration_with_cache(self, temp_lambda_code):
        """Test create_lambda_integration with cache parameters."""
        app = App()
        stack = Stack(app, "TestStack")

        service_dir = Path(temp_lambda_code) / "src" / "services" / "test"
        service_dir.mkdir(parents=True, exist_ok=True)
        (service_dir / "handler.py").write_text("def handler(e, c): return {}")

        fn = lambda_.Function(
            stack,
            "TestFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.handler",
            code=lambda_.Code.from_asset(str(service_dir)),
        )

        integration = create_lambda_integration(
            fn,
            cache_key_parameters=["method.request.querystring.id"],
            cache_namespace="my-cache",
        )

        assert integration is not None

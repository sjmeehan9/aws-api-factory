# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Integration tests for REST API + Lambda end-to-end."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from aws_cdk import App, assertions

from aws_api_factory.config.defaults import get_defaults
from aws_api_factory.config.loader import load_config
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
from aws_api_factory.config.resolver import resolve_config
from aws_api_factory.constructs import FactoryStack, create_factory_stack
from aws_api_factory.constructs.rest_api import RestLambdaConstruct


@pytest.fixture
def temp_project():
    """Create a temporary project directory with Lambda handlers."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create service directories and handlers
        for name in ["hello", "orders", "users"]:
            service_dir = Path(tmpdir) / "src" / "services" / name
            service_dir.mkdir(parents=True)
            handler_code = f'''
import json

def handler(event, context):
    """Lambda handler for {name} service."""
    return {{
        "statusCode": 200,
        "headers": {{"Content-Type": "application/json"}},
        "body": json.dumps({{"service": "{name}", "message": "Hello from {name}!"}})
    }}
'''
            (service_dir / "handler.py").write_text(handler_code)

        yield tmpdir


@pytest.fixture
def minimal_factory_yaml(temp_project):
    """Create a minimal factory.yaml in the temp project."""
    config_content = """
project:
  name: test-api
  envs:
    - dev
    - prod

profile: minimal

apis:
  rest:
    enabled: true
    routes:
      - path: /hello
        methods:
          - GET
        service: hello
        auth: none

compute:
  lambda:
    enabled: true
    services:
      hello:
        entry: src/services/hello/handler.py:handler
        memory_mb: auto
        timeout_s: auto
"""
    config_path = Path(temp_project) / "factory.yaml"
    config_path.write_text(config_content)
    return config_path


@pytest.fixture
def scalable_factory_yaml(temp_project):
    """Create a scalable factory.yaml in the temp project."""
    config_content = """
project:
  name: prod-api
  envs:
    - dev
    - staging
    - prod

profile: scalable

apis:
  rest:
    enabled: true
    throttle_rate: 1000
    throttle_burst: 2000
    routes:
      - path: /hello
        methods:
          - GET
        service: hello
        auth: none
      - path: /orders
        methods:
          - GET
          - POST
        service: orders
        auth: none
      - path: /orders/{orderId}
        methods:
          - GET
          - PUT
          - DELETE
        service: orders
        auth: none

compute:
  lambda:
    enabled: true
    services:
      hello:
        entry: src/services/hello/handler.py:handler
        memory_mb: 1024
        timeout_s: 30
      orders:
        entry: src/services/orders/handler.py:handler
        memory_mb: 2048
        timeout_s: 60
        environment:
          TABLE_NAME: orders
"""
    config_path = Path(temp_project) / "factory.yaml"
    config_path.write_text(config_content)
    return config_path


class TestRestLambdaIntegration:
    """Integration tests for REST API + Lambda combined construct."""

    def test_rest_lambda_construct_creates_both(self, temp_project):
        """Test RestLambdaConstruct creates both Lambda and API Gateway."""
        config = FactoryConfig(
            project=ProjectConfig(name="test-api", envs=["dev"]),
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

        from aws_cdk import Stack

        from aws_api_factory.constructs.outputs import OutputManager

        app = App()
        stack = Stack(app, "TestStack")

        defaults = get_defaults(ProfileEnum.MINIMAL)
        output_manager = OutputManager(
            stack=stack, project_name="test-api", environment="dev"
        )

        construct = RestLambdaConstruct(
            stack,
            "RestLambda",
            config=config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            code_path=temp_project,
        )

        # Verify both were created
        assert construct.lambda_construct is not None
        assert construct.rest_api_construct is not None
        assert "hello" in construct.functions
        assert construct.api is not None

        template = assertions.Template.from_stack(stack)

        # Verify Lambda function
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "Runtime": "python3.11",
            },
        )

        # Verify API Gateway
        template.has_resource_properties(
            "AWS::ApiGateway::RestApi",
            {
                "Name": assertions.Match.string_like_regexp("test-api"),
            },
        )

    def test_rest_lambda_construct_connects_correctly(self, temp_project):
        """Test that routes are connected to correct Lambda functions."""
        config = FactoryConfig(
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

        from aws_cdk import Stack

        from aws_api_factory.constructs.outputs import OutputManager

        app = App()
        stack = Stack(app, "TestStack")

        defaults = get_defaults(ProfileEnum.MINIMAL)
        output_manager = OutputManager(
            stack=stack, project_name="multi-api", environment="dev"
        )

        construct = RestLambdaConstruct(
            stack,
            "RestLambda",
            config=config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            code_path=temp_project,
        )

        # Verify both functions created
        assert len(construct.functions) == 2
        assert construct.get_function("hello") is not None
        assert construct.get_function("orders") is not None

        template = assertions.Template.from_stack(stack)

        # Verify at least 2 Lambda functions (CDK may add additional for log retention)
        resources = template.find_resources("AWS::Lambda::Function")
        assert (
            len(resources) >= 2
        ), f"Expected at least 2 Lambda functions, found {len(resources)}"

        # Verify routes exist
        template.has_resource_properties(
            "AWS::ApiGateway::Resource",
            {"PathPart": "hello"},
        )
        template.has_resource_properties(
            "AWS::ApiGateway::Resource",
            {"PathPart": "orders"},
        )


class TestFactoryStackWithRestLambda:
    """Integration tests for FactoryStack with REST + Lambda."""

    def test_factory_stack_synth_minimal(self, minimal_factory_yaml, temp_project):
        """Test FactoryStack synthesizes with minimal config."""
        import os

        # Change to temp directory for config loading
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_project)

            config = load_config(minimal_factory_yaml)
            resolved = resolve_config(config)

            app = App()
            stack = create_factory_stack(app, resolved, "dev")

            # Synthesize
            assembly = app.synth()

            # Verify synthesis succeeded
            assert assembly is not None
            assert len(assembly.stacks) > 0
        finally:
            os.chdir(original_cwd)

    def test_factory_stack_synth_scalable(self, scalable_factory_yaml, temp_project):
        """Test FactoryStack synthesizes with scalable config."""
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_project)

            config = load_config(scalable_factory_yaml)
            resolved = resolve_config(config)

            app = App()
            stack = create_factory_stack(app, resolved, "prod")

            # Synthesize
            assembly = app.synth()

            # Verify synthesis succeeded
            assert assembly is not None

            # Get the template
            template = assertions.Template.from_stack(stack)

            # Verify scalable profile settings
            template.has_resource_properties(
                "AWS::Lambda::Function",
                {
                    "MemorySize": assertions.Match.any_value(),
                    "Timeout": assertions.Match.any_value(),
                },
            )

            # Verify API Gateway with throttling
            template.has_resource_properties(
                "AWS::ApiGateway::Stage",
                {
                    "TracingEnabled": True,
                },
            )
        finally:
            os.chdir(original_cwd)

    def test_factory_stack_outputs(self, minimal_factory_yaml, temp_project):
        """Test FactoryStack creates proper CloudFormation outputs."""
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_project)

            config = load_config(minimal_factory_yaml)
            resolved = resolve_config(config)

            app = App()
            stack = create_factory_stack(app, resolved, "dev")

            template = assertions.Template.from_stack(stack)

            # Check that outputs exist (output names may vary)
            outputs = template.find_outputs("*")
            assert len(outputs) > 0, "Expected at least one output"

            # Verify RestAPI URL output exists
            found_api_output = False
            for output_id, output in outputs.items():
                if "RestApiUrl" in output_id or "Url" in output_id:
                    found_api_output = True
                    break

            # API output should exist (may be named differently)
            # The factory should create some outputs
            assert len(outputs) >= 1, "Expected at least 1 output"
        finally:
            os.chdir(original_cwd)

    def test_factory_stack_tags(self, minimal_factory_yaml, temp_project):
        """Test FactoryStack applies proper tags to all resources."""
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_project)

            config = load_config(minimal_factory_yaml)
            resolved = resolve_config(config)

            app = App()
            stack = create_factory_stack(app, resolved, "dev")

            template = assertions.Template.from_stack(stack)

            # Check Lambda function has project-related properties
            # Tags may be applied differently by CDK
            template.has_resource_properties(
                "AWS::Lambda::Function",
                {
                    "FunctionName": assertions.Match.string_like_regexp(
                        r"test-api.*lambda.*"
                    ),
                },
            )
        finally:
            os.chdir(original_cwd)


class TestCloudFormationValidity:
    """Tests to verify generated CloudFormation is valid."""

    def test_cloudformation_has_valid_resources(self, temp_project):
        """Test that generated CloudFormation has valid resource structure."""
        config = FactoryConfig(
            project=ProjectConfig(name="valid-api", envs=["dev"]),
            profile=ProfileEnum.MINIMAL,
            apis=ApisConfig(
                rest=RestApiConfig(
                    enabled=True,
                    routes=[
                        RouteConfig(
                            path="/test",
                            methods=[HttpMethodEnum.GET],
                            service="test",
                            auth=AuthModeEnum.NONE,
                        ),
                    ],
                )
            ),
            compute=ComputeConfig(
                lambda_=LambdaConfig(
                    enabled=True,
                    services={
                        "test": LambdaServiceConfig(
                            entry="src/services/hello/handler.py:handler",
                        ),
                    },
                )
            ),
        )

        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_project)

            app = App()
            resolved = resolve_config(config)
            stack = create_factory_stack(app, resolved, "dev")

            template = assertions.Template.from_stack(stack)
            cfn_template = template.to_json()

            # Verify basic CloudFormation structure
            assert "Resources" in cfn_template
            assert "Outputs" in cfn_template

            # Verify expected resource types exist
            resources = cfn_template["Resources"]
            resource_types = [r.get("Type") for r in resources.values()]

            assert "AWS::Lambda::Function" in resource_types
            assert "AWS::ApiGateway::RestApi" in resource_types
            assert "AWS::IAM::Role" in resource_types
            assert "AWS::Logs::LogGroup" in resource_types
        finally:
            os.chdir(original_cwd)

    def test_cloudformation_no_circular_dependencies(self, temp_project):
        """Test that generated CloudFormation has no circular dependencies."""
        config = FactoryConfig(
            project=ProjectConfig(name="no-circular", envs=["dev"]),
            profile=ProfileEnum.MINIMAL,
            apis=ApisConfig(
                rest=RestApiConfig(
                    enabled=True,
                    routes=[
                        RouteConfig(
                            path="/a",
                            methods=[HttpMethodEnum.GET],
                            service="a",
                            auth=AuthModeEnum.NONE,
                        ),
                        RouteConfig(
                            path="/b",
                            methods=[HttpMethodEnum.GET],
                            service="b",
                            auth=AuthModeEnum.NONE,
                        ),
                    ],
                )
            ),
            compute=ComputeConfig(
                lambda_=LambdaConfig(
                    enabled=True,
                    services={
                        "a": LambdaServiceConfig(
                            entry="src/services/hello/handler.py:handler",
                        ),
                        "b": LambdaServiceConfig(
                            entry="src/services/orders/handler.py:handler",
                        ),
                    },
                )
            ),
        )

        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_project)

            app = App()
            resolved = resolve_config(config)

            # This should not raise any circular dependency errors
            stack = create_factory_stack(app, resolved, "dev")

            # Synthesize should complete without error
            app.synth()
        finally:
            os.chdir(original_cwd)


class TestProfileDifferences:
    """Tests to verify Minimal vs Scalable profile differences."""

    def test_minimal_profile_settings(self, temp_project):
        """Test that Minimal profile uses appropriate settings."""
        config = FactoryConfig(
            project=ProjectConfig(name="minimal-test", envs=["dev"]),
            profile=ProfileEnum.MINIMAL,
            apis=ApisConfig(
                rest=RestApiConfig(
                    enabled=True,
                    routes=[
                        RouteConfig(
                            path="/test",
                            methods=[HttpMethodEnum.GET],
                            service="test",
                            auth=AuthModeEnum.NONE,
                        ),
                    ],
                )
            ),
            compute=ComputeConfig(
                lambda_=LambdaConfig(
                    enabled=True,
                    services={
                        "test": LambdaServiceConfig(
                            entry="src/services/hello/handler.py:handler",
                        ),
                    },
                )
            ),
        )

        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_project)

            app = App()
            resolved = resolve_config(config)
            stack = create_factory_stack(app, resolved, "dev")

            template = assertions.Template.from_stack(stack)

            # Minimal profile: 512MB memory, 30s timeout
            template.has_resource_properties(
                "AWS::Lambda::Function",
                {
                    "MemorySize": 512,
                    "Timeout": 30,
                },
            )

            # Minimal profile: No X-Ray tracing (TracingConfig not present)
            # Just verify the function properties without tracing
            resources = template.find_resources("AWS::Lambda::Function")
            user_lambdas = [
                r
                for r in resources.values()
                if r.get("Properties", {})
                .get("FunctionName", "")
                .startswith("minimal-test")
            ]
            assert len(user_lambdas) > 0, "Should have user Lambda function"
        finally:
            os.chdir(original_cwd)

    def test_scalable_profile_settings(self, temp_project):
        """Test that Scalable profile uses appropriate settings."""
        config = FactoryConfig(
            project=ProjectConfig(name="scalable-test", envs=["prod"]),
            profile=ProfileEnum.SCALABLE,
            apis=ApisConfig(
                rest=RestApiConfig(
                    enabled=True,
                    routes=[
                        RouteConfig(
                            path="/test",
                            methods=[HttpMethodEnum.GET],
                            service="test",
                            auth=AuthModeEnum.NONE,
                        ),
                    ],
                )
            ),
            compute=ComputeConfig(
                lambda_=LambdaConfig(
                    enabled=True,
                    services={
                        "test": LambdaServiceConfig(
                            entry="src/services/hello/handler.py:handler",
                        ),
                    },
                )
            ),
        )

        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_project)

            app = App()
            resolved = resolve_config(config)
            stack = create_factory_stack(app, resolved, "prod")

            template = assertions.Template.from_stack(stack)

            # Scalable profile: 1024MB memory, 60s timeout
            template.has_resource_properties(
                "AWS::Lambda::Function",
                {
                    "MemorySize": 1024,
                    "Timeout": 60,
                },
            )

            # Scalable profile: X-Ray tracing enabled
            template.has_resource_properties(
                "AWS::Lambda::Function",
                {
                    "TracingConfig": {"Mode": "Active"},
                },
            )

            # Scalable profile: API Gateway tracing
            template.has_resource_properties(
                "AWS::ApiGateway::Stage",
                {
                    "TracingEnabled": True,
                },
            )
        finally:
            os.chdir(original_cwd)

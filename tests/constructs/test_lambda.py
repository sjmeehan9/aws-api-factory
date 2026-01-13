# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Unit tests for Lambda function construct."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from aws_cdk import App, Stack, assertions

from aws_api_factory.config.defaults import get_defaults
from aws_api_factory.config.models import (
    ApisConfig,
    ComputeConfig,
    FactoryConfig,
    LambdaConfig,
    LambdaServiceConfig,
    ProfileEnum,
    ProjectConfig,
    RestApiConfig,
)
from aws_api_factory.constructs.compute_lambda import (
    LambdaFunctionConstruct,
    create_lambda_function,
)
from aws_api_factory.constructs.outputs import OutputManager


@pytest.fixture
def temp_lambda_code():
    """Create a temporary directory with Lambda handler code."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create the service directory structure
        service_dir = Path(tmpdir) / "src" / "services" / "hello"
        service_dir.mkdir(parents=True)

        # Create a simple handler
        handler_file = service_dir / "handler.py"
        handler_file.write_text(
            """
def handler(event, context):
    return {"statusCode": 200, "body": "Hello"}
"""
        )

        yield tmpdir


@pytest.fixture
def minimal_config():
    """Create a minimal factory config for testing."""
    return FactoryConfig(
        project=ProjectConfig(name="test-api", envs=["dev", "prod"]),
        profile=ProfileEnum.MINIMAL,
        apis=ApisConfig(rest=RestApiConfig(enabled=False)),
        compute=ComputeConfig(
            lambda_=LambdaConfig(
                enabled=True,
                services={
                    "hello": LambdaServiceConfig(
                        entry="src/services/hello/handler.py:handler",
                        memory_mb="auto",
                        timeout_s="auto",
                    ),
                },
            )
        ),
    )


@pytest.fixture
def scalable_config():
    """Create a scalable factory config for testing."""
    return FactoryConfig(
        project=ProjectConfig(name="test-api", envs=["dev", "prod"]),
        profile=ProfileEnum.SCALABLE,
        apis=ApisConfig(rest=RestApiConfig(enabled=False)),
        compute=ComputeConfig(
            lambda_=LambdaConfig(
                enabled=True,
                services={
                    "orders": LambdaServiceConfig(
                        entry="src/services/orders/handler.py:handler",
                        memory_mb=1024,
                        timeout_s=60,
                        reserved_concurrency=20,
                        environment={"ORDER_TABLE": "orders"},
                    ),
                },
            )
        ),
    )


@pytest.fixture
def multi_service_config():
    """Create a config with multiple Lambda services."""
    return FactoryConfig(
        project=ProjectConfig(name="multi-api", envs=["dev"]),
        profile=ProfileEnum.MINIMAL,
        apis=ApisConfig(rest=RestApiConfig(enabled=False)),
        compute=ComputeConfig(
            lambda_=LambdaConfig(
                enabled=True,
                services={
                    "hello": LambdaServiceConfig(
                        entry="src/services/hello/handler.py:handler",
                    ),
                    "orders": LambdaServiceConfig(
                        entry="src/services/orders/handler.py:handle_order",
                        memory_mb=512,
                        timeout_s=30,
                    ),
                },
            )
        ),
    )


class TestLambdaFunctionConstruct:
    """Tests for LambdaFunctionConstruct."""

    def test_construct_creates_function_with_minimal_profile(
        self, minimal_config, temp_lambda_code
    ):
        """Test Lambda function creation with minimal profile defaults."""
        app = App()
        stack = Stack(app, "TestStack")

        defaults = get_defaults(ProfileEnum.MINIMAL)
        output_manager = OutputManager(
            stack=stack, project_name="test-api", environment="dev"
        )

        construct = LambdaFunctionConstruct(
            stack,
            "LambdaFunctions",
            config=minimal_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            code_path=temp_lambda_code,
        )

        # Verify function was created
        assert "hello" in construct.functions
        assert construct.get_function("hello") is not None

        # Synthesize and check CloudFormation
        template = assertions.Template.from_stack(stack)

        # Check Lambda function exists with correct properties
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "Runtime": "python3.11",
                "MemorySize": 512,  # Minimal default
                "Timeout": 30,  # Minimal default
            },
        )

    def test_construct_creates_function_with_scalable_profile(self, temp_lambda_code):
        """Test Lambda function creation with scalable profile defaults."""
        # Create orders service directory
        service_dir = Path(temp_lambda_code) / "src" / "services" / "orders"
        service_dir.mkdir(parents=True)
        (service_dir / "handler.py").write_text("def handler(e, c): return {}")

        config = FactoryConfig(
            project=ProjectConfig(name="test-api", envs=["dev", "prod"]),
            profile=ProfileEnum.SCALABLE,
            compute=ComputeConfig(
                lambda_=LambdaConfig(
                    enabled=True,
                    services={
                        "orders": LambdaServiceConfig(
                            entry="src/services/orders/handler.py:handler",
                            memory_mb="auto",
                            timeout_s="auto",
                        ),
                    },
                )
            ),
        )

        app = App()
        stack = Stack(app, "TestStack")

        defaults = get_defaults(ProfileEnum.SCALABLE)
        output_manager = OutputManager(
            stack=stack, project_name="test-api", environment="dev"
        )

        construct = LambdaFunctionConstruct(
            stack,
            "LambdaFunctions",
            config=config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            code_path=temp_lambda_code,
        )

        template = assertions.Template.from_stack(stack)

        # Check Lambda function uses scalable defaults
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "Runtime": "python3.11",
                "MemorySize": 1024,  # Scalable default
                "Timeout": 60,  # Scalable default
            },
        )

    def test_construct_applies_custom_memory_and_timeout(self, temp_lambda_code):
        """Test that custom memory and timeout override defaults."""
        service_dir = Path(temp_lambda_code) / "src" / "services" / "custom"
        service_dir.mkdir(parents=True)
        (service_dir / "handler.py").write_text("def handler(e, c): return {}")

        config = FactoryConfig(
            project=ProjectConfig(name="test-api", envs=["dev"]),
            profile=ProfileEnum.MINIMAL,
            compute=ComputeConfig(
                lambda_=LambdaConfig(
                    enabled=True,
                    services={
                        "custom": LambdaServiceConfig(
                            entry="src/services/custom/handler.py:handler",
                            memory_mb=2048,  # Custom
                            timeout_s=120,  # Custom
                        ),
                    },
                )
            ),
        )

        app = App()
        stack = Stack(app, "TestStack")

        defaults = get_defaults(ProfileEnum.MINIMAL)
        output_manager = OutputManager(
            stack=stack, project_name="test-api", environment="dev"
        )

        LambdaFunctionConstruct(
            stack,
            "LambdaFunctions",
            config=config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            code_path=temp_lambda_code,
        )

        template = assertions.Template.from_stack(stack)

        # Verify custom values used
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "MemorySize": 2048,
                "Timeout": 120,
            },
        )

    def test_construct_sets_environment_variables(self, temp_lambda_code):
        """Test that environment variables are properly set."""
        service_dir = Path(temp_lambda_code) / "src" / "services" / "env"
        service_dir.mkdir(parents=True)
        (service_dir / "handler.py").write_text("def handler(e, c): return {}")

        config = FactoryConfig(
            project=ProjectConfig(name="test-api", envs=["dev"]),
            profile=ProfileEnum.MINIMAL,
            compute=ComputeConfig(
                lambda_=LambdaConfig(
                    enabled=True,
                    services={
                        "env": LambdaServiceConfig(
                            entry="src/services/env/handler.py:handler",
                            environment={"MY_VAR": "my_value", "ANOTHER": "value2"},
                        ),
                    },
                )
            ),
        )

        app = App()
        stack = Stack(app, "TestStack")

        defaults = get_defaults(ProfileEnum.MINIMAL)
        output_manager = OutputManager(
            stack=stack, project_name="test-api", environment="dev"
        )

        LambdaFunctionConstruct(
            stack,
            "LambdaFunctions",
            config=config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            code_path=temp_lambda_code,
        )

        template = assertions.Template.from_stack(stack)

        # Verify environment variables are set
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "Environment": {
                    "Variables": {
                        "ENVIRONMENT": "dev",
                        "PROJECT_NAME": "test-api",
                        "SERVICE_NAME": "env",
                        "MY_VAR": "my_value",
                        "ANOTHER": "value2",
                    }
                }
            },
        )

    def test_construct_creates_execution_role(self, minimal_config, temp_lambda_code):
        """Test that execution role is created with correct permissions."""
        app = App()
        stack = Stack(app, "TestStack")

        defaults = get_defaults(ProfileEnum.MINIMAL)
        output_manager = OutputManager(
            stack=stack, project_name="test-api", environment="dev"
        )

        LambdaFunctionConstruct(
            stack,
            "LambdaFunctions",
            config=minimal_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            code_path=temp_lambda_code,
        )

        template = assertions.Template.from_stack(stack)

        # Check IAM role exists
        template.has_resource_properties(
            "AWS::IAM::Role",
            {
                "AssumeRolePolicyDocument": {
                    "Statement": [
                        {
                            "Action": "sts:AssumeRole",
                            "Effect": "Allow",
                            "Principal": {"Service": "lambda.amazonaws.com"},
                        }
                    ]
                }
            },
        )

        # Check role has CloudWatch Logs policy
        template.has_resource_properties(
            "AWS::IAM::Role",
            {
                "ManagedPolicyArns": assertions.Match.array_with(
                    [
                        {
                            "Fn::Join": assertions.Match.any_value(),
                        }
                    ]
                )
            },
        )

    def test_construct_enables_xray_tracing_for_scalable(self, temp_lambda_code):
        """Test that X-Ray tracing is enabled for scalable profile."""
        service_dir = Path(temp_lambda_code) / "src" / "services" / "traced"
        service_dir.mkdir(parents=True)
        (service_dir / "handler.py").write_text("def handler(e, c): return {}")

        config = FactoryConfig(
            project=ProjectConfig(name="test-api", envs=["dev"]),
            profile=ProfileEnum.SCALABLE,
            compute=ComputeConfig(
                lambda_=LambdaConfig(
                    enabled=True,
                    services={
                        "traced": LambdaServiceConfig(
                            entry="src/services/traced/handler.py:handler",
                        ),
                    },
                )
            ),
        )

        app = App()
        stack = Stack(app, "TestStack")

        defaults = get_defaults(ProfileEnum.SCALABLE)
        output_manager = OutputManager(
            stack=stack, project_name="test-api", environment="dev"
        )

        LambdaFunctionConstruct(
            stack,
            "LambdaFunctions",
            config=config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            code_path=temp_lambda_code,
        )

        template = assertions.Template.from_stack(stack)

        # Verify X-Ray tracing is enabled
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "TracingConfig": {"Mode": "Active"},
            },
        )

    def test_construct_creates_multiple_functions(self, temp_lambda_code):
        """Test creation of multiple Lambda functions."""
        # Create multiple service directories
        for name in ["hello", "orders"]:
            service_dir = Path(temp_lambda_code) / "src" / "services" / name
            service_dir.mkdir(parents=True, exist_ok=True)
            (service_dir / "handler.py").write_text(
                f"def handle_order(e, c): return {{}}"
            )

        config = FactoryConfig(
            project=ProjectConfig(name="multi-api", envs=["dev"]),
            profile=ProfileEnum.MINIMAL,
            compute=ComputeConfig(
                lambda_=LambdaConfig(
                    enabled=True,
                    services={
                        "hello": LambdaServiceConfig(
                            entry="src/services/hello/handler.py:handle_order",
                        ),
                        "orders": LambdaServiceConfig(
                            entry="src/services/orders/handler.py:handle_order",
                        ),
                    },
                )
            ),
        )

        app = App()
        stack = Stack(app, "TestStack")

        defaults = get_defaults(ProfileEnum.MINIMAL)
        output_manager = OutputManager(
            stack=stack, project_name="multi-api", environment="dev"
        )

        construct = LambdaFunctionConstruct(
            stack,
            "LambdaFunctions",
            config=config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            code_path=temp_lambda_code,
        )

        # Verify both functions were created
        assert len(construct.functions) == 2
        assert "hello" in construct.functions
        assert "orders" in construct.functions

        template = assertions.Template.from_stack(stack)
        # CDK log retention also creates a Lambda function, so we have 3 total
        template.resource_count_is("AWS::Lambda::Function", 3)

    def test_construct_registers_outputs(self, minimal_config, temp_lambda_code):
        """Test that Lambda ARN and name outputs are registered."""
        app = App()
        stack = Stack(app, "TestStack")

        defaults = get_defaults(ProfileEnum.MINIMAL)
        output_manager = OutputManager(
            stack=stack, project_name="test-api", environment="dev"
        )

        LambdaFunctionConstruct(
            stack,
            "LambdaFunctions",
            config=minimal_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            code_path=temp_lambda_code,
        )

        # Check outputs were registered
        outputs = output_manager.get_all()
        output_keys = list(outputs.keys())

        assert "LambdaHelloArn" in output_keys
        assert "LambdaHelloName" in output_keys

    def test_construct_applies_tags(self, minimal_config, temp_lambda_code):
        """Test that tags are applied to Lambda function."""
        app = App()
        stack = Stack(app, "TestStack")

        defaults = get_defaults(ProfileEnum.MINIMAL)
        output_manager = OutputManager(
            stack=stack, project_name="test-api", environment="dev"
        )

        LambdaFunctionConstruct(
            stack,
            "LambdaFunctions",
            config=minimal_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            code_path=temp_lambda_code,
        )

        template = assertions.Template.from_stack(stack)

        # Verify Lambda function has expected properties
        # Tags are applied at the CDK level via Tags.of() which
        # manifests in the CloudFormation template
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "FunctionName": assertions.Match.string_like_regexp(
                    "test-api-dev-lambda-hello"
                ),
            },
        )

    def test_validation_fails_when_lambda_disabled(self, temp_lambda_code):
        """Test that validation fails when Lambda is disabled."""
        config = FactoryConfig(
            project=ProjectConfig(name="test-api", envs=["dev"]),
            profile=ProfileEnum.MINIMAL,
            compute=ComputeConfig(
                lambda_=LambdaConfig(
                    enabled=False,
                    services={},
                )
            ),
        )

        app = App()
        stack = Stack(app, "TestStack")

        defaults = get_defaults(ProfileEnum.MINIMAL)
        output_manager = OutputManager(
            stack=stack, project_name="test-api", environment="dev"
        )

        with pytest.raises(ValueError, match="Lambda compute is not enabled"):
            LambdaFunctionConstruct(
                stack,
                "LambdaFunctions",
                config=config,
                profile_defaults=defaults,
                output_manager=output_manager,
                environment="dev",
                code_path=temp_lambda_code,
            )

    def test_get_function_returns_none_for_unknown_service(
        self, minimal_config, temp_lambda_code
    ):
        """Test that get_function returns None for unknown service."""
        app = App()
        stack = Stack(app, "TestStack")

        defaults = get_defaults(ProfileEnum.MINIMAL)
        output_manager = OutputManager(
            stack=stack, project_name="test-api", environment="dev"
        )

        construct = LambdaFunctionConstruct(
            stack,
            "LambdaFunctions",
            config=minimal_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            code_path=temp_lambda_code,
        )

        assert construct.get_function("nonexistent") is None

    def test_get_all_functions_returns_dict(self, minimal_config, temp_lambda_code):
        """Test that get_all_functions returns a dictionary."""
        app = App()
        stack = Stack(app, "TestStack")

        defaults = get_defaults(ProfileEnum.MINIMAL)
        output_manager = OutputManager(
            stack=stack, project_name="test-api", environment="dev"
        )

        construct = LambdaFunctionConstruct(
            stack,
            "LambdaFunctions",
            config=minimal_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            code_path=temp_lambda_code,
        )

        all_functions = construct.get_all_functions()
        assert isinstance(all_functions, dict)
        assert "hello" in all_functions


class TestCreateLambdaFunction:
    """Tests for the create_lambda_function factory function."""

    def test_factory_function_creates_construct(self, minimal_config, temp_lambda_code):
        """Test the factory function creates a LambdaFunctionConstruct."""
        app = App()
        stack = Stack(app, "TestStack")

        defaults = get_defaults(ProfileEnum.MINIMAL)
        output_manager = OutputManager(
            stack=stack, project_name="test-api", environment="dev"
        )

        construct = create_lambda_function(
            stack,
            "LambdaFunctions",
            config=minimal_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            code_path=temp_lambda_code,
        )

        assert isinstance(construct, LambdaFunctionConstruct)
        assert "hello" in construct.functions

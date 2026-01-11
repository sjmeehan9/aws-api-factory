# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Unit tests for App Runner construct."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from aws_cdk import App, Stack, assertions

from aws_api_factory.config.defaults import get_defaults
from aws_api_factory.config.models import (
    ApisConfig,
    AppRunnerConfig,
    AppRunnerServiceConfig,
    AuthModeEnum,
    ComputeConfig,
    FactoryConfig,
    HttpMethodEnum,
    ProfileEnum,
    ProjectConfig,
    RestApiConfig,
    RouteConfig,
)
from aws_api_factory.constructs.compute_apprunner import (
    AppRunnerConstruct,
    create_apprunner_service,
)
from aws_api_factory.constructs.outputs import OutputManager


@pytest.fixture
def temp_dockerfile():
    """Create a temporary directory with a Dockerfile."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a minimal Dockerfile
        dockerfile_dir = Path(tmpdir) / "src" / "services" / "public_api"
        dockerfile_dir.mkdir(parents=True)

        dockerfile = dockerfile_dir / "Dockerfile"
        dockerfile.write_text(
            """
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
"""
        )

        # Create requirements.txt
        requirements = dockerfile_dir / "requirements.txt"
        requirements.write_text("fastapi>=0.104.0\nuvicorn>=0.24.0\n")

        # Create a minimal app.py
        app_py = dockerfile_dir / "app.py"
        app_py.write_text(
            """
from fastapi import FastAPI
app = FastAPI()

@app.get("/healthz")
def health(): return {"status": "healthy"}

@app.get("/")
def root(): return {"message": "Hello"}
"""
        )

        yield tmpdir


@pytest.fixture
def minimal_apprunner_config():
    """Create a minimal App Runner config for testing."""
    return FactoryConfig(
        project=ProjectConfig(name="test-api", envs=["dev", "prod"]),
        profile=ProfileEnum.MINIMAL,
        compute=ComputeConfig(
            apprunner=AppRunnerConfig(
                enabled=True,
                services={
                    "public_api": AppRunnerServiceConfig(
                        dockerfile="src/services/public_api/Dockerfile",
                        port=8000,
                        healthcheck_path="/healthz",
                        cpu=1,
                        memory=2,
                        min_instances=1,
                        max_instances=10,
                    ),
                },
            )
        ),
    )


@pytest.fixture
def scalable_apprunner_config():
    """Create a scalable App Runner config for testing."""
    return FactoryConfig(
        project=ProjectConfig(name="scalable-api", envs=["dev", "prod"]),
        profile=ProfileEnum.SCALABLE,
        compute=ComputeConfig(
            apprunner=AppRunnerConfig(
                enabled=True,
                services={
                    "public_api": AppRunnerServiceConfig(
                        dockerfile="src/services/public_api/Dockerfile",
                        port=8000,
                        healthcheck_path="/healthz",
                        cpu=2,
                        memory=4,
                        min_instances=2,
                        max_instances=25,
                        environment={"LOG_LEVEL": "INFO", "DEBUG": "false"},
                    ),
                },
            )
        ),
    )


@pytest.fixture
def multi_service_config():
    """Create a config with multiple App Runner services."""
    return FactoryConfig(
        project=ProjectConfig(name="multi-api", envs=["dev"]),
        profile=ProfileEnum.MINIMAL,
        compute=ComputeConfig(
            apprunner=AppRunnerConfig(
                enabled=True,
                services={
                    "api": AppRunnerServiceConfig(
                        dockerfile="src/services/public_api/Dockerfile",
                        port=8000,
                    ),
                    "worker": AppRunnerServiceConfig(
                        dockerfile="src/services/public_api/Dockerfile",
                        port=8080,
                        cpu=2,
                        memory=4,
                    ),
                },
            )
        ),
    )


@pytest.fixture
def disabled_apprunner_config():
    """Create a config with App Runner disabled."""
    return FactoryConfig(
        project=ProjectConfig(name="test-api", envs=["dev"]),
        profile=ProfileEnum.MINIMAL,
        compute=ComputeConfig(
            apprunner=AppRunnerConfig(enabled=False),
        ),
    )


class TestAppRunnerConstructValidation:
    """Tests for App Runner construct configuration validation."""

    def test_disabled_apprunner_fails_validation(
        self, disabled_apprunner_config, temp_dockerfile
    ):
        """Test that disabled App Runner config fails validation."""
        app = App()
        stack = Stack(app, "TestStack")
        output_manager = OutputManager(stack, "test-api", "dev")
        defaults = get_defaults(ProfileEnum.MINIMAL)

        with pytest.raises(ValueError, match="not enabled"):
            AppRunnerConstruct(
                stack,
                "AppRunner",
                config=disabled_apprunner_config,
                profile_defaults=defaults,
                output_manager=output_manager,
                environment="dev",
                code_path=temp_dockerfile,
            )

    def test_invalid_cpu_memory_combination(self, temp_dockerfile):
        """Test that invalid CPU/memory combinations are rejected."""
        # 1 vCPU with 8GB is not a valid combination
        config = FactoryConfig(
            project=ProjectConfig(name="test-api", envs=["dev"]),
            profile=ProfileEnum.MINIMAL,
            compute=ComputeConfig(
                apprunner=AppRunnerConfig(
                    enabled=True,
                    services={
                        "api": AppRunnerServiceConfig(
                            dockerfile="src/services/public_api/Dockerfile",
                            cpu=1,
                            memory=8,  # Invalid for 1 vCPU
                        ),
                    },
                )
            ),
        )

        app = App()
        stack = Stack(app, "TestStack")
        output_manager = OutputManager(stack, "test-api", "dev")
        defaults = get_defaults(ProfileEnum.MINIMAL)

        with pytest.raises(ValueError, match="Invalid CPU/memory combination"):
            AppRunnerConstruct(
                stack,
                "AppRunner",
                config=config,
                profile_defaults=defaults,
                output_manager=output_manager,
                environment="dev",
                code_path=temp_dockerfile,
            )


class TestAppRunnerConstructCreation:
    """Tests for App Runner construct resource creation."""

    def test_creates_apprunner_service(self, minimal_apprunner_config, temp_dockerfile):
        """Test that App Runner service is created."""
        app = App()
        stack = Stack(app, "TestStack")
        output_manager = OutputManager(stack, "test-api", "dev")
        defaults = get_defaults(ProfileEnum.MINIMAL)

        construct = AppRunnerConstruct(
            stack,
            "AppRunner",
            config=minimal_apprunner_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            code_path=temp_dockerfile,
        )

        # Verify the service was created
        assert "public_api" in construct.services
        assert construct.get_service("public_api") is not None

        # Synthesize and verify CloudFormation
        template = assertions.Template.from_stack(stack)

        # Verify CfnService exists
        template.resource_count_is("AWS::AppRunner::Service", 1)

    def test_creates_autoscaling_configuration(
        self, minimal_apprunner_config, temp_dockerfile
    ):
        """Test that auto-scaling configuration is created."""
        app = App()
        stack = Stack(app, "TestStack")
        output_manager = OutputManager(stack, "test-api", "dev")
        defaults = get_defaults(ProfileEnum.MINIMAL)

        AppRunnerConstruct(
            stack,
            "AppRunner",
            config=minimal_apprunner_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            code_path=temp_dockerfile,
        )

        template = assertions.Template.from_stack(stack)

        # Verify auto-scaling configuration exists
        template.resource_count_is("AWS::AppRunner::AutoScalingConfiguration", 1)

    def test_creates_iam_roles(self, minimal_apprunner_config, temp_dockerfile):
        """Test that IAM access and instance roles are created."""
        app = App()
        stack = Stack(app, "TestStack")
        output_manager = OutputManager(stack, "test-api", "dev")
        defaults = get_defaults(ProfileEnum.MINIMAL)

        construct = AppRunnerConstruct(
            stack,
            "AppRunner",
            config=minimal_apprunner_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            code_path=temp_dockerfile,
        )

        # Verify roles were created
        assert "public_api" in construct.access_roles
        assert "public_api" in construct.instance_roles

        template = assertions.Template.from_stack(stack)

        # Should have access role and instance role
        template.resource_count_is("AWS::IAM::Role", 2)

    def test_access_role_has_ecr_permissions(
        self, minimal_apprunner_config, temp_dockerfile
    ):
        """Test that access role has ECR pull permissions."""
        app = App()
        stack = Stack(app, "TestStack")
        output_manager = OutputManager(stack, "test-api", "dev")
        defaults = get_defaults(ProfileEnum.MINIMAL)

        AppRunnerConstruct(
            stack,
            "AppRunner",
            config=minimal_apprunner_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            code_path=temp_dockerfile,
        )

        template = assertions.Template.from_stack(stack)

        # Verify access role has the ECR policy attached
        template.has_resource_properties(
            "AWS::IAM::Role",
            {
                "AssumeRolePolicyDocument": {
                    "Statement": assertions.Match.array_with(
                        [
                            assertions.Match.object_like(
                                {
                                    "Principal": {
                                        "Service": "build.apprunner.amazonaws.com"
                                    },
                                }
                            )
                        ]
                    )
                }
            },
        )

    def test_instance_role_has_logs_permissions(
        self, minimal_apprunner_config, temp_dockerfile
    ):
        """Test that instance role has CloudWatch Logs permissions."""
        app = App()
        stack = Stack(app, "TestStack")
        output_manager = OutputManager(stack, "test-api", "dev")
        defaults = get_defaults(ProfileEnum.MINIMAL)

        AppRunnerConstruct(
            stack,
            "AppRunner",
            config=minimal_apprunner_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            code_path=temp_dockerfile,
        )

        template = assertions.Template.from_stack(stack)

        # Verify instance role exists with correct trust policy
        template.has_resource_properties(
            "AWS::IAM::Role",
            {
                "AssumeRolePolicyDocument": {
                    "Statement": assertions.Match.array_with(
                        [
                            assertions.Match.object_like(
                                {
                                    "Principal": {
                                        "Service": "tasks.apprunner.amazonaws.com"
                                    },
                                }
                            )
                        ]
                    )
                }
            },
        )


class TestAppRunnerServiceConfiguration:
    """Tests for App Runner service configuration properties."""

    def test_minimal_profile_uses_tcp_healthcheck(
        self, minimal_apprunner_config, temp_dockerfile
    ):
        """Test that minimal profile uses TCP health check."""
        app = App()
        stack = Stack(app, "TestStack")
        output_manager = OutputManager(stack, "test-api", "dev")
        defaults = get_defaults(ProfileEnum.MINIMAL)

        AppRunnerConstruct(
            stack,
            "AppRunner",
            config=minimal_apprunner_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            code_path=temp_dockerfile,
        )

        template = assertions.Template.from_stack(stack)

        # Verify health check is TCP for minimal
        template.has_resource_properties(
            "AWS::AppRunner::Service",
            {
                "HealthCheckConfiguration": {
                    "Protocol": "TCP",
                }
            },
        )

    def test_scalable_profile_uses_http_healthcheck(
        self, scalable_apprunner_config, temp_dockerfile
    ):
        """Test that scalable profile uses HTTP health check."""
        app = App()
        stack = Stack(app, "TestStack")
        output_manager = OutputManager(stack, "scalable-api", "dev")
        defaults = get_defaults(ProfileEnum.SCALABLE)

        AppRunnerConstruct(
            stack,
            "AppRunner",
            config=scalable_apprunner_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            code_path=temp_dockerfile,
        )

        template = assertions.Template.from_stack(stack)

        # Verify health check is HTTP for scalable
        template.has_resource_properties(
            "AWS::AppRunner::Service",
            {
                "HealthCheckConfiguration": {
                    "Protocol": "HTTP",
                    "Path": "/healthz",
                }
            },
        )

    def test_service_cpu_memory_configuration(
        self, scalable_apprunner_config, temp_dockerfile
    ):
        """Test that CPU and memory are configured correctly."""
        app = App()
        stack = Stack(app, "TestStack")
        output_manager = OutputManager(stack, "scalable-api", "dev")
        defaults = get_defaults(ProfileEnum.SCALABLE)

        AppRunnerConstruct(
            stack,
            "AppRunner",
            config=scalable_apprunner_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            code_path=temp_dockerfile,
        )

        template = assertions.Template.from_stack(stack)

        # Verify instance configuration
        template.has_resource_properties(
            "AWS::AppRunner::Service",
            {
                "InstanceConfiguration": {
                    "Cpu": "2 vCPU",
                    "Memory": "4 GB",
                }
            },
        )

    def test_environment_variables_injected(
        self, scalable_apprunner_config, temp_dockerfile
    ):
        """Test that environment variables are injected."""
        app = App()
        stack = Stack(app, "TestStack")
        output_manager = OutputManager(stack, "scalable-api", "dev")
        defaults = get_defaults(ProfileEnum.SCALABLE)

        AppRunnerConstruct(
            stack,
            "AppRunner",
            config=scalable_apprunner_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            code_path=temp_dockerfile,
        )

        template = assertions.Template.from_stack(stack)

        # Verify environment variables are set
        template.has_resource_properties(
            "AWS::AppRunner::Service",
            {
                "SourceConfiguration": {
                    "ImageRepository": {
                        "ImageConfiguration": {
                            "RuntimeEnvironmentVariables": assertions.Match.array_with(
                                [
                                    {"Name": "ENVIRONMENT", "Value": "dev"},
                                    {"Name": "PROJECT_NAME", "Value": "scalable-api"},
                                    {"Name": "SERVICE_NAME", "Value": "public_api"},
                                ]
                            )
                        }
                    }
                }
            },
        )

    def test_port_configuration(self, minimal_apprunner_config, temp_dockerfile):
        """Test that port is configured correctly."""
        app = App()
        stack = Stack(app, "TestStack")
        output_manager = OutputManager(stack, "test-api", "dev")
        defaults = get_defaults(ProfileEnum.MINIMAL)

        AppRunnerConstruct(
            stack,
            "AppRunner",
            config=minimal_apprunner_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            code_path=temp_dockerfile,
        )

        template = assertions.Template.from_stack(stack)

        # Verify port is set
        template.has_resource_properties(
            "AWS::AppRunner::Service",
            {
                "SourceConfiguration": {
                    "ImageRepository": {
                        "ImageConfiguration": {
                            "Port": "8000",
                        }
                    }
                }
            },
        )


class TestAppRunnerAutoScaling:
    """Tests for App Runner auto-scaling configuration."""

    def test_autoscaling_min_max_instances(
        self, minimal_apprunner_config, temp_dockerfile
    ):
        """Test that auto-scaling min/max instances are configured."""
        app = App()
        stack = Stack(app, "TestStack")
        output_manager = OutputManager(stack, "test-api", "dev")
        defaults = get_defaults(ProfileEnum.MINIMAL)

        AppRunnerConstruct(
            stack,
            "AppRunner",
            config=minimal_apprunner_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            code_path=temp_dockerfile,
        )

        template = assertions.Template.from_stack(stack)

        # Verify auto-scaling configuration
        template.has_resource_properties(
            "AWS::AppRunner::AutoScalingConfiguration",
            {
                "MinSize": 1,
                "MaxSize": 10,
                "MaxConcurrency": 100,
            },
        )

    def test_scalable_profile_scaling_values(
        self, scalable_apprunner_config, temp_dockerfile
    ):
        """Test that scalable profile has higher scaling values."""
        app = App()
        stack = Stack(app, "TestStack")
        output_manager = OutputManager(stack, "scalable-api", "dev")
        defaults = get_defaults(ProfileEnum.SCALABLE)

        AppRunnerConstruct(
            stack,
            "AppRunner",
            config=scalable_apprunner_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            code_path=temp_dockerfile,
        )

        template = assertions.Template.from_stack(stack)

        # Verify scalable has higher values
        template.has_resource_properties(
            "AWS::AppRunner::AutoScalingConfiguration",
            {
                "MinSize": 2,
                "MaxSize": 25,
            },
        )


class TestAppRunnerMultipleServices:
    """Tests for multiple App Runner services."""

    def test_creates_multiple_services(self, multi_service_config, temp_dockerfile):
        """Test that multiple services are created."""
        app = App()
        stack = Stack(app, "TestStack")
        output_manager = OutputManager(stack, "multi-api", "dev")
        defaults = get_defaults(ProfileEnum.MINIMAL)

        construct = AppRunnerConstruct(
            stack,
            "AppRunner",
            config=multi_service_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            code_path=temp_dockerfile,
        )

        # Verify both services were created
        assert len(construct.services) == 2
        assert "api" in construct.services
        assert "worker" in construct.services

        template = assertions.Template.from_stack(stack)

        # Should have 2 services
        template.resource_count_is("AWS::AppRunner::Service", 2)

        # Should have 2 auto-scaling configs
        template.resource_count_is("AWS::AppRunner::AutoScalingConfiguration", 2)

        # Should have 4 roles (2 access + 2 instance)
        template.resource_count_is("AWS::IAM::Role", 4)


class TestAppRunnerOutputs:
    """Tests for App Runner construct outputs."""

    def test_registers_service_outputs(self, minimal_apprunner_config, temp_dockerfile):
        """Test that service outputs are registered."""
        app = App()
        stack = Stack(app, "TestStack")
        output_manager = OutputManager(stack, "test-api", "dev")
        defaults = get_defaults(ProfileEnum.MINIMAL)

        AppRunnerConstruct(
            stack,
            "AppRunner",
            config=minimal_apprunner_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            code_path=temp_dockerfile,
        )

        # Verify outputs were registered
        outputs = output_manager.get_all()
        assert len(outputs) >= 3  # URL, ARN, ID

        # Check specific outputs exist (sanitized names: public_api -> PublicApi)
        output_keys = list(outputs.keys())
        assert "AppRunnerPublicApiUrl" in output_keys
        assert "AppRunnerPublicApiArn" in output_keys
        assert "AppRunnerPublicApiId" in output_keys


class TestAppRunnerTags:
    """Tests for App Runner resource tagging."""

    def test_service_has_tags(self, minimal_apprunner_config, temp_dockerfile):
        """Test that service has proper tags."""
        app = App()
        stack = Stack(app, "TestStack")
        output_manager = OutputManager(stack, "test-api", "dev")
        defaults = get_defaults(ProfileEnum.MINIMAL)

        AppRunnerConstruct(
            stack,
            "AppRunner",
            config=minimal_apprunner_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            code_path=temp_dockerfile,
        )

        template = assertions.Template.from_stack(stack)

        # Verify service has required tags - check individual tag presence
        template.has_resource_properties(
            "AWS::AppRunner::Service",
            {
                "Tags": assertions.Match.array_with(
                    [
                        assertions.Match.object_like(
                            {"Key": "Project", "Value": "test-api"}
                        ),
                    ]
                )
            },
        )
        template.has_resource_properties(
            "AWS::AppRunner::Service",
            {
                "Tags": assertions.Match.array_with(
                    [
                        assertions.Match.object_like(
                            {"Key": "Environment", "Value": "dev"}
                        ),
                    ]
                )
            },
        )
        template.has_resource_properties(
            "AWS::AppRunner::Service",
            {
                "Tags": assertions.Match.array_with(
                    [
                        assertions.Match.object_like(
                            {"Key": "ManagedBy", "Value": "aws-api-factory"}
                        ),
                    ]
                )
            },
        )


class TestConvenienceFunction:
    """Tests for the create_apprunner_service convenience function."""

    def test_create_apprunner_service(self, minimal_apprunner_config, temp_dockerfile):
        """Test the convenience function creates construct correctly."""
        app = App()
        stack = Stack(app, "TestStack")
        output_manager = OutputManager(stack, "test-api", "dev")
        defaults = get_defaults(ProfileEnum.MINIMAL)

        construct = create_apprunner_service(
            stack,
            "AppRunner",
            config=minimal_apprunner_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            code_path=temp_dockerfile,
        )

        assert isinstance(construct, AppRunnerConstruct)
        assert "public_api" in construct.services

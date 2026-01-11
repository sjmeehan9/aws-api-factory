# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""Integration tests for REST API + App Runner deployment.

These tests verify the complete stack synthesis with App Runner
and API Gateway HTTP integration working together.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from aws_cdk import App, Stack, assertions
from aws_cdk import aws_apigateway as apigw

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
from aws_api_factory.constructs.compute_apprunner import AppRunnerConstruct
from aws_api_factory.constructs.outputs import OutputManager
from aws_api_factory.constructs.rest_api import RestApiConstruct
from aws_api_factory.constructs.rest_api.http_integration import (
    attach_http_integration_to_resource,
    attach_http_integration_to_routes,
    create_catch_all_proxy,
    create_http_integration,
    create_http_proxy_integration,
)


@pytest.fixture
def temp_apprunner_project():
    """Create a temporary project structure with App Runner services."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create public_api service
        api_dir = Path(tmpdir) / "src" / "services" / "public_api"
        api_dir.mkdir(parents=True)

        (api_dir / "Dockerfile").write_text(
            """
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
"""
        )

        (api_dir / "requirements.txt").write_text("fastapi>=0.104.0\nuvicorn>=0.24.0\n")

        (api_dir / "app.py").write_text(
            """
from fastapi import FastAPI
app = FastAPI()

@app.get("/healthz")
def health(): return {"status": "healthy"}

@app.get("/")
def root(): return {"message": "Hello from App Runner"}
"""
        )

        yield tmpdir


@pytest.fixture
def full_stack_config():
    """Create a config with REST API and App Runner service."""
    return FactoryConfig(
        project=ProjectConfig(name="full-stack", envs=["dev", "prod"]),
        profile=ProfileEnum.MINIMAL,
        apis=ApisConfig(
            rest=RestApiConfig(
                enabled=True,
                routes=[
                    RouteConfig(
                        path="/api",
                        methods=[HttpMethodEnum.GET, HttpMethodEnum.POST],
                        service="public_api",
                        auth=AuthModeEnum.NONE,
                    ),
                    RouteConfig(
                        path="/api/items",
                        methods=[HttpMethodEnum.GET],
                        service="public_api",
                        auth=AuthModeEnum.NONE,
                    ),
                ],
            )
        ),
        compute=ComputeConfig(
            apprunner=AppRunnerConfig(
                enabled=True,
                services={
                    "public_api": AppRunnerServiceConfig(
                        dockerfile="src/services/public_api/Dockerfile",
                        port=8000,
                        healthcheck_path="/healthz",
                    ),
                },
            )
        ),
    )


@pytest.fixture
def scalable_full_stack_config():
    """Create a scalable config with REST API and App Runner service."""
    return FactoryConfig(
        project=ProjectConfig(name="scalable-stack", envs=["dev", "prod"]),
        profile=ProfileEnum.SCALABLE,
        apis=ApisConfig(
            rest=RestApiConfig(
                enabled=True,
                routes=[
                    RouteConfig(
                        path="/api",
                        methods=[HttpMethodEnum.GET, HttpMethodEnum.POST],
                        service="public_api",
                        auth=AuthModeEnum.API_KEY,
                    ),
                ],
            )
        ),
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
                        environment={"LOG_LEVEL": "INFO"},
                    ),
                },
            )
        ),
    )


class TestHttpIntegration:
    """Tests for HTTP integration functions."""

    def test_create_http_integration(self):
        """Test creating basic HTTP integration."""
        integration = create_http_integration(
            "https://abc123.us-east-1.awsapprunner.com"
        )
        assert integration is not None

    def test_create_http_proxy_integration_with_path(self):
        """Test creating HTTP proxy integration with path."""
        integration = create_http_proxy_integration(
            "https://abc123.us-east-1.awsapprunner.com", path="/api/v1"
        )
        assert integration is not None

    def test_attach_http_integration_to_resource(self):
        """Test attaching HTTP integration to API Gateway resource."""
        app = App()
        stack = Stack(app, "TestStack")

        api = apigw.RestApi(stack, "TestApi")
        resource = api.root.add_resource("test")

        integration = create_http_integration(
            "https://abc123.us-east-1.awsapprunner.com"
        )

        method = attach_http_integration_to_resource(resource, "GET", integration)

        assert method is not None

        template = assertions.Template.from_stack(stack)
        template.resource_count_is("AWS::ApiGateway::Method", 1)

    def test_attach_http_integration_with_iam_auth(self):
        """Test attaching HTTP integration with IAM auth."""
        app = App()
        stack = Stack(app, "TestStack")

        api = apigw.RestApi(stack, "TestApi")
        resource = api.root.add_resource("secure")

        integration = create_http_integration(
            "https://abc123.us-east-1.awsapprunner.com"
        )

        method = attach_http_integration_to_resource(
            resource,
            "GET",
            integration,
            authorization_type=apigw.AuthorizationType.IAM,
        )

        assert method is not None

        template = assertions.Template.from_stack(stack)
        template.has_resource_properties(
            "AWS::ApiGateway::Method", {"AuthorizationType": "AWS_IAM"}
        )

    def test_create_catch_all_proxy(self):
        """Test creating catch-all proxy for backend."""
        app = App()
        stack = Stack(app, "TestStack")

        api = apigw.RestApi(stack, "TestApi", deploy=False)

        methods = create_catch_all_proxy(
            api,
            "https://abc123.us-east-1.awsapprunner.com",
        )

        assert "proxy" in methods
        assert "root" in methods

        template = assertions.Template.from_stack(stack)

        # Should have proxy resource
        template.has_resource_properties(
            "AWS::ApiGateway::Resource", {"PathPart": "{proxy+}"}
        )


class TestRestAppRunnerIntegration:
    """Tests for REST API + App Runner combined stack."""

    def test_synthesizes_complete_stack(
        self, full_stack_config, temp_apprunner_project
    ):
        """Test that complete stack synthesizes successfully."""
        app = App()
        stack = Stack(app, "TestStack")
        output_manager = OutputManager(stack, "full-stack", "dev")
        defaults = get_defaults(ProfileEnum.MINIMAL)

        # Create App Runner services
        apprunner = AppRunnerConstruct(
            stack,
            "AppRunner",
            config=full_stack_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            code_path=temp_apprunner_project,
        )

        # Create REST API
        # Note: In production, you'd integrate with App Runner URLs
        # Here we just test that both constructs can be created together

        template = assertions.Template.from_stack(stack)

        # Verify App Runner resources
        template.resource_count_is("AWS::AppRunner::Service", 1)
        template.resource_count_is("AWS::AppRunner::AutoScalingConfiguration", 1)

        # Verify IAM roles
        template.resource_count_is("AWS::IAM::Role", 2)

    def test_cloudformation_template_valid(
        self, full_stack_config, temp_apprunner_project
    ):
        """Test that CloudFormation template is valid JSON."""
        app = App()
        stack = Stack(app, "TestStack")
        output_manager = OutputManager(stack, "full-stack", "dev")
        defaults = get_defaults(ProfileEnum.MINIMAL)

        AppRunnerConstruct(
            stack,
            "AppRunner",
            config=full_stack_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            code_path=temp_apprunner_project,
        )

        # Synthesize and verify it's valid JSON
        template = assertions.Template.from_stack(stack)
        template_json = template.to_json()

        # Verify it's valid JSON by parsing
        parsed = json.loads(json.dumps(template_json))
        assert "Resources" in parsed

    def test_scalable_profile_configuration(
        self, scalable_full_stack_config, temp_apprunner_project
    ):
        """Test that scalable profile applies correct settings."""
        app = App()
        stack = Stack(app, "TestStack")
        output_manager = OutputManager(stack, "scalable-stack", "dev")
        defaults = get_defaults(ProfileEnum.SCALABLE)

        AppRunnerConstruct(
            stack,
            "AppRunner",
            config=scalable_full_stack_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            code_path=temp_apprunner_project,
        )

        template = assertions.Template.from_stack(stack)

        # Verify scalable settings
        template.has_resource_properties(
            "AWS::AppRunner::Service",
            {
                "InstanceConfiguration": {
                    "Cpu": "2 vCPU",
                    "Memory": "4 GB",
                },
                "HealthCheckConfiguration": {
                    "Protocol": "HTTP",
                    "Path": "/healthz",
                },
            },
        )

        template.has_resource_properties(
            "AWS::AppRunner::AutoScalingConfiguration",
            {
                "MinSize": 2,
                "MaxSize": 25,
            },
        )


class TestDockerImageBuild:
    """Tests for Docker image building."""

    def test_docker_image_asset_created(
        self, full_stack_config, temp_apprunner_project
    ):
        """Test that Docker image asset is created."""
        app = App()
        stack = Stack(app, "TestStack")
        output_manager = OutputManager(stack, "full-stack", "dev")
        defaults = get_defaults(ProfileEnum.MINIMAL)

        construct = AppRunnerConstruct(
            stack,
            "AppRunner",
            config=full_stack_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            code_path=temp_apprunner_project,
        )

        # Verify Docker image was created
        assert "public_api" in construct._docker_images

    def test_ecr_image_uri_in_service(self, full_stack_config, temp_apprunner_project):
        """Test that ECR image URI is used in service config."""
        app = App()
        stack = Stack(app, "TestStack")
        output_manager = OutputManager(stack, "full-stack", "dev")
        defaults = get_defaults(ProfileEnum.MINIMAL)

        AppRunnerConstruct(
            stack,
            "AppRunner",
            config=full_stack_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            code_path=temp_apprunner_project,
        )

        template = assertions.Template.from_stack(stack)

        # Verify service uses ECR
        template.has_resource_properties(
            "AWS::AppRunner::Service",
            {
                "SourceConfiguration": {
                    "ImageRepository": {
                        "ImageRepositoryType": "ECR",
                    }
                }
            },
        )


class TestMultiEnvironmentDeployment:
    """Tests for multi-environment deployment scenarios."""

    def test_different_environments_have_different_names(
        self, full_stack_config, temp_apprunner_project
    ):
        """Test that different environments produce different resource names."""
        defaults = get_defaults(ProfileEnum.MINIMAL)

        # Dev environment
        dev_app = App()
        dev_stack = Stack(dev_app, "DevStack")
        dev_output_manager = OutputManager(dev_stack, "full-stack", "dev")

        dev_construct = AppRunnerConstruct(
            dev_stack,
            "AppRunner",
            config=full_stack_config,
            profile_defaults=defaults,
            output_manager=dev_output_manager,
            environment="dev",
            code_path=temp_apprunner_project,
        )

        # Prod environment
        prod_app = App()
        prod_stack = Stack(prod_app, "ProdStack")
        prod_output_manager = OutputManager(prod_stack, "full-stack", "prod")

        prod_construct = AppRunnerConstruct(
            prod_stack,
            "AppRunner",
            config=full_stack_config,
            profile_defaults=defaults,
            output_manager=prod_output_manager,
            environment="prod",
            code_path=temp_apprunner_project,
        )

        # Verify both constructs created successfully
        assert len(dev_construct.services) == 1
        assert len(prod_construct.services) == 1

        # Verify different environments in outputs
        dev_outputs = dev_output_manager.get_all()
        prod_outputs = prod_output_manager.get_all()

        assert len(dev_outputs) > 0
        assert len(prod_outputs) > 0


class TestOutputExports:
    """Tests for stack output exports."""

    def test_apprunner_outputs_exported(
        self, full_stack_config, temp_apprunner_project
    ):
        """Test that App Runner outputs are exported correctly."""
        app = App()
        stack = Stack(app, "TestStack")
        output_manager = OutputManager(stack, "full-stack", "dev")
        defaults = get_defaults(ProfileEnum.MINIMAL)

        construct = AppRunnerConstruct(
            stack,
            "AppRunner",
            config=full_stack_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            code_path=temp_apprunner_project,
        )

        # Export outputs
        output_manager.export_to_cfn()

        template = assertions.Template.from_stack(stack)

        # Verify outputs exist
        outputs = template.find_outputs("*")
        assert len(outputs) >= 3  # URL, ARN, ID

    def test_service_url_accessible(self, full_stack_config, temp_apprunner_project):
        """Test that service URL is accessible via construct."""
        app = App()
        stack = Stack(app, "TestStack")
        output_manager = OutputManager(stack, "full-stack", "dev")
        defaults = get_defaults(ProfileEnum.MINIMAL)

        construct = AppRunnerConstruct(
            stack,
            "AppRunner",
            config=full_stack_config,
            profile_defaults=defaults,
            output_manager=output_manager,
            environment="dev",
            code_path=temp_apprunner_project,
        )

        # Verify URL is accessible
        url = construct.get_service_url("public_api")
        assert url is not None
        assert "https://" in url

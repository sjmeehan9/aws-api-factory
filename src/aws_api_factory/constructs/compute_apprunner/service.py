# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""App Runner service construct for AWS API Factory.

This module implements the AppRunnerConstruct that creates AWS App Runner
services from Dockerfile configurations, with support for health checks,
auto-scaling, environment variables, and secrets injection.

Example:
    >>> from aws_api_factory.constructs.compute_apprunner import AppRunnerConstruct
    >>> construct = AppRunnerConstruct(
    ...     stack, "AppRunner",
    ...     config=config,
    ...     profile_defaults=defaults,
    ...     output_manager=outputs,
    ...     environment="dev",
    ... )
    >>> # Access created services
    >>> url = construct.get_service_url("public_api")

"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from aws_cdk import CfnOutput, Duration, RemovalPolicy
from aws_cdk import aws_apprunner as apprunner
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_ecr_assets as ecr_assets
from aws_cdk import aws_iam as iam
from constructs import Construct

from aws_api_factory.constructs.base import BaseConstruct

if TYPE_CHECKING:
    from aws_api_factory.config.defaults import ProfileDefaults
    from aws_api_factory.config.models import AppRunnerServiceConfig, FactoryConfig
    from aws_api_factory.constructs.outputs import OutputManager


class AppRunnerConstruct(BaseConstruct):
    """CDK construct for creating App Runner services from configuration.

    This construct creates App Runner services for each service defined in
    compute.apprunner.services. It applies profile-based defaults and sets
    up health checks, auto-scaling, and environment variables.

    Attributes:
        services: Dictionary mapping service name to CfnService.
        service_urls: Dictionary mapping service name to service URL.
        access_roles: Dictionary mapping service name to IAM access role.
        instance_roles: Dictionary mapping service name to IAM instance role.

    Example:
        >>> construct = AppRunnerConstruct(
        ...     stack, "AppRunner",
        ...     config=config,
        ...     profile_defaults=defaults,
        ...     output_manager=outputs,
        ...     environment="dev",
        ... )
        >>> url = construct.get_service_url("public_api")
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
        """Initialize the App Runner construct.

        Args:
            scope: The CDK construct scope.
            id: The construct ID.
            config: The factory configuration.
            profile_defaults: Profile defaults for App Runner settings.
            output_manager: Output manager for registering outputs.
            environment: Deployment environment name.
            code_path: Optional base path for Dockerfile locations. Defaults to cwd.
            **kwargs: Additional arguments passed to BaseConstruct.
        """
        self._code_path = code_path or os.getcwd()
        self.services: dict[str, apprunner.CfnService] = {}
        self.service_urls: dict[str, str] = {}
        self.access_roles: dict[str, iam.Role] = {}
        self.instance_roles: dict[str, iam.Role] = {}
        self._docker_images: dict[str, ecr_assets.DockerImageAsset] = {}

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
        """Validate App Runner configuration.

        Returns:
            List of validation error messages (empty if valid).
        """
        errors: list[str] = []

        if not self.config.compute.apprunner.enabled:
            errors.append("App Runner compute is not enabled in configuration")
            return errors

        services = self.config.compute.apprunner.services
        if not services:
            # Not an error - App Runner enabled but no services defined yet
            return errors

        for name, service_config in services.items():
            # Validate dockerfile path exists
            dockerfile_path = Path(self._code_path) / service_config.dockerfile
            dockerfile_dir = dockerfile_path.parent

            # Check if the directory exists (Dockerfile might be in the directory)
            if not dockerfile_dir.exists():
                errors.append(
                    f"Service '{name}': Dockerfile directory does not exist: "
                    f"'{dockerfile_dir}'"
                )

            # Validate port is reasonable
            if service_config.port < 1 or service_config.port > 65535:
                errors.append(
                    f"Service '{name}': port must be between 1 and 65535, "
                    f"got {service_config.port}"
                )

            # Validate CPU/memory combination is valid for App Runner
            valid_combinations = [
                (1, 2),
                (1, 3),
                (1, 4),
                (2, 4),
                (2, 6),
                (4, 8),
                (4, 10),
                (4, 12),
            ]
            if (service_config.cpu, service_config.memory) not in valid_combinations:
                errors.append(
                    f"Service '{name}': Invalid CPU/memory combination "
                    f"({service_config.cpu} vCPU, {service_config.memory} GB). "
                    f"Valid combinations: {valid_combinations}"
                )

        return errors

    def _create_resources(self) -> None:
        """Create App Runner services for all configured services."""
        if not self.config.compute.apprunner.enabled:
            return

        services = self.config.compute.apprunner.services
        for service_name, service_config in services.items():
            self._create_service(service_name, service_config)

    def _create_service(
        self,
        service_name: str,
        service_config: AppRunnerServiceConfig,
    ) -> None:
        """Create a single App Runner service.

        Args:
            service_name: Name of the service (used for naming).
            service_config: Service configuration from factory.yaml.
        """
        # Build Docker image and push to ECR
        docker_image = self._build_docker_image(service_name, service_config)
        self._docker_images[service_name] = docker_image

        # Create IAM roles
        access_role = self._create_access_role(service_name)
        instance_role = self._create_instance_role(service_name)

        self.access_roles[service_name] = access_role
        self.instance_roles[service_name] = instance_role

        # Create the App Runner service
        service = self._create_apprunner_service(
            service_name, service_config, docker_image, access_role, instance_role
        )
        self.services[service_name] = service

        # Store the service URL (will be resolved at deploy time)
        # App Runner URL format: https://<random>.<region>.awsapprunner.com
        self.service_urls[service_name] = f"https://{service.attr_service_url}"

        # Register outputs
        self._register_service_outputs(service_name, service)

    def _build_docker_image(
        self,
        service_name: str,
        service_config: AppRunnerServiceConfig,
    ) -> ecr_assets.DockerImageAsset:
        """Build Docker image using CDK's DockerImageAsset.

        Args:
            service_name: Name of the service.
            service_config: Service configuration.

        Returns:
            The DockerImageAsset that will be built and pushed to ECR.
        """
        dockerfile_path = Path(service_config.dockerfile)

        # The directory containing the Dockerfile
        docker_dir = str(Path(self._code_path) / dockerfile_path.parent)

        # The Dockerfile name (default is "Dockerfile")
        dockerfile_name = dockerfile_path.name

        asset = ecr_assets.DockerImageAsset(
            self,
            f"DockerImage{service_name.capitalize()}",
            directory=docker_dir,
            file=dockerfile_name,
            platform=ecr_assets.Platform.LINUX_AMD64,
        )

        self.apply_tags(asset, Service=service_name)

        return asset

    def _create_access_role(self, service_name: str) -> iam.Role:
        """Create IAM access role for App Runner to pull images from ECR.

        Args:
            service_name: Name of the service.

        Returns:
            IAM Role for ECR access.
        """
        role_name = self.generate_resource_name("role", f"{service_name}-access")

        role = iam.Role(
            self,
            f"AccessRole{service_name.capitalize()}",
            role_name=role_name,
            assumed_by=iam.ServicePrincipal("build.apprunner.amazonaws.com"),
            description=f"App Runner access role for {service_name}",
        )

        # Add ECR pull permissions
        role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSAppRunnerServicePolicyForECRAccess"
            )
        )

        self.apply_tags(role, Service=service_name, RoleType="AppRunnerAccess")

        return role

    def _create_instance_role(self, service_name: str) -> iam.Role:
        """Create IAM instance role for the App Runner service.

        This role is assumed by the running container and can be used
        to access AWS services like DynamoDB, S3, Secrets Manager, etc.

        Args:
            service_name: Name of the service.

        Returns:
            IAM Role for the instance.
        """
        role_name = self.generate_resource_name("role", f"{service_name}-instance")

        role = iam.Role(
            self,
            f"InstanceRole{service_name.capitalize()}",
            role_name=role_name,
            assumed_by=iam.ServicePrincipal("tasks.apprunner.amazonaws.com"),
            description=f"App Runner instance role for {service_name}",
        )

        # Add basic CloudWatch Logs permissions
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                resources=["*"],
            )
        )

        self.apply_tags(role, Service=service_name, RoleType="AppRunnerInstance")

        return role

    def _create_apprunner_service(
        self,
        service_name: str,
        service_config: AppRunnerServiceConfig,
        docker_image: ecr_assets.DockerImageAsset,
        access_role: iam.Role,
        instance_role: iam.Role,
    ) -> apprunner.CfnService:
        """Create the App Runner CfnService.

        Args:
            service_name: Name of the service.
            service_config: Service configuration.
            docker_image: Docker image asset.
            access_role: IAM role for ECR access.
            instance_role: IAM role for the instance.

        Returns:
            The CfnService.
        """
        resource_name = self.generate_resource_name("apprunner", service_name)

        # Determine health check configuration based on profile
        health_check = self._create_health_check_config(service_config)

        # Create auto-scaling configuration
        auto_scaling = self._create_auto_scaling_config(service_name, service_config)

        # Build environment variables
        env_vars = self._build_environment_variables(service_name, service_config)

        # Create the source configuration
        source_config = apprunner.CfnService.SourceConfigurationProperty(
            image_repository=apprunner.CfnService.ImageRepositoryProperty(
                image_identifier=docker_image.image_uri,
                image_repository_type="ECR",
                image_configuration=apprunner.CfnService.ImageConfigurationProperty(
                    port=str(service_config.port),
                    runtime_environment_variables=env_vars if env_vars else None,
                ),
            ),
            authentication_configuration=apprunner.CfnService.AuthenticationConfigurationProperty(
                access_role_arn=access_role.role_arn,
            ),
            auto_deployments_enabled=False,  # Manual deployments for production safety
        )

        # Create instance configuration
        instance_config = apprunner.CfnService.InstanceConfigurationProperty(
            cpu=self._get_cpu_string(service_config.cpu),
            memory=self._get_memory_string(service_config.memory),
            instance_role_arn=instance_role.role_arn,
        )

        # Create the service
        service = apprunner.CfnService(
            self,
            f"Service{service_name.capitalize()}",
            service_name=resource_name,
            source_configuration=source_config,
            instance_configuration=instance_config,
            health_check_configuration=health_check,
            auto_scaling_configuration_arn=(
                auto_scaling.attr_auto_scaling_configuration_arn
                if auto_scaling
                else None
            ),
            tags=[
                {"key": "Project", "value": self.project_name},
                {"key": "Environment", "value": self.environment},
                {"key": "Service", "value": service_name},
                {"key": "ManagedBy", "value": "aws-api-factory"},
                {"key": "Profile", "value": self.config.profile.value},
            ],
        )

        # Ensure proper dependency on auto-scaling config
        if auto_scaling:
            service.add_dependency(auto_scaling)

        return service

    def _create_health_check_config(
        self, service_config: AppRunnerServiceConfig
    ) -> apprunner.CfnService.HealthCheckConfigurationProperty:
        """Create health check configuration based on profile.

        Args:
            service_config: Service configuration.

        Returns:
            Health check configuration property.
        """
        # Use profile defaults for health check protocol
        profile_healthcheck = (
            self.profile_defaults.apprunner.healthcheck_protocol.upper()
        )

        # For scalable profile or if healthcheck_path is specified, use HTTP
        if (
            profile_healthcheck == "HTTP"
            or service_config.healthcheck_path != "/healthz"
        ):
            return apprunner.CfnService.HealthCheckConfigurationProperty(
                protocol="HTTP",
                path=service_config.healthcheck_path,
                interval=10,
                timeout=5,
                healthy_threshold=1,
                unhealthy_threshold=5,
            )
        else:
            # TCP health check for minimal profile (simpler, lower overhead)
            return apprunner.CfnService.HealthCheckConfigurationProperty(
                protocol="TCP",
                interval=10,
                timeout=5,
                healthy_threshold=1,
                unhealthy_threshold=5,
            )

    def _create_auto_scaling_config(
        self,
        service_name: str,
        service_config: AppRunnerServiceConfig,
    ) -> apprunner.CfnAutoScalingConfiguration:
        """Create auto-scaling configuration.

        Args:
            service_name: Name of the service.
            service_config: Service configuration.

        Returns:
            Auto-scaling configuration.
        """
        config_name = self.generate_resource_name("autoscale", service_name)

        # Use config values with profile defaults as fallback
        min_size = service_config.min_instances
        max_size = service_config.max_instances

        # Apply profile-based scaling
        if min_size == 1 and self.profile_defaults.apprunner.min_instances > 1:
            min_size = self.profile_defaults.apprunner.min_instances
        if max_size == 10 and self.profile_defaults.apprunner.max_instances > 10:
            max_size = self.profile_defaults.apprunner.max_instances

        return apprunner.CfnAutoScalingConfiguration(
            self,
            f"AutoScaling{service_name.capitalize()}",
            auto_scaling_configuration_name=config_name,
            min_size=min_size,
            max_size=max_size,
            max_concurrency=100,  # Requests per instance before scaling
            tags=[
                {"key": "Project", "value": self.project_name},
                {"key": "Environment", "value": self.environment},
                {"key": "Service", "value": service_name},
                {"key": "ManagedBy", "value": "aws-api-factory"},
            ],
        )

    def _build_environment_variables(
        self,
        service_name: str,
        service_config: AppRunnerServiceConfig,
    ) -> list[apprunner.CfnService.KeyValuePairProperty]:
        """Build environment variables for the service.

        Args:
            service_name: Name of the service.
            service_config: Service configuration.

        Returns:
            List of environment variable properties.
        """
        env_vars = [
            apprunner.CfnService.KeyValuePairProperty(
                name="ENVIRONMENT", value=self.environment
            ),
            apprunner.CfnService.KeyValuePairProperty(
                name="PROJECT_NAME", value=self.project_name
            ),
            apprunner.CfnService.KeyValuePairProperty(
                name="SERVICE_NAME", value=service_name
            ),
        ]

        # Add user-defined environment variables
        for key, value in service_config.environment.items():
            env_vars.append(
                apprunner.CfnService.KeyValuePairProperty(name=key, value=value)
            )

        return env_vars

    def _get_cpu_string(self, cpu: int) -> str:
        """Convert CPU units to App Runner CPU string.

        Args:
            cpu: CPU units (1, 2, or 4).

        Returns:
            CPU string (e.g., "1 vCPU", "2 vCPU").
        """
        return f"{cpu} vCPU"

    def _get_memory_string(self, memory: int) -> str:
        """Convert memory to App Runner memory string.

        Args:
            memory: Memory in GB (2, 3, 4, 6, 8, 10, or 12).

        Returns:
            Memory string (e.g., "2 GB", "4 GB").
        """
        return f"{memory} GB"

    def _register_service_outputs(
        self,
        service_name: str,
        service: apprunner.CfnService,
    ) -> None:
        """Register App Runner service outputs.

        Args:
            service_name: Name of the service.
            service: The CfnService.
        """
        # Sanitize service name for CloudFormation export (alphanumeric, colons, hyphens only)
        # Convert underscores to hyphens and capitalize words
        sanitized_name = "".join(
            word.capitalize() for word in service_name.replace("-", "_").split("_")
        )

        # Service URL
        self.add_output(
            key=f"AppRunner{sanitized_name}Url",
            value=f"https://{service.attr_service_url}",
            description=f"App Runner service URL for {service_name}",
            export=True,
        )

        # Service ARN
        self.add_output(
            key=f"AppRunner{sanitized_name}Arn",
            value=service.attr_service_arn,
            description=f"App Runner service ARN for {service_name}",
        )

        # Service ID
        self.add_output(
            key=f"AppRunner{sanitized_name}Id",
            value=service.attr_service_id,
            description=f"App Runner service ID for {service_name}",
        )

    def get_service(self, service_name: str) -> apprunner.CfnService | None:
        """Get an App Runner service by name.

        Args:
            service_name: The service name as defined in config.

        Returns:
            The CfnService or None if not found.
        """
        return self.services.get(service_name)

    def get_service_url(self, service_name: str) -> str | None:
        """Get the URL for an App Runner service.

        Args:
            service_name: The service name as defined in config.

        Returns:
            The service URL or None if not found.
        """
        return self.service_urls.get(service_name)

    def get_instance_role(self, service_name: str) -> iam.Role | None:
        """Get the instance role for an App Runner service.

        This role can be used to grant additional permissions to the
        running container.

        Args:
            service_name: The service name as defined in config.

        Returns:
            The IAM Role or None if not found.
        """
        return self.instance_roles.get(service_name)


def create_apprunner_service(
    scope: Construct,
    id: str,
    *,
    config: FactoryConfig,
    profile_defaults: ProfileDefaults,
    output_manager: OutputManager,
    environment: str,
    code_path: str | None = None,
) -> AppRunnerConstruct:
    """Convenience function to create an App Runner construct.

    Args:
        scope: The CDK construct scope.
        id: The construct ID.
        config: The factory configuration.
        profile_defaults: Profile defaults.
        output_manager: Output manager.
        environment: Deployment environment.
        code_path: Optional base path for Dockerfiles.

    Returns:
        The created AppRunnerConstruct.
    """
    return AppRunnerConstruct(
        scope,
        id,
        config=config,
        profile_defaults=profile_defaults,
        output_manager=output_manager,
        environment=environment,
        code_path=code_path,
    )

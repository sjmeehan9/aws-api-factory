# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Sean Meehan
"""User-customizable Factory Stack.

This module provides a customizable FactoryStack that users can extend
to add custom resources, override construct behavior, or integrate with
existing infrastructure.

For most use cases, the base FactoryStack is sufficient and you don't
need to modify this file. However, if you need to:

1. Add custom AWS resources not covered by factory.yaml
2. Import existing resources (VPCs, certificates, etc.)
3. Add custom IAM policies or permissions
4. Override construct defaults programmatically

Then this file is your escape hatch.

Example:
    To add a custom S3 bucket:

    >>> class MyFactoryStack(FactoryStack):
    ...     def __init__(self, scope, id, *, config, environment, **kwargs):
    ...         super().__init__(scope, id, config=config, environment=environment, **kwargs)
    ...
    ...         # Add custom resources after factory constructs
    ...         self.custom_bucket = s3.Bucket(
    ...             self, "CustomBucket",
    ...             bucket_name=f"{config.project.name}-{environment}-custom",
    ...         )

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from aws_api_factory.constructs import FactoryStack as BaseFactoryStack

if TYPE_CHECKING:
    from aws_cdk import Environment
    from constructs import Construct

    from aws_api_factory.config.defaults import ProfileDefaults
    from aws_api_factory.config.models import FactoryConfig


class FactoryStack(BaseFactoryStack):
    """Customizable Factory Stack.

    This class extends the base FactoryStack to allow user customizations.
    Override the `add_custom_resources()` method to add your own resources
    without modifying the core factory logic.

    All factory constructs are created first, then `add_custom_resources()`
    is called, giving you access to all factory-created resources.

    Attributes:
        config: The resolved factory configuration.
        environment_name: The deployment environment name.
        output_manager: The output manager for this stack.
        constructs: Dictionary of instantiated constructs by config section.

    Example:
        >>> class MyStack(FactoryStack):
        ...     def add_custom_resources(self) -> None:
        ...         # Access factory constructs
        ...         api_construct = self.get_construct("apis.rest")
        ...
        ...         # Add custom resources
        ...         from aws_cdk import aws_s3 as s3
        ...         self.custom_bucket = s3.Bucket(self, "MyBucket")
        ...
        ...         # Register custom outputs
        ...         self.output_manager.add(
        ...             key="CustomBucketName",
        ...             value=self.custom_bucket.bucket_name,
        ...             description="Custom S3 bucket name",
        ...             category="custom",
        ...         )
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        config: FactoryConfig,
        environment: str,
        profile_defaults: ProfileDefaults | None = None,
        env: Environment | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the customizable FactoryStack.

        Args:
            scope: The CDK app or construct scope.
            construct_id: The stack construct ID.
            config: The resolved factory configuration.
            environment: The deployment environment name.
            profile_defaults: Optional profile defaults.
            env: Optional CDK environment (account, region).
            **kwargs: Additional arguments passed to Stack.
        """
        # NOTE: We need to delay output export to add custom resources
        # The base class exports outputs in __init__, so we override
        # the entire initialization flow here.

        super().__init__(
            scope,
            construct_id,
            config=config,
            environment=environment,
            profile_defaults=profile_defaults,
            env=env,
            **kwargs,
        )

        # Note: Custom resources should be added by overriding this class
        # and calling add_custom_resources() in the subclass __init__
        # AFTER calling super().__init__()

    def add_custom_resources(self) -> None:
        """Override this method to add custom AWS resources.

        This method is called after all factory constructs are created.
        You have access to:

        - self.config: The resolved configuration
        - self.environment_name: The environment name
        - self.constructs: All created factory constructs
        - self.output_manager: For registering custom outputs

        Example:
            >>> def add_custom_resources(self) -> None:
            ...     from aws_cdk import aws_s3 as s3
            ...
            ...     # Create custom bucket
            ...     self.logs_bucket = s3.Bucket(
            ...         self, "LogsBucket",
            ...         bucket_name=f"{self.config.project.name}-{self.environment_name}-logs",
            ...     )
            ...
            ...     # Register output
            ...     self.output_manager.add(
            ...         key="LogsBucketArn",
            ...         value=self.logs_bucket.bucket_arn,
            ...         description="Logs bucket ARN",
            ...         category="custom",
            ...     )
        """
        pass  # Override in subclass to add custom resources

    # =========================================================================
    # Escape Hatches
    # =========================================================================

    def import_existing_vpc(self, vpc_id: str) -> Any:
        """Import an existing VPC by ID.

        Args:
            vpc_id: The VPC ID to import.

        Returns:
            The imported VPC construct.

        Example:
            >>> vpc = self.import_existing_vpc("vpc-12345678")
        """
        from aws_cdk import aws_ec2 as ec2

        return ec2.Vpc.from_lookup(self, "ImportedVpc", vpc_id=vpc_id)

    def import_existing_certificate(self, certificate_arn: str) -> Any:
        """Import an existing ACM certificate by ARN.

        Args:
            certificate_arn: The certificate ARN to import.

        Returns:
            The imported certificate construct.

        Example:
            >>> cert = self.import_existing_certificate(
            ...     "arn:aws:acm:us-east-1:123456789:certificate/xxx"
            ... )
        """
        from aws_cdk import aws_certificatemanager as acm

        return acm.Certificate.from_certificate_arn(
            self, "ImportedCertificate", certificate_arn
        )

    def import_existing_hosted_zone(self, hosted_zone_id: str, zone_name: str) -> Any:
        """Import an existing Route53 hosted zone.

        Args:
            hosted_zone_id: The hosted zone ID to import.
            zone_name: The domain name of the zone.

        Returns:
            The imported hosted zone construct.

        Example:
            >>> zone = self.import_existing_hosted_zone(
            ...     "Z1234567890ABC",
            ...     "example.com"
            ... )
        """
        from aws_cdk import aws_route53 as route53

        return route53.HostedZone.from_hosted_zone_attributes(
            self,
            "ImportedHostedZone",
            hosted_zone_id=hosted_zone_id,
            zone_name=zone_name,
        )
